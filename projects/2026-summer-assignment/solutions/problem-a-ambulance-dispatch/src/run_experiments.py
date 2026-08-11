from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

from ambulance_model import (
    BUSY_MINUTES,
    DAILY_CAP,
    MINUTES_PER_DAY,
    generate_calls,
    delay_penalty_cost,
    problem_statement_path,
    read_problem,
    sha256,
    simulate,
)


INPUT_SHA256 = "5F5079815AB8AD6592FEE7A4B0B8B01A5DF8865983A2871C324B6AB772C39F2D"
TUNING_REPLICATIONS = 30
SELECTION_REPLICATIONS = 30
FINAL_REPLICATIONS = 100
MEASURE_DAYS = 100
FIXED_WARMUP_DAYS = 30

_WORKER_DATA = None


def b_candidates() -> list[dict[str, object]]:
    return [
        {
            "candidate": f"B_beta{beta:g}_delta{delta:g}",
            "strategy": "B",
            "beta": float(beta),
            "delta": float(delta),
        }
        for beta, delta in itertools.product([0, 0.5, 1, 2, 4], [0.5, 1, 1.5, 2])
    ]


def b_fine_candidates(coarse_name: str) -> list[dict[str, object]]:
    coarse = {candidate["candidate"]: candidate for candidate in b_candidates()}
    if coarse_name not in coarse:
        raise ValueError(f"Unknown coarse B candidate: {coarse_name}")
    center = coarse[coarse_name]
    beta_grid = [0.0, 0.5, 1.0, 2.0, 4.0]
    delta_grid = [0.5, 1.0, 1.5, 2.0]

    def local_values(grid: list[float], value: float) -> list[float]:
        index = grid.index(value)
        values = {value}
        if index > 0:
            values.add((grid[index - 1] + value) / 2.0)
        if index + 1 < len(grid):
            values.add((value + grid[index + 1]) / 2.0)
        return sorted(values)

    coarse_pairs = {(candidate["beta"], candidate["delta"]) for candidate in coarse.values()}
    candidates = []
    for beta, delta in itertools.product(
        local_values(beta_grid, float(center["beta"])),
        local_values(delta_grid, float(center["delta"])),
    ):
        if (beta, delta) in coarse_pairs:
            continue
        candidates.append(
            {
                "candidate": f"B_beta{beta:g}_delta{delta:g}",
                "strategy": "B",
                "beta": beta,
                "delta": delta,
            }
        )
    return candidates


def c_candidates() -> list[dict[str, object]]:
    capacities = [3, 2, 2, 2, 1, 2]
    vectors = [
        list(vector)
        for vector in itertools.product(*(range(capacity) for capacity in capacities))
        if any(vector)
    ]
    return [
        {
            "candidate": "C_r" + "".join(map(str, vector)) + f"_tau{tau:g}",
            "strategy": "C",
            "reserve_vector": vector,
            "tau": float(tau),
        }
        for vector, tau in itertools.product(vectors, [4, 5, 6, 7, 8])
    ]


def a_candidate() -> dict[str, object]:
    return {"candidate": "A", "strategy": "A"}


def daily_diagnostics(records: pd.DataFrame, total_days: int) -> pd.DataFrame:
    rows = []
    for day in range(total_days):
        start = day * MINUTES_PER_DAY
        end = (day + 1) * MINUTES_PER_DAY
        arrivals = records[(records["arrival_min"] >= start) & (records["arrival_min"] < end)]
        backlog = records[(records["arrival_min"] < end) & (records["dispatch_min"] >= end)]
        busy = records[(records["dispatch_min"] < end) & (records["dispatch_min"] + BUSY_MINUTES > end)]
        if "ambulance_id" in busy.columns:
            busy_count = int(busy["ambulance_id"].nunique())
        else:
            busy_count = int(len(busy))
        rows.append(
            {
                "day": day,
                "end_backlog": int(len(backlog)),
                "busy_at_midnight": busy_count,
                "mean_response_min": float(arrivals["response_min"].mean()) if len(arrivals) else np.nan,
                "total_delay_penalty_yuan": float(
                    np.sum(delay_penalty_cost(arrivals["response_min"].to_numpy(dtype=float)))
                ),
            }
        )
    return pd.DataFrame(rows).set_index("day")


