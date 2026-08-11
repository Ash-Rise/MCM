from __future__ import annotations

import argparse
import hashlib
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats
from scipy.integrate import quad

from ambulance_model import (
    DELAY_PENALTY_YUAN_PER_MINUTE,
    GOLDEN_RESPONSE_MINUTES,
    MINUTES_PER_DAY,
    Call,
    ProblemData,
    generate_calls,
    intraday_density,
    problem_statement_path,
    read_problem,
    sha256,
    simulate,
)


INPUT_SHA256 = "5F5079815AB8AD6592FEE7A4B0B8B01A5DF8865983A2871C324B6AB772C39F2D"
WARMUP_DAYS = 30
BETA = 4.0
DELTA = 2.0
DURATIONS_HOURS = (0.5, 1.0, 2.0, 4.0, 8.0, 12.0)
REPLICATIONS = 10
BASE_SEED = 600_000

_WORKER_DATA: ProblemData | None = None


def _duration_mass(start_hour: float, duration_hours: float) -> float:
    if not 0.0 < duration_hours <= 24.0:
        raise ValueError("Incident duration must lie in (0, 24] hours")
    value, _ = quad(
        lambda hour: float(intraday_density(hour)),
        start_hour,
        start_hour + duration_hours,
        epsabs=1e-10,
        epsrel=1e-10,
        limit=100,
    )
    return float(value)


def worst_start_hour(duration_hours: float, candidate_start: float | None = None) -> float:
    if candidate_start is not None:
        return _duration_mass(float(candidate_start) % 24.0, duration_hours)
    grid = np.arange(0.0, 24.0, 1.0 / 60.0)
    masses = np.array([_duration_mass(float(start), duration_hours) for start in grid])
    return float(grid[int(np.argmax(masses))])


def incident_rate_multiplier(
    zone: int,
    start_min: float,
    end_min: float,
    zone_count: int,
) -> Callable[[float], np.ndarray]:
    if not 0 <= zone < zone_count:
        raise ValueError("Incident zone is outside the demand-zone set")
    if end_min <= start_min:
        raise ValueError("Incident end must be after its start")

    def multiplier(future_min: float) -> np.ndarray:
        values = np.ones(zone_count)
        if start_min <= future_min < end_min:
            values[zone] = 5.0
        return values

    return multiplier


def generate_incident_calls(
    data: ProblemData,
    warmup_days: int,
    incident_zone: int,
    start_hour: float,
    duration_hours: float,
    seed: int,
) -> list[Call]:
    if warmup_days < 0:
        raise ValueError("Warmup days cannot be negative")
    if not 0 <= incident_zone < len(data.zone_ids):
        raise ValueError("Incident zone is outside the demand-zone set")
    start_min = warmup_days * MINUTES_PER_DAY + start_hour * 60.0
    end_min = start_min + duration_hours * 60.0
    expected_extra = 4.0 * float(data.demand[incident_zone]) * _duration_mass(start_hour, duration_hours)
    rng = np.random.default_rng(seed)
    count = int(rng.poisson(expected_extra))
    if count == 0:
        return []

    grid = np.linspace(start_hour, start_hour + duration_hours, max(121, int(duration_hours * 120) + 1))
    upper = 1.001 * float(np.max(intraday_density(grid)))
    accepted: list[float] = []
    while len(accepted) < count:
        remaining = count - len(accepted)
        candidates = rng.uniform(start_hour, start_hour + duration_hours, size=max(remaining * 2, 32))
        heights = rng.uniform(0.0, upper, size=len(candidates))
        accepted.extend(candidates[heights <= intraday_density(candidates)][:remaining].tolist())
    arrivals = sorted(start_min + 60.0 * (hour - start_hour) for hour in accepted)
    return [Call(call_id=index, arrival_min=arrival, zone=incident_zone) for index, arrival in enumerate(arrivals)]


def build_scenario_calls(
    data: ProblemData,
    incident_zone: int,
    start_hour: float,
    duration_hours: float,
    seed: int,
) -> list[Call]:
    incident_end = WARMUP_DAYS * MINUTES_PER_DAY + (start_hour + duration_hours) * 60.0
    days = int(math.ceil(incident_end / MINUTES_PER_DAY))
    background = [call for call in generate_calls(data, days=days, seed=seed) if call.arrival_min < incident_end]
    extra = generate_incident_calls(
        data,
        warmup_days=WARMUP_DAYS,
        incident_zone=incident_zone,
        start_hour=start_hour,
        duration_hours=duration_hours,
        seed=seed + 1_000_000,
    )
    ordered = sorted([*background, *extra], key=lambda call: (call.arrival_min, call.zone, call.call_id))
    return [Call(call_id=index, arrival_min=call.arrival_min, zone=call.zone) for index, call in enumerate(ordered)]


