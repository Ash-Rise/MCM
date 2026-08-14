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
from scipy.interpolate import PchipInterpolator

from ambulance_model import (
    DELAY_PENALTY_YUAN_PER_MINUTE,
    GOLDEN_RESPONSE_MINUTES,
    MINUTES_PER_DAY,
    Call,
    ProblemData,
    SimulationState,
    generate_calls,
    intraday_density,
    prepare_simulation_state,
    problem_statement_path,
    read_problem,
    sha256,
    simulate,
)


INPUT_SHA256 = "5F5079815AB8AD6592FEE7A4B0B8B01A5DF8865983A2871C324B6AB772C39F2D"
WARMUP_DAYS = 30
BETA = 4.0
DELTA = 2.0
DURATION_DOMAIN_HOURS = (0.5, 12.0)
INITIAL_DURATIONS_HOURS = (0.5, 1.0, 2.0, 4.0, 8.0, 12.0)
MAX_DURATION_NODES = 10
ADAPTIVE_BATCH_SIZE = 2
MIN_DURATION_SPACING_HOURS = 0.2
SURFACE_GRID_POINTS = 117
REPLICATIONS = 10
BASE_SEED = 600_000
EXTERNAL_COUNTS = tuple(range(7))
RESPONSE_SURFACE_METRICS = (
    "mean_response_min",
    "p95_response_min",
    "strict_4min_rate",
    "max_incident_queue",
)
SCOPED_RESPONSE_METRICS = (
    "incident_zone_mean_response_min",
    "nonincident_zone_mean_response_min",
)

_WORKER_DATA: ProblemData | None = None


def validate_duration(duration_hours: float) -> float:
    duration = float(duration_hours)
    low, high = DURATION_DOMAIN_HOURS
    if not math.isfinite(duration) or duration < low or duration > high:
        raise ValueError(f"Incident duration must lie in [{low}, {high}] hours")
    return duration


def _duration_mass(start_hour: float, duration_hours: float) -> float:
    duration_hours = validate_duration(duration_hours)
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
    duration_hours = validate_duration(duration_hours)
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
    duration_hours = validate_duration(duration_hours)
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


def nearest_external_sites(
    data: ProblemData,
    incident_zone: int,
    count: int,
) -> list[int]:
    if isinstance(incident_zone, bool) or not isinstance(incident_zone, (int, np.integer)):
        raise ValueError("Incident zone must be an integer index")
    if not 0 <= int(incident_zone) < len(data.zone_ids):
        raise ValueError("Incident zone is outside the demand-zone set")
    if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 0:
        raise ValueError("External ambulance count must be a nonnegative integer")

    distances = data.distance[int(incident_zone)]
    nearest_distance = float(np.min(distances))
    tied_sites = np.flatnonzero(np.isclose(distances, nearest_distance, rtol=0.0, atol=1e-12))
    return [int(tied_sites[index % len(tied_sites)]) for index in range(int(count))]


def _run_external_support(
    data: ProblemData,
    calls: list[Call],
    incident_zone: int,
    start_min: float,
    end_min: float,
    external_counts: tuple[int, ...] = EXTERNAL_COUNTS,
    initial_state: SimulationState | None = None,
) -> list[dict[str, object]]:
    digest = _call_digest(calls)
    multiplier = incident_rate_multiplier(incident_zone, start_min, end_min, len(data.zone_ids))
    original_fleet_size = int(np.sum(data.site_caps))
    if initial_state is None:
        initial_state = prepare_simulation_state(
            data,
            calls,
            strategy="B",
            beta=BETA,
            delta=DELTA,
            stop_min=start_min,
            rate_multiplier=multiplier,
            rate_multiplier_active_from=start_min,
        )
    rows: list[dict[str, object]] = []
    for count in external_counts:
        sites = nearest_external_sites(data, incident_zone, count)
        records, full_metrics = simulate(
            data,
            calls,
            strategy="B",
            beta=BETA,
            delta=DELTA,
            rate_multiplier=multiplier,
            rate_multiplier_active_from=start_min,
            external_sites=sites,
            external_activation_min=start_min,
            initial_state=initial_state,
        )
        rows.append(
            {
                "mode": "B_E",
                "external_count": int(count),
                "external_sites": "|".join(data.site_ids[site] for site in sites),
                "call_digest": digest,
                **summarize_incident(records, incident_zone, start_min, end_min),
                "external_dispatches": int((records["ambulance_id"] >= original_fleet_size).sum()),
                "max_daily_dispatches_per_ambulance": full_metrics[
                    "max_daily_dispatches_per_ambulance"
                ],
            }
        )
    return rows


def _run_external_support_group(
    data: ProblemData,
    scenarios: list[dict[str, object]],
    external_counts: tuple[int, ...] = EXTERNAL_COUNTS,
) -> list[dict[str, object]]:
    if not scenarios:
        return []
    start_min = float(scenarios[0]["start_min"])
    if any(not math.isclose(float(scenario["start_min"]), start_min) for scenario in scenarios):
        raise ValueError("Grouped external-support scenarios must share an incident start")

    first_zone = int(scenarios[0]["incident_zone"])
    first_calls = scenarios[0]["calls"]
    if not isinstance(first_calls, list):
        raise TypeError("Grouped external-support calls must be a list")
    first_multiplier = incident_rate_multiplier(
        first_zone,
        start_min,
        float(scenarios[0]["end_min"]),
        len(data.zone_ids),
    )
    shared_state = prepare_simulation_state(
        data,
        first_calls,
        strategy="B",
        beta=BETA,
        delta=DELTA,
        stop_min=start_min,
        rate_multiplier=first_multiplier,
        rate_multiplier_active_from=start_min,
    )

    rows: list[dict[str, object]] = []
    for scenario in scenarios:
        calls = scenario["calls"]
        if not isinstance(calls, list):
            raise TypeError("Grouped external-support calls must be a list")
        scenario_rows = _run_external_support(
            data,
            calls,
            incident_zone=int(scenario["incident_zone"]),
            start_min=float(scenario["start_min"]),
            end_min=float(scenario["end_min"]),
            external_counts=external_counts,
            initial_state=shared_state,
        )
        metadata = scenario.get("metadata", {})
        if not isinstance(metadata, dict):
            raise TypeError("Grouped external-support metadata must be a dictionary")
        rows.extend(
            {
                **row,
                **metadata,
            }
            for row in scenario_rows
        )
    return rows


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