def _queue_statistics(records: pd.DataFrame, start: float, end: float) -> tuple[int, float, int]:
    initial = int(((records["arrival_min"] < start) & (records["dispatch_min"] >= start)).sum())
    events: list[tuple[float, int, int]] = []
    for arrival in records.loc[(records["arrival_min"] >= start) & (records["arrival_min"] < end), "arrival_min"]:
        events.append((float(arrival), 0, 1))
    for dispatch in records.loc[(records["dispatch_min"] >= start) & (records["dispatch_min"] < end), "dispatch_min"]:
        events.append((float(dispatch), 1, -1))
    queue = initial
    maximum = initial
    area = 0.0
    last = start
    for event_time, _, delta in sorted(events):
        area += queue * max(0.0, event_time - last)
        queue += delta
        maximum = max(maximum, queue)
        last = event_time
    area += queue * max(0.0, end - last)
    return maximum, area / max(end - start, 1.0), queue


def summarize_measurement(
    records: pd.DataFrame,
    warmup_days: int,
    measure_days: int,
    strategy: str,
    reserve_vector: list[int] | None,
) -> dict[str, float | int]:
    start = warmup_days * MINUTES_PER_DAY
    end = (warmup_days + measure_days) * MINUTES_PER_DAY
    measured = records[(records["arrival_min"] >= start) & (records["arrival_min"] < end)].copy()
    if measured.empty:
        raise RuntimeError("Measurement window contains no calls")
    response = measured["response_min"].to_numpy(dtype=float)
    chain = response + 60.0 * _WORKER_DATA.hospital_distance[measured["zone"].to_numpy(dtype=int)] / 45.0
    wait = measured["wait_min"].to_numpy(dtype=float)
    delay_costs = np.asarray(delay_penalty_cost(response), dtype=float)
    maximum_queue, mean_queue, terminal_queue = _queue_statistics(records, start, end)
    daily = daily_diagnostics(records, warmup_days + measure_days).loc[warmup_days:]
    region_means = measured.groupby("zone")["response_min"].mean()
    accepted = records[(records["dispatch_min"] >= start) & (records["dispatch_min"] < end)].copy()
    accepted["accepted_day"] = (accepted["dispatch_min"] // MINUTES_PER_DAY).astype(int)
    daily_vehicle = accepted.groupby(["ambulance_id", "accepted_day"]).size()

    metrics: dict[str, float | int] = {
        "calls": int(len(measured)),
        "mean_response_min": float(np.mean(response)),
        "mean_ideal_chain_min": float(np.mean(chain)),
        "p95_ideal_chain_min": float(np.quantile(chain, 0.95)),
        "strict_4min_rate": float(np.mean(response <= 4.0 + 1e-9)),
        "median_response_min": float(np.quantile(response, 0.50)),
        "p90_response_min": float(np.quantile(response, 0.90)),
        "p95_response_min": float(np.quantile(response, 0.95)),
        "mean_wait_min": float(np.mean(wait)),
        "mean_delay_penalty_yuan_per_call": float(np.mean(delay_costs)),
        "mean_daily_delay_penalty_yuan": float(np.sum(delay_costs) / measure_days),
        "wait_probability": float(np.mean(wait > 1e-9)),
        "max_wait_min": float(np.max(wait)),
        "max_queue": int(maximum_queue),
        "mean_queue": float(mean_queue),
        "terminal_queue": int(terminal_queue),
        "mean_end_backlog": float(daily["end_backlog"].mean()),
        "max_end_backlog": int(daily["end_backlog"].max()),
        "regional_mean_gap_min": float(region_means.max() - region_means.min()),
        "worst_region_mean_min": float(region_means.max()),
        "max_daily_dispatches_per_ambulance": int(daily_vehicle.max()),
        "daily_cap_hit_rate": float(np.sum(daily_vehicle.to_numpy() >= DAILY_CAP) / (12 * measure_days)),
    }
    if strategy == "B":
        c_values = measured["c_loss_min"].dropna().to_numpy(dtype=float)
        metrics["mean_c_loss_min"] = float(np.mean(c_values))
        metrics["max_c_loss_min"] = float(np.max(c_values))
    if strategy == "C" and reserve_vector is not None:
        reserve_ids = set()
        offset = 0
        for site_count, reserve_count in zip([3, 2, 2, 2, 1, 2], reserve_vector, strict=True):
            reserve_ids.update(range(offset, offset + reserve_count))
            offset += site_count
        metrics["reserve_dispatches"] = int(measured["ambulance_id"].isin(reserve_ids).sum())
    return metrics


def _init_worker(input_path: str) -> None:
    global _WORKER_DATA
    _WORKER_DATA = read_problem(Path(input_path))


def _strategy_kwargs(candidate: dict[str, object]) -> dict[str, object]:
    if candidate["strategy"] == "B":
        return {"beta": candidate["beta"], "delta": candidate["delta"]}
    if candidate["strategy"] == "C":
        return {"reserve_vector": candidate["reserve_vector"], "tau": candidate["tau"]}
    return {}


def _replication_worker(task: dict[str, object]) -> dict[str, object] | list[dict[str, object]]:
    if _WORKER_DATA is None:
        raise RuntimeError("Worker input data was not initialized")
    candidate = task["candidate"]
    seed = int(task["seed"])
    warmup_days = int(task["warmup_days"])
    measure_days = int(task["measure_days"])
    calls = generate_calls(_WORKER_DATA, warmup_days + measure_days, seed)
    records, _ = simulate(
        _WORKER_DATA,
        calls,
        strategy=str(candidate["strategy"]),
        **_strategy_kwargs(candidate),
    )
    common = {
        "candidate": candidate["candidate"],
        "strategy": candidate["strategy"],
        "seed": seed,
    }
    if task.get("daily_only"):
        daily = daily_diagnostics(records, warmup_days + measure_days).reset_index()
        return [{**common, **row} for row in daily.to_dict(orient="records")]
    metrics = summarize_measurement(
        records,
        warmup_days=warmup_days,
        measure_days=measure_days,
        strategy=str(candidate["strategy"]),
        reserve_vector=candidate.get("reserve_vector"),
    )
    metrics.setdefault("mean_c_loss_min", None)
    metrics.setdefault("max_c_loss_min", None)
    metrics.setdefault("reserve_dispatches", None)
    return {**common, **metrics}


def _append_rows(path: Path, rows: list[dict[str, object]]) -> None:
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def run_tasks(
    input_path: Path,
    output_path: Path,
    tasks: list[dict[str, object]],
    workers: int,
    daily_only: bool,
) -> pd.DataFrame:
    completed: set[tuple[str, int]] = set()
    if output_path.exists():
        existing = pd.read_csv(output_path)
        if not existing.empty:
            if daily_only:
                counts = existing.groupby(["candidate", "seed"])["day"].nunique()
                required = int(tasks[0]["warmup_days"]) + int(tasks[0]["measure_days"])
                completed = {tuple(index) for index, count in counts.items() if count == required}
            else:
                completed = set(zip(existing["candidate"], existing["seed"].astype(int)))
    pending = [
        {**task, "daily_only": daily_only}
        for task in tasks
        if (str(task["candidate"]["candidate"]), int(task["seed"])) not in completed
    ]
    total = len(pending)
    started = time.perf_counter()
    if pending:
        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_init_worker,
            initargs=(str(input_path),),
        ) as executor:
            future_map = {executor.submit(_replication_worker, task): task for task in pending}
            for finished, future in enumerate(as_completed(future_map), start=1):
                result = future.result()
                rows = result if isinstance(result, list) else [result]
                _append_rows(output_path, rows)
                if finished == 1 or finished % max(1, min(25, total // 20 or 1)) == 0 or finished == total:
                    elapsed = time.perf_counter() - started
                    rate = finished / elapsed
                    eta = (total - finished) / rate if rate > 0 else math.inf
                    print(
                        f"[{output_path.stem}] {finished}/{total} tasks, "
                        f"elapsed={elapsed:.1f}s, eta={eta:.1f}s",
                        flush=True,
                    )
    frame = pd.read_csv(output_path)
    sort_columns = ["candidate", "seed"] + (["day"] if daily_only else [])
    frame = frame.sort_values(sort_columns).reset_index(drop=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return frame


def _seed_block(base: int, count: int) -> list[int]:
    return list(range(base, base + count))


def _paired_ci(differences: np.ndarray, confidence: float = 0.95) -> tuple[float, float]:
    values = np.asarray(differences, dtype=float)
    mean = float(np.mean(values))
    if len(values) < 2 or np.std(values, ddof=1) == 0:
        return mean, mean
    half = float(stats.t.ppf(0.5 + confidence / 2.0, len(values) - 1) * stats.sem(values))
    return mean - half, mean + half


def select_b(tuning: pd.DataFrame) -> str:
    data = tuning[tuning["strategy"] == "B"]
    means = data.groupby("candidate")["mean_response_min"].mean().sort_values()
    best = str(means.index[0])
    pivot = data.pivot(index="seed", columns="candidate", values="mean_response_min")
    tied = []
    for candidate in means.index:
        low, high = _paired_ci((pivot[candidate] - pivot[best]).dropna().to_numpy())
        if low <= 0 <= high:
            tied.append(candidate)
    secondary = (
        data[data["candidate"].isin(tied)]
        .groupby("candidate")
        .agg(
            strict_4min_rate=("strict_4min_rate", "mean"),
            p95_response_min=("p95_response_min", "mean"),
            regional_mean_gap_min=("regional_mean_gap_min", "mean"),
        )
        .reset_index()
        .sort_values(
            ["strict_4min_rate", "p95_response_min", "regional_mean_gap_min", "candidate"],
            ascending=[False, True, True, True],
        )
    )
    return str(secondary.iloc[0]["candidate"])


def select_c(tuning: pd.DataFrame) -> str | None:
    a = tuning[tuning["candidate"] == "A"].set_index("seed")["mean_response_min"]
    candidates = []
    for candidate, group in tuning[tuning["strategy"] == "C"].groupby("candidate"):
        c = group.set_index("seed")["mean_response_min"]
        common = a.index.intersection(c.index)
        if float((c.loc[common] - a.loc[common]).mean()) <= 0:
            candidates.append(candidate)
    if not candidates:
        return None
    ranked = (
        tuning[tuning["candidate"].isin(candidates)]
        .groupby("candidate")
        .agg(
            strict_4min_rate=("strict_4min_rate", "mean"),
            p95_response_min=("p95_response_min", "mean"),
            regional_mean_gap_min=("regional_mean_gap_min", "mean"),
        )
        .reset_index()
        .sort_values(
            ["strict_4min_rate", "p95_response_min", "regional_mean_gap_min", "candidate"],
            ascending=[False, True, True, True],
        )
    )
    return str(ranked.iloc[0]["candidate"])


def one_sided_upper(differences: np.ndarray, confidence: float = 0.95) -> float:
    values = np.asarray(differences, dtype=float)
    mean = float(np.mean(values))
    if len(values) < 2 or np.std(values, ddof=1) == 0:
        return mean
    return mean + float(stats.t.ppf(confidence, len(values) - 1) * stats.sem(values))


def choose_main_policy(selection: pd.DataFrame, eligible: list[str]) -> str:
    data = selection[selection["candidate"].isin(eligible)]
    means = data.groupby("candidate")["mean_response_min"].mean().sort_values()
    best = str(means.index[0])
    pivot = data.pivot(index="seed", columns="candidate", values="mean_response_min")
    tied = []
    for candidate in means.index:
        low, high = _paired_ci((pivot[candidate] - pivot[best]).dropna().to_numpy())
        if low <= 0 <= high:
            tied.append(candidate)
    ranked = (
        data[data["candidate"].isin(tied)]
        .groupby("candidate")
        .agg(
            strict_4min_rate=("strict_4min_rate", "mean"),
            p95_response_min=("p95_response_min", "mean"),
            regional_mean_gap_min=("regional_mean_gap_min", "mean"),
        )
        .reset_index()
        .sort_values(
            ["strict_4min_rate", "p95_response_min", "regional_mean_gap_min", "candidate"],
            ascending=[False, True, True, True],
        )
    )
    return str(ranked.iloc[0]["candidate"])


def _candidate_map() -> dict[str, dict[str, object]]:
    candidates = [a_candidate(), *b_candidates(), *c_candidates()]
    return {str(candidate["candidate"]): candidate for candidate in candidates}


def stage_result_path(results_dir: Path, stage: str, warmup_days: int) -> Path:
    return results_dir / f"{stage}_W{warmup_days:03d}.csv"


def run_full(project_root: Path, workers: int) -> Path:
    input_path = problem_statement_path(project_root)
    if sha256(input_path) != INPUT_SHA256:
        raise ValueError("Problem A statement hash does not match the frozen model input")
    results_dir = project_root / "results" / "task-2"
    results_dir.mkdir(parents=True, exist_ok=True)
    candidate_map = _candidate_map()
    warmup_days = FIXED_WARMUP_DAYS
    tuning_candidates = [a_candidate(), *b_candidates(), *c_candidates()]
    tuning_tasks = [
        {
            "candidate": candidate,
            "seed": seed,
            "warmup_days": warmup_days,
            "measure_days": MEASURE_DAYS,
        }
        for candidate in tuning_candidates
        for seed in _seed_block(200_000, TUNING_REPLICATIONS)
    ]
    tuning_coarse = run_tasks(
        input_path,
        stage_result_path(results_dir, "tuning_coarse", warmup_days),
        tuning_tasks,
        workers,
        daily_only=False,
    )
    coarse_b_name = select_b(tuning_coarse)
    fine_candidates = b_fine_candidates(coarse_b_name)
    for candidate in fine_candidates:
        candidate_map[str(candidate["candidate"])] = candidate
    if fine_candidates:
        fine_tasks = [
            {
                "candidate": candidate,
                "seed": seed,
                "warmup_days": warmup_days,
                "measure_days": MEASURE_DAYS,
            }
            for candidate in fine_candidates
            for seed in _seed_block(200_000, TUNING_REPLICATIONS)
        ]
        tuning_fine = run_tasks(
            input_path,
            stage_result_path(results_dir, "tuning_fine", warmup_days),
            fine_tasks,
            workers,
            daily_only=False,
        )
        tuning = pd.concat([tuning_coarse, tuning_fine], ignore_index=True)
    else:
        tuning = tuning_coarse
    tuning.to_csv(
        stage_result_path(results_dir, "tuning_all", warmup_days),
        index=False,
        encoding="utf-8-sig",
    )
    best_b_name = select_b(tuning)
    best_c_name = select_c(tuning_coarse)

    selection_names = ["A", best_b_name] + ([best_c_name] if best_c_name else [])
    selection_tasks = [
        {
            "candidate": candidate_map[name],
            "seed": seed,
            "warmup_days": warmup_days,
            "measure_days": MEASURE_DAYS,
        }
        for name in selection_names
        for seed in _seed_block(300_000, SELECTION_REPLICATIONS)
    ]
    selection = run_tasks(
        input_path,
        stage_result_path(results_dir, "selection_replicates", warmup_days),
        selection_tasks,
        workers,
        daily_only=False,
    )
    c_upper = None
    c_qualified = False
    if best_c_name:
        pivot = selection.pivot(index="seed", columns="candidate", values="mean_response_min")
        c_upper = one_sided_upper((pivot[best_c_name] - pivot["A"]).dropna().to_numpy())
        c_qualified = c_upper <= 0
    eligible = ["A", best_b_name] + ([best_c_name] if c_qualified and best_c_name else [])
    main_policy = choose_main_policy(selection, eligible)

    decision = {
        "warmup_days": warmup_days,
        "best_b": candidate_map[best_b_name],
        "best_c": candidate_map[best_c_name] if best_c_name else None,
        "c_one_sided_95_upper_min": c_upper,
        "c_qualified": c_qualified,
        "eligible_daily_policies": eligible,
        "main_policy": candidate_map[main_policy],
        "selection_rule": "mean response first; if paired 95% CI includes zero, strict-4 rate, P95, fairness",
    }
    (results_dir / "selected_policy.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    final_names = list(dict.fromkeys(["A", best_b_name] + ([best_c_name] if c_qualified else [])))
    final_tasks = [
        {
            "candidate": candidate_map[name],
            "seed": seed,
            "warmup_days": warmup_days,
            "measure_days": MEASURE_DAYS,
        }
        for name in final_names
        for seed in _seed_block(400_000, FINAL_REPLICATIONS)
    ]
    final = run_tasks(
        input_path,
        stage_result_path(results_dir, "final_replicates", warmup_days),
        final_tasks,
        workers,
        daily_only=False,
    )

    metric_columns = [
        "mean_response_min",
        "mean_delay_penalty_yuan_per_call",
        "mean_daily_delay_penalty_yuan",
        "strict_4min_rate",
        "p90_response_min",
        "p95_response_min",
        "mean_wait_min",
        "wait_probability",
        "max_wait_min",
        "max_queue",
        "mean_end_backlog",
        "regional_mean_gap_min",
        "mean_ideal_chain_min",
        "p95_ideal_chain_min",
    ]
    summary_rows = []
    for candidate, group in final.groupby("candidate"):
        for metric in metric_columns:
            values = group[metric].to_numpy(dtype=float)
            mean = float(np.mean(values))
            half = float(stats.t.ppf(0.975, len(values) - 1) * stats.sem(values))
            summary_rows.append(
                {
                    "candidate": candidate,
                    "metric": metric,
                    "mean": mean,
                    "ci95_low": mean - half,
                    "ci95_high": mean + half,
                    "replications": len(values),
                }
            )
    pd.DataFrame(summary_rows).to_csv(
        results_dir / "final_summary.csv", index=False, encoding="utf-8-sig"
    )

    pivot = final.pivot(index="seed", columns="candidate", values="mean_response_min")
    paired_rows = []
    for candidate in final_names:
        if candidate == "A":
            continue
        differences = (pivot[candidate] - pivot["A"]).dropna().to_numpy()
        low, high = _paired_ci(differences)
        paired_rows.append(
            {
                "comparison": f"{candidate}-A",
                "mean_difference_min": float(np.mean(differences)),
                "ci95_low": low,
                "ci95_high": high,
                "replications": len(differences),
            }
        )
    pd.DataFrame(paired_rows).to_csv(
        results_dir / "final_paired_response.csv", index=False, encoding="utf-8-sig"
    )
    return results_dir / "selected_policy.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen A-problem task-one/two experiment")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workers", type=int, default=min(12, max(1, (os.cpu_count() or 2) - 1)))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected = run_full(args.project_root.resolve(), workers=args.workers)
    print(selected)


if __name__ == "__main__":
    main()