def _queue_statistics(records: pd.DataFrame, start_min: float, end_min: float) -> tuple[int, int]:
    initial = int(((records["arrival_min"] < start_min) & (records["dispatch_min"] >= start_min)).sum())
    events: list[tuple[float, int, int]] = []
    for arrival in records.loc[
        (records["arrival_min"] >= start_min) & (records["arrival_min"] < end_min), "arrival_min"
    ]:
        events.append((float(arrival), 0, 1))
    for dispatch in records.loc[
        (records["dispatch_min"] >= start_min) & (records["dispatch_min"] < end_min), "dispatch_min"
    ]:
        events.append((float(dispatch), 1, -1))
    queue = initial
    maximum = initial
    for _, _, change in sorted(events):
        queue += change
        maximum = max(maximum, queue)
    end_backlog = int(((records["arrival_min"] < end_min) & (records["dispatch_min"] >= end_min)).sum())
    return maximum, end_backlog


def _group_metrics(frame: pd.DataFrame, prefix: str) -> dict[str, float | int]:
    if frame.empty:
        return {
            f"{prefix}calls": 0,
            f"{prefix}mean_response_min": np.nan,
            f"{prefix}p95_response_min": np.nan,
            f"{prefix}strict_4min_rate": np.nan,
            f"{prefix}mean_wait_min": np.nan,
            f"{prefix}mean_delay_penalty_yuan_per_call": np.nan,
        }
    response = frame["response_min"].to_numpy(dtype=float)
    wait = frame["wait_min"].to_numpy(dtype=float)
    return {
        f"{prefix}calls": int(len(frame)),
        f"{prefix}mean_response_min": float(np.mean(response)),
        f"{prefix}p95_response_min": float(np.quantile(response, 0.95)),
        f"{prefix}strict_4min_rate": float(np.mean(response <= GOLDEN_RESPONSE_MINUTES + 1e-9)),
        f"{prefix}mean_wait_min": float(np.mean(wait)),
        f"{prefix}mean_delay_penalty_yuan_per_call": float(
            np.mean(DELAY_PENALTY_YUAN_PER_MINUTE * np.maximum(response - GOLDEN_RESPONSE_MINUTES, 0.0))
        ),
    }


def summarize_incident(
    records: pd.DataFrame,
    incident_zone: int,
    start_min: float,
    end_min: float,
) -> dict[str, float | int]:
    incident = records[(records["arrival_min"] >= start_min) & (records["arrival_min"] < end_min)]
    local = incident[incident["zone"] == incident_zone]
    other = incident[incident["zone"] != incident_zone]
    maximum_queue, end_backlog = _queue_statistics(records, start_min, end_min)
    metrics: dict[str, float | int] = {
        **_group_metrics(incident, ""),
        **_group_metrics(local, "incident_zone_"),
        **_group_metrics(other, "nonincident_zone_"),
        "max_incident_queue": maximum_queue,
        "incident_end_backlog": end_backlog,
    }
    return metrics


def _call_digest(calls: list[Call]) -> str:
    payload = "\n".join(f"{call.call_id},{call.arrival_min:.12f},{call.zone}" for call in calls)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _init_worker(input_path: str) -> None:
    global _WORKER_DATA
    _WORKER_DATA = read_problem(Path(input_path))


def _scenario_worker(task: dict[str, float | int]) -> list[dict[str, object]]:
    if _WORKER_DATA is None:
        raise RuntimeError("Worker data is not initialized")
    zone = int(task["incident_zone"])
    duration = float(task["duration_hours"])
    seed = int(task["seed"])
    start_hour = float(task["start_hour"])
    start_min = WARMUP_DAYS * MINUTES_PER_DAY + start_hour * 60.0
    end_min = start_min + duration * 60.0
    calls = build_scenario_calls(_WORKER_DATA, zone, start_hour, duration, seed)
    digest = _call_digest(calls)
    multiplier = incident_rate_multiplier(zone, start_min, end_min, len(_WORKER_DATA.zone_ids))
    configurations = {
        "B_N": {},
        "B_E": {
            "rate_multiplier": multiplier,
            "rate_multiplier_active_from": start_min,
        },
    }
    rows = []
    for mode, settings in configurations.items():
        records, full_metrics = simulate(
            _WORKER_DATA,
            calls,
            strategy="B",
            beta=BETA,
            delta=DELTA,
            **settings,
        )
        rows.append(
            {
                "mode": mode,
                "incident_zone": zone + 1,
                "duration_hours": duration,
                "start_hour": start_hour,
                "seed": seed,
                "call_digest": digest,
                **summarize_incident(records, zone, start_min, end_min),
                "max_daily_dispatches_per_ambulance": full_metrics["max_daily_dispatches_per_ambulance"],
            }
        )
    return rows