def _external_scenario_worker(task: dict[str, object]) -> list[dict[str, object]]:
    if _WORKER_DATA is None:
        raise RuntimeError("Worker data is not initialized")
    zone = int(task["incident_zone"])
    duration = float(task["duration_hours"])
    seed = int(task["seed"])
    start_hour = float(task["start_hour"])
    start_min = WARMUP_DAYS * MINUTES_PER_DAY + start_hour * 60.0
    end_min = start_min + duration * 60.0
    calls = build_scenario_calls(_WORKER_DATA, zone, start_hour, duration, seed)
    counts = tuple(int(value) for value in task.get("external_counts", EXTERNAL_COUNTS))
    rows = _run_external_support(
        _WORKER_DATA,
        calls,
        incident_zone=zone,
        start_min=start_min,
        end_min=end_min,
        external_counts=counts,
    )
    return [
        {
            **row,
            "incident_zone": zone + 1,
            "duration_hours": duration,
            "start_hour": start_hour,
            "seed": seed,
        }
        for row in rows
    ]


def _build_external_tasks(
    scenarios: pd.DataFrame,
    seeds: tuple[int, ...],
    external_counts: tuple[int, ...],
) -> list[dict[str, object]]:
    tasks: list[dict[str, object]] = []
    for (duration, start_hour), group in scenarios.groupby(
        ["duration_hours", "start_hour"], sort=True
    ):
        incident_zones = tuple(
            sorted(int(zone) - 1 for zone in group["incident_zone"].tolist())
        )
        for seed in seeds:
            tasks.append(
                {
                    "duration_hours": float(duration),
                    "start_hour": float(start_hour),
                    "seed": int(seed),
                    "incident_zones": incident_zones,
                    "external_counts": external_counts,
                }
            )
    return tasks


def _external_scenario_group_worker(task: dict[str, object]) -> list[dict[str, object]]:
    if _WORKER_DATA is None:
        raise RuntimeError("Worker data is not initialized")
    duration = float(task["duration_hours"])
    seed = int(task["seed"])
    start_hour = float(task["start_hour"])
    start_min = WARMUP_DAYS * MINUTES_PER_DAY + start_hour * 60.0
    end_min = start_min + duration * 60.0
    counts = tuple(int(value) for value in task.get("external_counts", EXTERNAL_COUNTS))
    incident_zones = tuple(int(value) for value in task["incident_zones"])
    scenarios = []
    for zone in incident_zones:
        scenarios.append(
            {
                "incident_zone": zone,
                "start_min": start_min,
                "end_min": end_min,
                "calls": build_scenario_calls(
                    _WORKER_DATA,
                    zone,
                    start_hour,
                    duration,
                    seed,
                ),
                "metadata": {
                    "incident_zone": zone + 1,
                    "duration_hours": duration,
                    "start_hour": start_hour,
                    "seed": seed,
                },
            }
        )
    return _run_external_support_group(
        _WORKER_DATA,
        scenarios,
        external_counts=counts,
    )


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


def _ci95(values: np.ndarray) -> tuple[float, float, float]:
    mean = float(np.mean(values))
    half = 0.0 if len(values) == 1 else float(
        stats.t.ppf(0.975, len(values) - 1) * stats.sem(values)
    )
    return mean, mean - half, mean + half


def build_external_support_table(
    replicates: pd.DataFrame,
    expected_counts: tuple[int, ...] = EXTERNAL_COUNTS,
    require_all_zones: bool = True,
) -> pd.DataFrame:
    required = {
        "external_count",
        "call_digest",
        "incident_zone",
        "duration_hours",
        "start_hour",
        "seed",
        "calls",
        "mean_response_min",
        "mean_delay_penalty_yuan_per_call",
        "max_daily_dispatches_per_ambulance",
    }
    missing = required.difference(replicates.columns)
    if missing:
        raise ValueError(f"External-support evidence is missing columns: {sorted(missing)}")
    if replicates.empty:
        raise AssertionError("External-support evidence cannot be empty")
    if "mode" in replicates.columns and set(replicates["mode"]) != {"B_E"}:
        raise AssertionError("External-support evidence must use policy B_E")

    working = replicates.copy()
    scenario_keys = ["incident_zone", "duration_hours", "start_hour", "seed"]
    if working.duplicated([*scenario_keys, "external_count"]).any():
        raise AssertionError("External-support evidence contains duplicate vehicle-count rows")
    expected = set(expected_counts)
    for _, group in working.groupby(scenario_keys, sort=False):
        if set(group["external_count"]) != expected:
            raise AssertionError("Every external-support scenario must contain counts 0 through 6")
        if group["call_digest"].nunique() != 1 or group["calls"].nunique() != 1:
            raise AssertionError("External vehicle counts must receive identical calls")
    if require_all_zones:
        expected_zones = set(range(1, 11))
        for _, group in working.groupby(
            ["duration_hours", "start_hour", "seed", "external_count"], sort=False
        ):
            if set(group["incident_zone"]) != expected_zones:
                raise AssertionError("External-support evidence must cover all ten incident zones")
    if working["max_daily_dispatches_per_ambulance"].max() > 12:
        raise AssertionError("External-support evidence violated the daily dispatch cap")

    working["total_delay_penalty_yuan"] = (
        working["calls"].to_numpy(dtype=float)
        * working["mean_delay_penalty_yuan_per_call"].to_numpy(dtype=float)
    )
    for column in (
        "cumulative_response_gain_min",
        "marginal_response_gain_min",
        "avoided_penalty_yuan",
        "avoided_penalty_per_vehicle_yuan",
        "marginal_break_even_cost_yuan",
    ):
        working[column] = np.nan

    for _, group in working.groupby(scenario_keys, sort=False):
        ordered = group.sort_values("external_count")
        counts = ordered["external_count"].to_numpy(dtype=int)
        response = ordered["mean_response_min"].to_numpy(dtype=float)
        penalty = ordered["total_delay_penalty_yuan"].to_numpy(dtype=float)
        index = ordered.index
        working.loc[index, "cumulative_response_gain_min"] = response[0] - response
        working.loc[index, "avoided_penalty_yuan"] = penalty[0] - penalty
        positive = counts > 0
        working.loc[index[positive], "marginal_response_gain_min"] = response[:-1] - response[1:]
        working.loc[index[positive], "avoided_penalty_per_vehicle_yuan"] = (
            penalty[0] - penalty[positive]
        ) / counts[positive]
        working.loc[index[positive], "marginal_break_even_cost_yuan"] = penalty[:-1] - penalty[1:]

    return working.sort_values([*scenario_keys, "external_count"]).reset_index(drop=True)


