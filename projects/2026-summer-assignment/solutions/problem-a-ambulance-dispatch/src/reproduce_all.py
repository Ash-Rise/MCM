from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from scipy import stats

from ambulance_model import DAILY_CAP, problem_statement_path, read_problem, sha256, solve_q1
from run_emergency_experiments import _summaries as emergency_summaries
from run_emergency_experiments import (
    BASE_SEED,
    INITIAL_DURATIONS_HOURS,
    MAX_DURATION_NODES,
    REPLICATIONS,
    RESPONSE_SURFACE_METRICS,
    build_citywide_duration_table,
    build_duration_table,
    build_response_surfaces,
    build_scoped_paired_surfaces,
)


INPUT_SHA256 = "5F5079815AB8AD6592FEE7A4B0B8B01A5DF8865983A2871C324B6AB772C39F2D"
Q2_CANDIDATES = ("A", "B_beta4_delta2", "C_r001000_tau7")
LEGACY_Q3_EVIDENCE_FILENAMES = (
    "aggregate_absolute_metrics.csv",
    "aggregate_paired_effects.csv",
    "paper_metrics.csv",
)
Q2_METRICS = (
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
)
def _assert_close_frame(actual: pd.DataFrame, expected: pd.DataFrame, keys: list[str]) -> None:
    actual = actual.sort_values(keys).reset_index(drop=True)
    expected = expected.sort_values(keys).reset_index(drop=True)
    assert_frame_equal(actual, expected, check_dtype=False, rtol=1e-10, atol=1e-10)


def _paired_ci(values: np.ndarray) -> tuple[float, float]:
    mean = float(np.mean(values))
    half = float(stats.t.ppf(0.975, len(values) - 1) * stats.sem(values))
    return mean - half, mean + half


def remove_legacy_q3_outputs(output: Path) -> list[str]:
    removed: list[str] = []
    for name in LEGACY_Q3_EVIDENCE_FILENAMES:
        path = output / name
        if path.is_file():
            path.unlink()
            removed.append(name)
    return removed


