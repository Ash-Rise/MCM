from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_q5_joint import (  # noqa: E402
    coarse_score,
    high_resolution_result,
    initial_parameters,
    optimize_drone,
    record_strategy,
)
from solve_q5 import DRONES, MISSILES  # noqa: E402


def one_change_patterns(assignments: list[str]) -> list[list[str]]:
    patterns = []
    for index, current in enumerate(assignments):
        for missile_name in MISSILES:
            if missile_name == current:
                continue
            candidate = list(assignments)
            candidate[index] = missile_name
            patterns.append(candidate)
    return patterns


def main() -> None:
    incumbent = json.loads(
        (PROJECT_ROOT / "results" / "working" / "q5.json").read_text(encoding="utf-8")
    )
    grouped = {name: [] for name in DRONES}
    for record in incumbent["records"]:
        grouped[record["drone"]].append(record)
    schedules = {
        name: [(record["assigned_missile"], record_strategy(record)) for record in records]
        for name, records in grouped.items()
    }
    trace = []
    for drone_index, drone_name in enumerate(DRONES, 1):
        base_heading, x0, assignments = initial_parameters(grouped[drone_name])
        before = coarse_score(schedules)
        best = (before, schedules[drone_name], None)
        for pattern_index, pattern in enumerate(one_change_patterns(assignments)):
            score, strategies = optimize_drone(
                drone_name,
                schedules,
                base_heading,
                x0,
                pattern,
                10000 + 100 * drone_index + pattern_index,
                maxiter=10,
                population_size=32,
            )
            if score > best[0]:
                best = (score, list(zip(pattern, strategies, strict=True)), pattern)
        if best[0] > before:
            schedules[drone_name] = best[1]
        trace.append(
            {
                "drone": drone_name,
                "before_s": before,
                "after_s": coarse_score(schedules),
                "accepted_one_change_pattern": best[2],
            }
        )
    candidate = high_resolution_result(schedules)
    candidate["audit"] = {
        "type": "one-assignment-change neighborhood with joint continuous reoptimization",
        "incumbent_b1_s": incumbent["formal_b1"]["objective_sum_s"],
        "trace": trace,
    }
    output = PROJECT_ROOT / "results" / "audits" / "q5_assignments.json"
    output.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if candidate["formal_b1"]["objective_sum_s"] > incumbent["formal_b1"]["objective_sum_s"] + 1e-6:
        (PROJECT_ROOT / "results" / "working" / "q5.json").write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "incumbent_b1_s": incumbent["formal_b1"]["objective_sum_s"],
                "candidate_b1_s": candidate["formal_b1"]["objective_sum_s"],
                "trace": trace,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