def _summaries(replicates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    key = ["mode", "incident_zone", "duration_hours", "start_hour"]
    metric_columns = [
        column
        for column in replicates.columns
        if column not in {*key, "seed", "call_digest", "max_daily_dispatches_per_ambulance"}
    ]
    summary_rows = []
    for group_key, group in replicates.groupby(key, sort=True):
        common = dict(zip(key, group_key, strict=True))
        for metric in metric_columns:
            values = group[metric].dropna().to_numpy(dtype=float)
            if len(values) == 0:
                continue
            mean = float(np.mean(values))
            half = 0.0 if len(values) == 1 else float(stats.t.ppf(0.975, len(values) - 1) * stats.sem(values))
            summary_rows.append(
                {**common, "metric": metric, "mean": mean, "ci95_low": mean - half, "ci95_high": mean + half, "replications": len(values)}
            )

    paired_rows = []
    pair_keys = ["incident_zone", "duration_hours", "start_hour", "seed"]
    for metric in metric_columns:
        pivot = replicates.pivot(index=pair_keys, columns="mode", values=metric).dropna()
        if not {"B_N", "B_E"}.issubset(pivot.columns):
            continue
        pivot = pivot.assign(difference=pivot["B_E"] - pivot["B_N"]).reset_index()
        for group_key, group in pivot.groupby(pair_keys[:-1], sort=True):
            values = group["difference"].to_numpy(dtype=float)
            mean = float(np.mean(values))
            half = 0.0 if len(values) == 1 else float(stats.t.ppf(0.975, len(values) - 1) * stats.sem(values))
            paired_rows.append(
                {
                    **dict(zip(pair_keys[:-1], group_key, strict=True)),
                    "metric": metric,
                    "mean_difference_B_E_minus_B_N": mean,
                    "ci95_low": mean - half,
                    "ci95_high": mean + half,
                    "replications": len(values),
                }
            )
    return pd.DataFrame(summary_rows), pd.DataFrame(paired_rows)


def run_full(project_root: Path, workers: int) -> Path:
    input_path = problem_statement_path(project_root)
    if sha256(input_path) != INPUT_SHA256:
        raise ValueError("Problem A statement hash does not match the frozen model input")
    output = project_root / "results" / "task-3"
    output.mkdir(parents=True, exist_ok=True)
    scenarios = pd.DataFrame(
        [
            {
                "incident_zone": zone,
                "duration_hours": duration,
                "start_hour": worst_start_hour(duration),
                "expected_extra_calls": 4.0
                * float(read_problem(input_path).demand[zone - 1])
                * _duration_mass(worst_start_hour(duration), duration),
            }
            for zone in range(1, 11)
            for duration in DURATIONS_HOURS
        ]
    )
    scenarios.to_csv(output / "scenarios.csv", index=False, encoding="utf-8-sig")
    tasks = [
        {**row, "incident_zone": int(row["incident_zone"]) - 1, "seed": BASE_SEED + replication}
        for row in scenarios.to_dict(orient="records")
        for replication in range(REPLICATIONS)
    ]
    started = time.time()
    rows: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(str(input_path),)) as executor:
        futures = [executor.submit(_scenario_worker, task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.extend(future.result())
            if completed == 1 or completed % max(1, len(tasks) // 20) == 0 or completed == len(tasks):
                elapsed = time.time() - started
                print(f"[task-3] {completed}/{len(tasks)} scenarios, elapsed={elapsed:.1f}s", flush=True)
    replicates = pd.DataFrame(rows).sort_values(["incident_zone", "duration_hours", "seed", "mode"])
    expected_rows = len(tasks) * 2
    if len(replicates) != expected_rows:
        raise AssertionError(f"Expected {expected_rows} paired rows, received {len(replicates)}")
    pair_counts = replicates.groupby(["incident_zone", "duration_hours", "seed"])["mode"].nunique()
    if not (pair_counts == 2).all():
        raise AssertionError("Every Task 3 scenario must contain both B_N and B_E")
    if not (replicates.groupby(["incident_zone", "duration_hours", "seed"])["call_digest"].nunique() == 1).all():
        raise AssertionError("Paired Task 3 modes did not receive identical calls")
    if replicates["max_daily_dispatches_per_ambulance"].max() > 12:
        raise AssertionError("Task 3 violated the per-ambulance daily dispatch cap")
    replicates.to_csv(output / "replicates.csv", index=False, encoding="utf-8-sig")
    summary, paired = _summaries(replicates)
    summary.to_csv(output / "summary.csv", index=False, encoding="utf-8-sig")
    paired.to_csv(output / "paired_effects.csv", index=False, encoding="utf-8-sig")
    return output / "summary.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Task 3 emergency dispatch scenarios")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workers", type=int, default=min(12, max(1, (os.cpu_count() or 2) - 1)))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(run_full(args.project_root.resolve(), args.workers))


if __name__ == "__main__":
    main()