def q2_aggregates(replicates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    for candidate, group in replicates.groupby("candidate"):
        for metric in Q2_METRICS:
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

    pivot = replicates.pivot(index="seed", columns="candidate", values="mean_response_min")
    paired_rows: list[dict[str, object]] = []
    for candidate in Q2_CANDIDATES[1:]:
        differences = (pivot[candidate] - pivot["A"]).dropna().to_numpy(dtype=float)
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
    return pd.DataFrame(summary_rows), pd.DataFrame(paired_rows)


def rebuild_stage(project_root: Path, scope: str) -> None:
    q2_dir = project_root / "results" / "task-2"
    q2_replicates = pd.read_csv(q2_dir / "final_replicates_W030.csv")
    q2_summary, q2_paired = q2_aggregates(q2_replicates)
    q2_summary.to_csv(q2_dir / "final_summary.csv", index=False, encoding="utf-8-sig")
    q2_paired.to_csv(q2_dir / "final_paired_response.csv", index=False, encoding="utf-8-sig")

    if scope == "q1-q2":
        return
    if scope != "all":
        raise ValueError(f"Unknown rebuild scope: {scope}")

    q3_dir = project_root / "results" / "task-3"
    remove_legacy_q3_outputs(q3_dir)
    q3_replicates = pd.read_csv(q3_dir / "replicates.csv")
    q3_summary, q3_paired = emergency_summaries(q3_replicates)
    q3_summary.to_csv(q3_dir / "summary.csv", index=False, encoding="utf-8-sig")
    q3_paired.to_csv(q3_dir / "paired_effects.csv", index=False, encoding="utf-8-sig")
    build_duration_table(q3_replicates).to_csv(
        q3_dir / "duration_table.csv", index=False, encoding="utf-8-sig"
    )
    build_citywide_duration_table(q3_replicates).to_csv(
        q3_dir / "citywide_duration_table.csv", index=False, encoding="utf-8-sig"
    )
    q3_surfaces, q3_paired_surfaces = build_response_surfaces(q3_replicates)
    q3_surfaces.to_csv(
        q3_dir / "response_surfaces.csv", index=False, encoding="utf-8-sig"
    )
    q3_paired_surfaces.to_csv(
        q3_dir / "paired_response_surfaces.csv", index=False, encoding="utf-8-sig"
    )
    build_scoped_paired_surfaces(q3_replicates).to_csv(
        q3_dir / "scoped_paired_response_surfaces.csv", index=False, encoding="utf-8-sig"
    )


def verify_q1(project_root: Path) -> None:
    data = read_problem(problem_statement_path(project_root))
    live = solve_q1(data)
    frozen = json.loads((project_root / "results" / "task-1" / "summary.json").read_text(encoding="utf-8"))
    np.testing.assert_array_equal(live["vehicles"], frozen["vehicles"])
    np.testing.assert_allclose(live["loads"], frozen["loads"], rtol=0.0, atol=1e-9)
    for key in (
        "distance_total",
        "distance_mean",
        "service_3km_coverage",
        "strict_center_proxy_coverage",
        "potential_3km_coverage",
    ):
        np.testing.assert_allclose(live[key], frozen[key], rtol=1e-12, atol=1e-12)
    if int(np.sum(live["vehicles"])) != 12 or float(np.sum(live["loads"])) != 140.0:
        raise AssertionError("Task 1 fleet or demand conservation contract failed")


def verify_q2(project_root: Path) -> None:
    output = project_root / "results" / "task-2"
    replicates = pd.read_csv(output / "final_replicates_W030.csv")
    if len(replicates) != 90:
        raise AssertionError(f"Task 2 expected 90 final rows, received {len(replicates)}")
    if set(replicates["candidate"]) != set(Q2_CANDIDATES):
        raise AssertionError("Task 2 final candidate set has drifted")
    if set(replicates["seed"]) != set(range(400_000, 400_030)):
        raise AssertionError("Task 2 final seed block has drifted")
    if not (replicates.groupby("candidate").size() == 30).all():
        raise AssertionError("Task 2 candidates do not each contain 30 replications")
    if not (replicates["calls"] == 4_200).all():
        raise AssertionError("Task 2 does not contain exactly 140 calls for each measured day")
    if replicates["max_daily_dispatches_per_ambulance"].max() > DAILY_CAP:
        raise AssertionError("Task 2 violated the per-ambulance daily dispatch cap")

    expected_summary, expected_paired = q2_aggregates(replicates)
    _assert_close_frame(
        pd.read_csv(output / "final_summary.csv"),
        expected_summary,
        ["candidate", "metric"],
    )
    _assert_close_frame(
        pd.read_csv(output / "final_paired_response.csv"),
        expected_paired,
        ["comparison"],
    )
    decision = json.loads((output / "selected_policy.json").read_text(encoding="utf-8"))
    if decision["warmup_days"] != 30:
        raise AssertionError("Task 2 warmup must remain fixed at 30 days")
    if decision["main_policy"] != {
        "candidate": "B_beta4_delta2",
        "strategy": "B",
        "beta": 4.0,
        "delta": 2.0,
    }:
        raise AssertionError("Task 2 main policy has drifted")
    if decision["best_c"] != {
        "candidate": "C_r001000_tau7",
        "strategy": "C",
        "reserve_vector": [0, 0, 1, 0, 0, 0],
        "tau": 7.0,
    }:
        raise AssertionError("Task 2 explicit reserve configuration has drifted")


def verify_q3(project_root: Path) -> None:
    output = project_root / "results" / "task-3"
    stale = [name for name in LEGACY_Q3_EVIDENCE_FILENAMES if (output / name).exists()]
    if stale:
        raise AssertionError(f"Legacy cross-duration Task 3 evidence remains: {stale}")
    replicates = pd.read_csv(output / "replicates.csv")
    scenarios = pd.read_csv(output / "scenarios.csv")
    durations = sorted(replicates["duration_hours"].unique())
    if len(durations) != MAX_DURATION_NODES:
        raise AssertionError(
            f"Task 3 expected {MAX_DURATION_NODES} adaptive duration nodes, received {len(durations)}"
        )
    if not set(INITIAL_DURATIONS_HOURS).issubset(durations):
        raise AssertionError("Task 3 is missing one or more frozen initial duration nodes")
    expected_rows = MAX_DURATION_NODES * 10 * REPLICATIONS * 2
    if len(replicates) != expected_rows:
        raise AssertionError(
            f"Task 3 expected {expected_rows} duration-resolved rows, received {len(replicates)}"
        )
    if set(replicates["seed"]) != set(range(BASE_SEED, BASE_SEED + REPLICATIONS)):
        raise AssertionError("Task 3 seed block has drifted")
    if set(replicates["incident_zone"]) != set(range(1, 11)):
        raise AssertionError("Task 3 must evaluate all ten incident zones")
    if set(replicates["mode"]) != {"B_N", "B_E"}:
        raise AssertionError("Task 3 policy modes have drifted")
    pair_keys = ["incident_zone", "duration_hours", "seed"]
    if not (replicates.groupby(pair_keys)["mode"].nunique() == 2).all():
        raise AssertionError("Task 3 contains an incomplete B_N/B_E pair")
    if not (replicates.groupby(["incident_zone", "duration_hours", "mode"]).size() == REPLICATIONS).all():
        raise AssertionError("Task 3 duration-zone-mode cells do not contain all replications")
    if not (replicates.groupby(pair_keys)["call_digest"].nunique() == 1).all():
        raise AssertionError("Task 3 paired policies did not receive identical calls")
    if replicates["max_daily_dispatches_per_ambulance"].max() > DAILY_CAP:
        raise AssertionError("Task 3 violated the per-ambulance daily dispatch cap")
    boundary_columns = {
        "calls",
        "incident_zone_calls",
        "nonincident_zone_calls",
        "max_incident_queue",
        "incident_end_backlog",
    }
    if not boundary_columns.issubset(replicates.columns):
        raise AssertionError("Task 3 incident-window boundary fields are incomplete")
    if replicates[list(boundary_columns)].isna().any().any():
        raise AssertionError("Task 3 incident-window boundary fields contain missing values")

    scenario_keys = ["incident_zone", "duration_hours"]
    if len(scenarios) != MAX_DURATION_NODES * 10 or scenarios.duplicated(scenario_keys).any():
        raise AssertionError("Task 3 scenario design is incomplete or duplicated")
    if set(scenarios["duration_hours"]) != set(durations):
        raise AssertionError("Task 3 scenario and replicate duration nodes differ")
    if set(scenarios["incident_zone"]) != set(range(1, 11)):
        raise AssertionError("Task 3 scenario design does not cover all ten zones")

    expected_summary, expected_paired = emergency_summaries(replicates)
    expected_duration = build_duration_table(replicates)
    expected_citywide_duration = build_citywide_duration_table(replicates)
    expected_surfaces, expected_paired_surfaces = build_response_surfaces(replicates)
    expected_scoped_surfaces = build_scoped_paired_surfaces(replicates)
    _assert_close_frame(
        pd.read_csv(output / "summary.csv"),
        expected_summary,
        ["mode", "incident_zone", "duration_hours", "start_hour", "metric"],
    )
    _assert_close_frame(
        pd.read_csv(output / "paired_effects.csv"),
        expected_paired,
        ["incident_zone", "duration_hours", "start_hour", "metric"],
    )
    _assert_close_frame(
        pd.read_csv(output / "duration_table.csv"),
        expected_duration,
        ["incident_zone", "duration_hours", "metric"],
    )
    _assert_close_frame(
        pd.read_csv(output / "citywide_duration_table.csv"),
        expected_citywide_duration,
        ["duration_hours", "metric"],
    )
    if not (expected_citywide_duration["incident_zone_scenarios"] == 10).all():
        raise AssertionError("Task 3 citywide effects did not average all ten incident-zone scenarios")
    _assert_close_frame(
        pd.read_csv(output / "response_surfaces.csv"),
        expected_surfaces,
        ["incident_zone", "mode", "metric", "duration_hours"],
    )
    _assert_close_frame(
        pd.read_csv(output / "paired_response_surfaces.csv"),
        expected_paired_surfaces,
        ["incident_zone", "metric", "duration_hours"],
    )
    _assert_close_frame(
        pd.read_csv(output / "scoped_paired_response_surfaces.csv"),
        expected_scoped_surfaces,
        ["metric", "duration_hours"],
    )
    if not (expected_scoped_surfaces["incident_zone_scenarios"] == 10).all():
        raise AssertionError("Task 3 scoped effects did not pool all ten incident-zone scenarios")
    if set(expected_duration["duration_hours"]) != set(durations):
        raise AssertionError("Task 3 evidence table pooled or omitted duration nodes")
    if set(expected_duration["metric"]) != set(RESPONSE_SURFACE_METRICS):
        raise AssertionError("Task 3 duration-resolved metric set has drifted")


def verify_figures(project_root: Path, questions: tuple[str, ...] = ("q1", "q2", "q3")) -> None:
    figures = project_root / "figures"
    by_question = {
        "q1": {
            "raw_q1_demand",
            "process_q1_transport_network",
            "result_q1_coverage",
        },
        "q2": {
            "raw_q2_nhpp_intensity",
            "process_q2_b_grid",
            "result_q2_mean_response",
        },
        "q3": {
            "raw_q3_incident_load",
            "process_q3_duration_zone",
            "result_q3_paired_effect",
        },
    }
    expected = set().union(*(by_question[question] for question in questions))
    for stem in expected:
        for suffix in (".png", ".svg"):
            if not (figures / f"{stem}{suffix}").is_file():
                raise FileNotFoundError(f"Missing required figure: {stem}{suffix}")


def verify_all(project_root: Path) -> None:
    statement = problem_statement_path(project_root)
    if sha256(statement) != INPUT_SHA256:
        raise AssertionError("Problem statement SHA-256 does not match the frozen input")
    verify_q1(project_root)
    verify_q2(project_root)
    verify_q3(project_root)
    verify_figures(project_root)
    print("[verify] Task 1, Task 2, Task 3, and figure evidence: PASS")


def verify_stage(project_root: Path, scope: str) -> None:
    statement = problem_statement_path(project_root)
    if sha256(statement) != INPUT_SHA256:
        raise AssertionError("Problem statement SHA-256 does not match the frozen input")
    if scope == "q1-q2":
        verify_q1(project_root)
        verify_q2(project_root)
        verify_figures(project_root, questions=("q1", "q2"))
        print("[verify] Task 1, Task 2, and their figure evidence: PASS")
        return
    if scope == "all":
        verify_all(project_root)
        return
    raise ValueError(f"Unknown verification scope: {scope}")


def _run(project_root: Path, script: str, workers: int | None = None) -> None:
    command = [sys.executable, str(project_root / "src" / script), "--project-root", str(project_root)]
    if workers is not None:
        command.extend(["--workers", str(workers)])
    subprocess.run(command, cwd=project_root, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reproduce or verify all Problem A evidence")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--mode", choices=("verify", "rebuild", "full"), default="verify")
    parser.add_argument("--scope", choices=("all", "q1-q2"), default="all")
    parser.add_argument("--workers", type=int, default=min(12, max(1, (os.cpu_count() or 2) - 1)))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    if args.mode == "full":
        _run(project_root, "run_experiments.py", args.workers)
        _run(project_root, "run_emergency_experiments.py", args.workers)
    if args.mode in {"rebuild", "full"}:
        rebuild_stage(project_root, args.scope)
        if args.scope == "all":
            _run(project_root, "generate_figures.py")
    verify_stage(project_root, args.scope)


if __name__ == "__main__":
    main()