EXTERNAL_SUMMARY_METRICS = (
    "mean_response_min",
    "cumulative_response_gain_min",
    "marginal_response_gain_min",
    "total_delay_penalty_yuan",
    "avoided_penalty_yuan",
    "avoided_penalty_per_vehicle_yuan",
    "marginal_break_even_cost_yuan",
    "external_dispatches",
)


def _summarize_external_groups(frame: pd.DataFrame, group_keys: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metrics = [metric for metric in EXTERNAL_SUMMARY_METRICS if metric in frame.columns]
    for group_key, group in frame.groupby(group_keys, sort=True):
        key_values = group_key if isinstance(group_key, tuple) else (group_key,)
        row: dict[str, object] = dict(zip(group_keys, key_values, strict=True))
        row["replications"] = int(
            group.loc[group["mean_response_min"].notna(), "seed"].nunique()
        )
        for metric in metrics:
            values = group[metric].dropna().to_numpy(dtype=float)
            row[f"{metric}_n"] = int(
                group.loc[group[metric].notna(), "seed"].nunique()
            )
            if len(values) == 0:
                mean = low = high = np.nan
            else:
                mean, low, high = _ci95(values)
            row[f"{metric}_mean"] = mean
            row[f"{metric}_ci95_low"] = low
            row[f"{metric}_ci95_high"] = high
        rows.append(row)
    return pd.DataFrame(rows)


def build_external_support_summaries(
    paired_replicates: pd.DataFrame,
    require_all_zones: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = {
        "incident_zone",
        "duration_hours",
        "seed",
        "external_count",
        "mean_response_min",
        "cumulative_response_gain_min",
        "marginal_response_gain_min",
        "total_delay_penalty_yuan",
        "avoided_penalty_yuan",
        "avoided_penalty_per_vehicle_yuan",
        "marginal_break_even_cost_yuan",
    }
    missing = required.difference(paired_replicates.columns)
    if missing:
        raise ValueError(f"Paired external-support evidence is missing columns: {sorted(missing)}")

    by_zone = _summarize_external_groups(
        paired_replicates,
        ["incident_zone", "duration_hours", "external_count"],
    )

    scenario_key = ["duration_hours", "seed", "external_count"]
    expected_zones = set(range(1, 11)) if require_all_zones else None
    for _, group in paired_replicates.groupby(scenario_key, sort=False):
        zones = set(group["incident_zone"])
        if expected_zones is None:
            expected_zones = zones
        if zones != expected_zones:
            raise AssertionError("Citywide external-support summaries require all ten incident zones")
    metrics = [metric for metric in EXTERNAL_SUMMARY_METRICS if metric in paired_replicates.columns]
    complete_blocks = (
        paired_replicates.loc[paired_replicates["mean_response_min"].notna()]
        .groupby(scenario_key)["incident_zone"]
        .nunique()
        .eq(len(expected_zones))
    )
    complete_keys = complete_blocks[complete_blocks].index.to_frame(index=False)
    complete_replicates = paired_replicates.merge(complete_keys, on=scenario_key, how="inner")
    citywide_seed = complete_replicates.groupby(scenario_key, as_index=False)[metrics].mean()
    citywide = _summarize_external_groups(
        citywide_seed,
        ["duration_hours", "external_count"],
    )
    citywide["incident_zone_scenarios"] = len(expected_zones)

    worst_rows: list[pd.Series] = []
    for _, group in by_zone.groupby(["duration_hours", "external_count"], sort=True):
        worst_index = group.sort_values(
            ["mean_response_min_mean", "incident_zone"],
            ascending=[False, True],
        ).index[0]
        worst_rows.append(by_zone.loc[worst_index])
    worst = pd.DataFrame(worst_rows).reset_index(drop=True)
    return by_zone, citywide, worst


def validate_external_support_evidence(
    replicates: pd.DataFrame,
    frozen_emergency: pd.DataFrame,
    expected_counts: tuple[int, ...] = EXTERNAL_COUNTS,
    require_all_zones: bool = True,
) -> pd.DataFrame:
    paired = build_external_support_table(
        replicates,
        expected_counts=expected_counts,
        require_all_zones=require_all_zones,
    )
    frozen = frozen_emergency.copy()
    if "mode" in frozen.columns:
        frozen = frozen[frozen["mode"] == "B_E"]
    keys = ["incident_zone", "duration_hours", "start_hour", "seed"]
    count_zero = paired[paired["external_count"] == 0]
    if frozen.duplicated(keys).any() or count_zero.duplicated(keys).any():
        raise AssertionError("Count-0 equivalence requires unique frozen B_E scenario rows")
    merged = count_zero.merge(frozen, on=keys, how="left", suffixes=("_external", "_frozen"), indicator=True)
    if len(merged) != len(count_zero) or not (merged["_merge"] == "both").all():
        raise AssertionError("External-support count-0 rows do not match frozen B_E scenario keys")

    exact_columns = ("call_digest", "calls", "max_daily_dispatches_per_ambulance")
    numeric_columns = (
        "mean_response_min",
        "p95_response_min",
        "strict_4min_rate",
        "mean_wait_min",
        "mean_delay_penalty_yuan_per_call",
        "incident_zone_calls",
        "incident_zone_mean_response_min",
        "nonincident_zone_calls",
        "nonincident_zone_mean_response_min",
        "max_incident_queue",
        "incident_end_backlog",
    )
    for column in exact_columns:
        left = f"{column}_external"
        right = f"{column}_frozen"
        if left in merged.columns and right in merged.columns:
            if not merged[left].equals(merged[right]):
                raise AssertionError("External-support count-0 rows do not match frozen B_E")
    for column in numeric_columns:
        left = f"{column}_external"
        right = f"{column}_frozen"
        if left in merged.columns and right in merged.columns:
            if not np.allclose(
                merged[left].to_numpy(dtype=float),
                merged[right].to_numpy(dtype=float),
                rtol=1e-12,
                atol=1e-12,
                equal_nan=True,
            ):
                raise AssertionError("External-support count-0 rows do not match frozen B_E")
    return paired


def build_duration_table(
    replicates: pd.DataFrame,
    metrics: tuple[str, ...] = RESPONSE_SURFACE_METRICS,
) -> pd.DataFrame:
    """Summarize each duration separately; cross-duration pooling is prohibited."""
    rows: list[dict[str, object]] = []
    pair_keys = ["incident_zone", "duration_hours", "start_hour", "seed"]
    for metric in metrics:
        pivot = replicates.pivot(index=pair_keys, columns="mode", values=metric).dropna()
        if not {"B_N", "B_E"}.issubset(pivot.columns):
            continue
        pivot = pivot.assign(difference=pivot["B_E"] - pivot["B_N"]).reset_index()
        for (zone, duration), group in pivot.groupby(
            ["incident_zone", "duration_hours"], sort=True
        ):
            seed_pairs = group.groupby("seed")[["B_N", "B_E", "difference"]].mean()
            baseline_mean, _, _ = _ci95(seed_pairs["B_N"].to_numpy(dtype=float))
            emergency_mean, _, _ = _ci95(seed_pairs["B_E"].to_numpy(dtype=float))
            difference_mean, low, high = _ci95(seed_pairs["difference"].to_numpy(dtype=float))
            rows.append(
                {
                    "incident_zone": int(zone),
                    "duration_hours": float(duration),
                    "metric": metric,
                    "B_N_mean": baseline_mean,
                    "B_E_mean": emergency_mean,
                    "mean_difference_B_E_minus_B_N": difference_mean,
                    "ci95_low": low,
                    "ci95_high": high,
                    "replications": len(seed_pairs),
                }
            )
    return pd.DataFrame(rows)


def build_citywide_duration_table(
    replicates: pd.DataFrame,
    metric: str = "mean_response_min",
) -> pd.DataFrame:
    """Summarize the ten incident-zone scenarios within each seed at every duration."""
    key = ["duration_hours", "seed", "incident_zone", "mode"]
    if replicates.duplicated(key).any():
        raise AssertionError("Citywide duration effects require one row per scenario and mode")
    expected_zones = set(range(1, 11))
    for _, group in replicates.groupby(["duration_hours", "seed", "mode"], sort=False):
        if set(group["incident_zone"]) != expected_zones:
            raise AssertionError("Citywide duration effects require all ten incident-zone scenarios")
    if not (replicates.groupby(key[:-1])["mode"].nunique() == 2).all():
        raise AssertionError("Citywide duration effects require paired B_N and B_E modes")
    if metric not in replicates.columns:
        raise ValueError(f"Missing citywide duration metric: {metric}")

    seed_means = (
        replicates.groupby(["duration_hours", "seed", "mode"], as_index=False)[metric]
        .mean()
        .dropna()
    )
    pivot = seed_means.pivot(
        index=["duration_hours", "seed"], columns="mode", values=metric
    ).dropna()
    rows: list[dict[str, object]] = []
    for duration, group in pivot.reset_index().groupby("duration_hours", sort=True):
        differences = (group["B_E"] - group["B_N"]).to_numpy(dtype=float)
        _, low, high = _ci95(differences)
        rows.append(
            {
                "duration_hours": float(duration),
                "metric": metric,
                "B_N_mean": float(group["B_N"].mean()),
                "B_E_mean": float(group["B_E"].mean()),
                "mean_difference_B_E_minus_B_N": float(np.mean(differences)),
                "ci95_low": low,
                "ci95_high": high,
                "replications": len(group),
                "incident_zone_scenarios": 10,
            }
        )
    return pd.DataFrame(rows)


def build_scenarios(data: ProblemData, durations: list[float] | tuple[float, ...]) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []
    for duration_value in sorted({validate_duration(value) for value in durations}):
        start_hour = worst_start_hour(duration_value)
        duration_mass = _duration_mass(start_hour, duration_value)
        for zone in range(1, len(data.zone_ids) + 1):
            rows.append(
                {
                    "incident_zone": zone,
                    "duration_hours": duration_value,
                    "start_hour": start_hour,
                    "expected_extra_calls": 4.0 * float(data.demand[zone - 1]) * duration_mass,
                }
            )
    return pd.DataFrame(rows)


def _unit_scale_metric(metric: str, values: np.ndarray) -> float:
    if metric == "strict_4min_rate":
        return 1.0
    finite = np.abs(values[np.isfinite(values)])
    return max(1.0, float(np.quantile(finite, 0.9))) if len(finite) else 1.0


def build_acquisition_curves(
    replicates: pd.DataFrame,
    metrics: tuple[str, ...] = RESPONSE_SURFACE_METRICS,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for zone in sorted(replicates["incident_zone"].unique()):
        zone_frame = replicates[replicates["incident_zone"] == zone]
        for metric in metrics:
            scale = _unit_scale_metric(metric, zone_frame[metric].to_numpy(dtype=float))
            for mode in ("B_N", "B_E"):
                mode_frame = zone_frame[zone_frame["mode"] == mode]
                for duration, group in mode_frame.groupby("duration_hours", sort=True):
                    seed_values = group.groupby("seed")[metric].mean().dropna().to_numpy(dtype=float)
                    if len(seed_values) == 0:
                        continue
                    mean, low, high = _ci95(seed_values / scale)
                    rows.append(
                        {
                            "curve_id": f"R{int(zone)}:{mode}:{metric}",
                            "incident_zone": int(zone),
                            "mode": mode,
                            "metric": metric,
                            "duration_hours": float(duration),
                            "mean": mean,
                            "ci_half_width": 0.5 * (high - low),
                        }
                    )
            pivot = zone_frame.pivot(
                index=["duration_hours", "seed"], columns="mode", values=metric
            ).dropna()
            if {"B_N", "B_E"}.issubset(pivot.columns):
                difference = (pivot["B_E"] - pivot["B_N"]).reset_index(name="difference")
                for duration, group in difference.groupby("duration_hours", sort=True):
                    values = group["difference"].to_numpy(dtype=float) / scale
                    mean, low, high = _ci95(values)
                    rows.append(
                        {
                            "curve_id": f"R{int(zone)}:B_E-B_N:{metric}",
                            "incident_zone": int(zone),
                            "mode": "B_E-B_N",
                            "metric": metric,
                            "duration_hours": float(duration),
                            "mean": mean,
                            "ci_half_width": 0.5 * (high - low),
                        }
                    )
    return pd.DataFrame(rows)


def select_adaptive_midpoints(
    acquisition_curves: pd.DataFrame,
    sampled_durations: np.ndarray | list[float] | tuple[float, ...],
    max_new_points: int = ADAPTIVE_BATCH_SIZE,
) -> pd.DataFrame:
    sampled = np.array(sorted({validate_duration(value) for value in sampled_durations}), dtype=float)
    if len(sampled) < 2:
        raise ValueError("Adaptive design requires at least two duration nodes")
    intervals: list[dict[str, object]] = []
    for left, right in zip(sampled[:-1], sampled[1:], strict=True):
        if right - left < 2.0 * MIN_DURATION_SPACING_HOURS:
            continue
        midpoint = 0.5 * (left + right)
        local = acquisition_curves[
            acquisition_curves["duration_hours"].isin([left, right])
        ]
        uncertainty = float(local["ci_half_width"].max()) if not local.empty else 0.0
        curvature = 0.0
        for _, curve in acquisition_curves.groupby("curve_id", sort=False):
            ordered = curve.sort_values("duration_hours")
            x = ordered["duration_hours"].to_numpy(dtype=float)
            y = ordered["mean"].to_numpy(dtype=float)
            if left not in x or right not in x:
                continue
            left_index = int(np.where(x == left)[0][0])
            right_index = int(np.where(x == right)[0][0])
            slopes: list[float] = []
            if left_index > 0:
                slopes.append(abs((y[left_index] - y[left_index - 1]) / (x[left_index] - x[left_index - 1])))
            slopes.append(abs((y[right_index] - y[left_index]) / (right - left)))
            if right_index + 1 < len(x):
                slopes.append(abs((y[right_index + 1] - y[right_index]) / (x[right_index + 1] - x[right_index])))
            if len(slopes) >= 2:
                curvature = max(curvature, float(np.max(np.abs(np.diff(slopes)))))
        intervals.append(
            {
                "duration_hours": midpoint,
                "left_hours": left,
                "right_hours": right,
                "curvature_score": curvature,
                "uncertainty_score": uncertainty,
            }
        )
    if not intervals or max_new_points <= 0:
        return pd.DataFrame(columns=["duration_hours", "reason", "acquisition_score"])
    candidates = pd.DataFrame(intervals)
    selected_indices: list[int] = []
    for column in ("curvature_score", "uncertainty_score"):
        remaining = candidates.drop(index=selected_indices)
        if remaining.empty or len(selected_indices) >= max_new_points:
            break
        if column == "uncertainty_score":
            ranked = remaining.sort_values(
                [column, "duration_hours"], ascending=[False, False]
            )
            selected_indices.append(int(ranked.index[0]))
        else:
            selected_indices.append(int(remaining[column].idxmax()))
    if len(selected_indices) < max_new_points:
        remaining = candidates.drop(index=selected_indices).copy()
        remaining["fallback_score"] = (
            remaining["right_hours"] - remaining["left_hours"]
        )
        selected_indices.extend(
            remaining.nlargest(max_new_points - len(selected_indices), "fallback_score").index.tolist()
        )
    selected = candidates.loc[selected_indices].copy()
    selected["reason"] = np.where(
        selected["curvature_score"] >= selected["uncertainty_score"],
        "high_curvature",
        "high_uncertainty",
    )
    selected["acquisition_score"] = selected[["curvature_score", "uncertainty_score"]].max(axis=1)
    return selected.sort_values("duration_hours").reset_index(drop=True)


def _surface_from_seed_curves(
    sampled: pd.DataFrame,
    evaluation_grid: np.ndarray,
    value_column: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    sampled_nodes = np.sort(sampled["duration_hours"].unique())
    for seed, seed_frame in sampled.groupby("seed", sort=True):
        ordered = seed_frame.sort_values("duration_hours")
        x = ordered["duration_hours"].to_numpy(dtype=float)
        y = ordered[value_column].to_numpy(dtype=float)
        if len(x) != len(sampled_nodes):
            continue
        interpolator = PchipInterpolator(x, y, extrapolate=False)
        for duration, value in zip(evaluation_grid, interpolator(evaluation_grid), strict=True):
            rows.append({"seed": int(seed), "duration_hours": float(duration), "value": float(value)})
    return pd.DataFrame(rows)


def build_response_surfaces(
    replicates: pd.DataFrame,
    evaluation_grid: np.ndarray | None = None,
    metrics: tuple[str, ...] = RESPONSE_SURFACE_METRICS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sampled_nodes = np.sort(replicates["duration_hours"].unique())
    if evaluation_grid is None:
        evaluation_grid = np.unique(
            np.concatenate(
                (
                    np.linspace(
                        DURATION_DOMAIN_HOURS[0],
                        DURATION_DOMAIN_HOURS[1],
                        SURFACE_GRID_POINTS,
                    ),
                    sampled_nodes,
                )
            )
        )
    grid = np.array([validate_duration(value) for value in evaluation_grid], dtype=float)
    absolute_rows: list[dict[str, object]] = []
    paired_rows: list[dict[str, object]] = []
    for zone in sorted(replicates["incident_zone"].unique()):
        zone_frame = replicates[replicates["incident_zone"] == zone]
        for metric in metrics:
            for mode in ("B_N", "B_E"):
                sampled = zone_frame[zone_frame["mode"] == mode][
                    ["duration_hours", "seed", metric]
                ].dropna()
                curves = _surface_from_seed_curves(sampled, grid, metric)
                for duration, group in curves.groupby("duration_hours", sort=True):
                    mean, low, high = _ci95(group["value"].to_numpy(dtype=float))
                    absolute_rows.append(
                        {
                            "incident_zone": int(zone),
                            "mode": mode,
                            "metric": metric,
                            "duration_hours": float(duration),
                            "mean": mean,
                            "ci95_low": low,
                            "ci95_high": high,
                            "replications": len(group),
                            "sampled_node": bool(np.any(np.isclose(duration, sampled_nodes))),
                        }
                    )
            pivot = zone_frame.pivot(
                index=["duration_hours", "seed"], columns="mode", values=metric
            ).dropna()
            differences = pivot.assign(value=pivot["B_E"] - pivot["B_N"])["value"].reset_index()
            curves = _surface_from_seed_curves(differences, grid, "value")
            for duration, group in curves.groupby("duration_hours", sort=True):
                mean, low, high = _ci95(group["value"].to_numpy(dtype=float))
                paired_rows.append(
                    {
                        "incident_zone": int(zone),
                        "metric": metric,
                        "duration_hours": float(duration),
                        "mean_difference_B_E_minus_B_N": mean,
                        "ci95_low": low,
                        "ci95_high": high,
                        "replications": len(group),
                        "sampled_node": bool(np.any(np.isclose(duration, sampled_nodes))),
                    }
                )
    return pd.DataFrame(absolute_rows), pd.DataFrame(paired_rows)


def build_scoped_paired_surfaces(
    replicates: pd.DataFrame,
    evaluation_grid: np.ndarray | None = None,
    metrics: tuple[str, ...] = SCOPED_RESPONSE_METRICS,
) -> pd.DataFrame:
    """Pool calls from all ten incident-zone scenarios within each seed and duration."""
    key = ["duration_hours", "seed", "incident_zone", "mode"]
    if replicates.duplicated(key).any():
        raise AssertionError("Scoped effects require one row per incident-zone scenario and mode")
    expected_zones = set(range(1, 11))
    for _, group in replicates.groupby(["duration_hours", "seed", "mode"], sort=False):
        if set(group["incident_zone"]) != expected_zones:
            raise AssertionError("Scoped effects require all ten incident-zone scenarios")
    if not (replicates.groupby(key[:-1])["mode"].nunique() == 2).all():
        raise AssertionError("Scoped effects require paired B_N and B_E modes")

    sampled_nodes = np.sort(replicates["duration_hours"].unique())
    if evaluation_grid is None:
        evaluation_grid = np.unique(
            np.concatenate(
                (
                    np.linspace(
                        DURATION_DOMAIN_HOURS[0],
                        DURATION_DOMAIN_HOURS[1],
                        SURFACE_GRID_POINTS,
                    ),
                    sampled_nodes,
                )
            )
        )
    grid = np.array([validate_duration(value) for value in evaluation_grid], dtype=float)
    rows: list[dict[str, object]] = []
    for metric in metrics:
        count_column = metric.replace("mean_response_min", "calls")
        required = {metric, count_column}
        if not required.issubset(replicates.columns):
            raise ValueError(f"Scoped metric requires columns: {sorted(required)}")
        call_counts = replicates.pivot(index=key[:-1], columns="mode", values=count_column)
        if call_counts.isna().any().any() or not np.allclose(
            call_counts["B_N"], call_counts["B_E"], rtol=0.0, atol=0.0
        ):
            raise AssertionError("Paired policies must have identical scoped call counts")

        working = replicates[[*key, count_column, metric]].copy()
        counts = working[count_column].to_numpy(dtype=float)
        values = working[metric].to_numpy(dtype=float)
        if np.any(counts < 0) or np.any(~np.isclose(counts, np.round(counts))):
            raise AssertionError("Scoped call counts must be nonnegative integers")
        invalid = ((counts == 0) & np.isfinite(values)) | ((counts > 0) & ~np.isfinite(values))
        if np.any(invalid):
            raise AssertionError("Scoped means must be defined exactly when scoped calls are positive")
        working["weighted_response_sum"] = counts * np.nan_to_num(values, nan=0.0)
        pooled = working.groupby(["duration_hours", "seed", "mode"], as_index=False).agg(
            scoped_calls=(count_column, "sum"),
            weighted_response_sum=("weighted_response_sum", "sum"),
        )
        pooled[metric] = pooled["weighted_response_sum"] / pooled["scoped_calls"].replace(0, np.nan)
        pivot = pooled.pivot(
            index=["duration_hours", "seed"], columns="mode", values=metric
        ).dropna()
        differences = pivot.assign(value=pivot["B_E"] - pivot["B_N"])["value"].reset_index()
        curves = _surface_from_seed_curves(differences, grid, "value")
        for duration, group in curves.groupby("duration_hours", sort=True):
            mean, low, high = _ci95(group["value"].to_numpy(dtype=float))
            rows.append(
                {
                    "metric": metric,
                    "duration_hours": float(duration),
                    "mean_difference_B_E_minus_B_N": mean,
                    "ci95_low": low,
                    "ci95_high": high,
                    "replications": len(group),
                    "incident_zone_scenarios": 10,
                    "sampled_node": bool(np.any(np.isclose(duration, sampled_nodes))),
                }
            )
    return pd.DataFrame(rows)


def _run_scenarios(
    input_path: Path,
    scenarios: pd.DataFrame,
    workers: int,
) -> pd.DataFrame:
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
    return replicates


def _run_external_scenarios(
    input_path: Path,
    scenarios: pd.DataFrame,
    workers: int,
    seeds: tuple[int, ...],
    external_counts: tuple[int, ...],
) -> pd.DataFrame:
    tasks = _build_external_tasks(scenarios, seeds, external_counts)
    started = time.time()
    rows: list[dict[str, object]] = []
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(str(input_path),),
    ) as executor:
        futures = [executor.submit(_external_scenario_group_worker, task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), start=1):
            rows.extend(future.result())
            if completed == 1 or completed % max(1, len(tasks) // 20) == 0 or completed == len(tasks):
                elapsed = time.time() - started
                print(
                    f"[task-3 external] {completed}/{len(tasks)} scenarios, elapsed={elapsed:.1f}s",
                    flush=True,
                )
    replicates = pd.DataFrame(rows).sort_values(
        ["incident_zone", "duration_hours", "seed", "external_count"]
    )
    expected_rows = len(scenarios) * len(seeds) * len(external_counts)
    if len(replicates) != expected_rows:
        raise AssertionError(
            f"Expected {expected_rows} external-support rows, received {len(replicates)}"
        )
    scenario_keys = ["incident_zone", "duration_hours", "seed"]
    if not (
        replicates.groupby(scenario_keys)["external_count"].nunique() == len(external_counts)
    ).all():
        raise AssertionError("Every external-support scenario must contain every vehicle count")
    if not (replicates.groupby(scenario_keys)["call_digest"].nunique() == 1).all():
        raise AssertionError("External-support vehicle counts did not receive identical calls")
    if replicates["max_daily_dispatches_per_ambulance"].max() > 12:
        raise AssertionError("External-support experiment violated the daily dispatch cap")
    return replicates


def _validate_reuse_evidence(replicates: pd.DataFrame, scenarios: pd.DataFrame) -> None:
    required_columns = {
        "mode",
        "incident_zone",
        "duration_hours",
        "seed",
        "call_digest",
        "calls",
        "incident_zone_calls",
        "nonincident_zone_calls",
        "max_incident_queue",
        "incident_end_backlog",
        "max_daily_dispatches_per_ambulance",
    }
    missing = required_columns.difference(replicates.columns)
    if missing:
        raise AssertionError(f"Task 3 reuse evidence is missing fields: {sorted(missing)}")
    durations = sorted(float(value) for value in replicates["duration_hours"].unique())
    if not set(INITIAL_DURATIONS_HOURS).issubset(durations):
        raise AssertionError("Task 3 reuse evidence is missing an initial duration node")
    if set(replicates["incident_zone"]) != set(range(1, 11)):
        raise AssertionError("Task 3 reuse evidence must cover all ten incident zones")
    if set(replicates["seed"]) != set(range(BASE_SEED, BASE_SEED + REPLICATIONS)):
        raise AssertionError("Task 3 reuse seed block has drifted")
    if set(replicates["mode"]) != {"B_N", "B_E"}:
        raise AssertionError("Task 3 reuse policy modes have drifted")

    pair_keys = ["incident_zone", "duration_hours", "seed"]
    if replicates.duplicated([*pair_keys, "mode"]).any():
        raise AssertionError("Task 3 reuse evidence contains duplicate policy rows")
    if not (replicates.groupby(pair_keys)["mode"].nunique() == 2).all():
        raise AssertionError("Task 3 reuse evidence contains an incomplete B_N/B_E pair")
    if not (replicates.groupby(pair_keys)["call_digest"].nunique() == 1).all():
        raise AssertionError("Paired Task 3 reuse policies did not receive identical calls")
    expected_rows = len(durations) * 10 * REPLICATIONS * 2
    if len(replicates) != expected_rows:
        raise AssertionError(
            f"Task 3 reuse expected {expected_rows} rows, received {len(replicates)}"
        )
    if replicates["max_daily_dispatches_per_ambulance"].max() > 12:
        raise AssertionError("Task 3 reuse violated the per-ambulance daily dispatch cap")
    boundary_columns = [
        "calls",
        "incident_zone_calls",
        "nonincident_zone_calls",
        "max_incident_queue",
        "incident_end_backlog",
    ]
    if replicates[boundary_columns].isna().any().any():
        raise AssertionError("Task 3 reuse incident-window boundary fields contain missing values")

    scenario_keys = ["incident_zone", "duration_hours"]
    if scenarios.duplicated(scenario_keys).any():
        raise AssertionError("Task 3 reuse scenarios contain duplicate duration-zone rows")
    if len(scenarios) != len(durations) * 10:
        raise AssertionError("Task 3 reuse scenario design is incomplete")
    if set(scenarios["incident_zone"]) != set(range(1, 11)):
        raise AssertionError("Task 3 reuse scenarios do not cover all ten incident zones")
    if set(scenarios["duration_hours"]) != set(durations):
        raise AssertionError("Task 3 reuse scenario and replicate duration nodes differ")


def validate_initial_reuse(replicates: pd.DataFrame, scenarios: pd.DataFrame) -> None:
    durations = set(float(value) for value in replicates["duration_hours"].unique())
    if durations != set(INITIAL_DURATIONS_HOURS):
        raise AssertionError("Frozen Task 3 reuse must contain exactly the six initial duration nodes")
    _validate_reuse_evidence(replicates, scenarios)
    if len(replicates) != 1_200:
        raise AssertionError(f"Frozen Task 3 reuse expected 1200 rows, received {len(replicates)}")


def _write_outputs(output: Path, scenarios: pd.DataFrame, replicates: pd.DataFrame) -> Path:
    scenarios.sort_values(["incident_zone", "duration_hours"]).to_csv(
        output / "scenarios.csv", index=False, encoding="utf-8-sig"
    )
    replicates = replicates.sort_values(["incident_zone", "duration_hours", "seed", "mode"])
    replicates.to_csv(output / "replicates.csv", index=False, encoding="utf-8-sig")
    summary, paired = _summaries(replicates)
    summary.to_csv(output / "summary.csv", index=False, encoding="utf-8-sig")
    paired.to_csv(output / "paired_effects.csv", index=False, encoding="utf-8-sig")
    build_duration_table(replicates).to_csv(
        output / "duration_table.csv", index=False, encoding="utf-8-sig"
    )
    build_citywide_duration_table(replicates).to_csv(
        output / "citywide_duration_table.csv", index=False, encoding="utf-8-sig"
    )
    surfaces, paired_surfaces = build_response_surfaces(replicates)
    surfaces.to_csv(output / "response_surfaces.csv", index=False, encoding="utf-8-sig")
    paired_surfaces.to_csv(
        output / "paired_response_surfaces.csv", index=False, encoding="utf-8-sig"
    )
    build_scoped_paired_surfaces(replicates).to_csv(
        output / "scoped_paired_response_surfaces.csv", index=False, encoding="utf-8-sig"
    )
    return output / "summary.csv"


def _write_external_outputs(
    output: Path,
    replicates: pd.DataFrame,
    frozen_emergency: pd.DataFrame,
    expected_counts: tuple[int, ...] = EXTERNAL_COUNTS,
    require_all_zones: bool = True,
) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    ordered = replicates.sort_values(
        ["incident_zone", "duration_hours", "seed", "external_count"]
    ).reset_index(drop=True)
    paired = validate_external_support_evidence(
        ordered,
        frozen_emergency,
        expected_counts=expected_counts,
        require_all_zones=require_all_zones,
    )
    by_zone, citywide, worst = build_external_support_summaries(
        paired,
        require_all_zones=require_all_zones,
    )
    ordered.to_csv(output / "replicates.csv", index=False, encoding="utf-8-sig")
    paired.to_csv(output / "paired_gains.csv", index=False, encoding="utf-8-sig")
    by_zone.to_csv(
        output / "external_support_by_zone_duration.csv",
        index=False,
        encoding="utf-8-sig",
    )
    citywide.to_csv(
        output / "external_support_citywide.csv",
        index=False,
        encoding="utf-8-sig",
    )
    worst.to_csv(
        output / "external_support_worst_zone.csv",
        index=False,
        encoding="utf-8-sig",
    )
    return output / "external_support_citywide.csv"


def run_full(project_root: Path, workers: int) -> Path:
    input_path = problem_statement_path(project_root)
    if sha256(input_path) != INPUT_SHA256:
        raise ValueError("Problem A statement hash does not match the frozen model input")
    data = read_problem(input_path)
    output = project_root / "results" / "task-3"
    output.mkdir(parents=True, exist_ok=True)

    initial_scenarios = build_scenarios(data, list(INITIAL_DURATIONS_HOURS))
    replicate_path = output / "replicates.csv"
    if replicate_path.exists():
        existing = pd.read_csv(replicate_path)
        scenario_path = output / "scenarios.csv"
        if not scenario_path.exists():
            raise FileNotFoundError("Task 3 replicates exist without their scenario design")
        scenarios = pd.read_csv(scenario_path)
        existing_durations = set(existing["duration_hours"].unique())
        if existing_durations == set(INITIAL_DURATIONS_HOURS):
            validate_initial_reuse(existing, scenarios)
            replicates = existing
            print("[task-3] Reusing validated initial duration nodes", flush=True)
        elif set(INITIAL_DURATIONS_HOURS).issubset(existing_durations):
            _validate_reuse_evidence(existing, scenarios)
            replicates = existing
            print("[task-3] Resuming from validated adaptive duration nodes", flush=True)
        else:
            raise AssertionError("Existing Task 3 evidence cannot be reused safely")
    else:
        replicates = _run_scenarios(input_path, initial_scenarios, workers)
        scenarios = initial_scenarios

    acquisitions: list[pd.DataFrame] = []
    while len(set(replicates["duration_hours"].unique())) < MAX_DURATION_NODES:
        sampled = np.sort(replicates["duration_hours"].unique())
        curves = build_acquisition_curves(replicates)
        remaining = MAX_DURATION_NODES - len(sampled)
        selected = select_adaptive_midpoints(
            curves,
            sampled,
            max_new_points=min(ADAPTIVE_BATCH_SIZE, remaining),
        )
        if selected.empty:
            break
        selected.insert(0, "round", len(acquisitions) + 1)
        acquisitions.append(selected)
        new_scenarios = build_scenarios(data, selected["duration_hours"].tolist())
        new_replicates = _run_scenarios(input_path, new_scenarios, workers)
        scenarios = pd.concat([scenarios, new_scenarios], ignore_index=True).drop_duplicates(
            ["incident_zone", "duration_hours"]
        )
        replicates = pd.concat([replicates, new_replicates], ignore_index=True).drop_duplicates(
            ["incident_zone", "duration_hours", "seed", "mode"]
        )
        _write_outputs(output, scenarios, replicates)

    if acquisitions:
        pd.concat(acquisitions, ignore_index=True).to_csv(
            output / "adaptive_design.csv", index=False, encoding="utf-8-sig"
        )
    return _write_outputs(output, scenarios, replicates)


def run_external_support(
    project_root: Path,
    workers: int,
    incident_zone: int | None = None,
    duration_hours: float | None = None,
    seed: int | None = None,
    external_counts: tuple[int, ...] = EXTERNAL_COUNTS,
) -> Path:
    input_path = problem_statement_path(project_root)
    if sha256(input_path) != INPUT_SHA256:
        raise ValueError("Problem A statement hash does not match the frozen model input")
    if 0 not in external_counts:
        raise ValueError("External-support experiments must include count 0")
    if len(set(external_counts)) != len(external_counts):
        raise ValueError("External ambulance counts must be unique")
    for count in external_counts:
        if count not in EXTERNAL_COUNTS:
            raise ValueError("External ambulance counts must lie between 0 and 6")

    task3_output = project_root / "results" / "task-3"
    scenarios = pd.read_csv(task3_output / "scenarios.csv")
    if incident_zone is not None:
        if not 1 <= incident_zone <= 10:
            raise ValueError("Incident zone must lie between 1 and 10")
        scenarios = scenarios[scenarios["incident_zone"] == incident_zone]
    if duration_hours is not None:
        duration = validate_duration(duration_hours)
        scenarios = scenarios[np.isclose(scenarios["duration_hours"], duration)]
    if scenarios.empty:
        raise ValueError("No frozen Task 3 scenario matches the requested external-support slice")

    seeds = (seed,) if seed is not None else tuple(range(BASE_SEED, BASE_SEED + REPLICATIONS))
    replicates = _run_external_scenarios(
        input_path,
        scenarios,
        workers,
        seeds=seeds,
        external_counts=tuple(sorted(external_counts)),
    )
    frozen = pd.read_csv(task3_output / "replicates.csv")
    full_design = (
        incident_zone is None
        and duration_hours is None
        and seed is None
        and tuple(sorted(external_counts)) == EXTERNAL_COUNTS
    )
    output = task3_output / "external-support"
    if not full_design:
        output = output / "p1"
    return _write_external_outputs(
        output,
        replicates,
        frozen,
        expected_counts=tuple(sorted(external_counts)),
        require_all_zones=incident_zone is None,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Task 3 emergency dispatch scenarios")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workers", type=int, default=min(12, max(1, (os.cpu_count() or 2) - 1)))
    parser.add_argument("--external-support", action="store_true")
    parser.add_argument("--external-zone", type=int)
    parser.add_argument("--external-duration", type=float)
    parser.add_argument("--external-seed", type=int)
    parser.add_argument("--external-counts", type=int, nargs="+")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    if args.external_support:
        counts = EXTERNAL_COUNTS if args.external_counts is None else tuple(args.external_counts)
        print(
            run_external_support(
                project_root,
                args.workers,
                incident_zone=args.external_zone,
                duration_hours=args.external_duration,
                seed=args.external_seed,
                external_counts=counts,
            )
        )
    else:
        print(run_full(project_root, args.workers))


if __name__ == "__main__":
    main()
