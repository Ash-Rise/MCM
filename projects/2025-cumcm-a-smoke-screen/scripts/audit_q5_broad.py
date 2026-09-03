from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_q5_joint import (  # noqa: E402
    coarse_score,
    high_resolution_result,
    optimize_drone,
    record_strategy,
)
from solve_q5 import DRONES, MISSILES, optimize_pair  # noqa: E402


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
        before = coarse_score(schedules)
        best = (before, schedules[drone_name], None)
        for missile_index, missile_name in enumerate(MISSILES, 1):
            single = optimize_pair(drone_name, missile_name)
            if single is None:
                continue
            heading, speed, explosion_time, fuse = single
            release = max(0.0, explosion_time - fuse)
            first = max(0.0, release - 1.1)
            x0 = np.array([0.0, speed, first, 0.1, 0.1, fuse, fuse, fuse])
            assignments = [missile_name, missile_name, missile_name]
            score, strategies = optimize_drone(
                drone_name,
                schedules,
                heading,
                x0,
                assignments,
                9000 + 100 * drone_index + missile_index,
                maxiter=18,
            )
            if score > best[0]:
                best = (score, list(zip(assignments, strategies, strict=True)), missile_name)
        if best[0] > before:
            schedules[drone_name] = best[1]
        trace.append(
            {
                "drone": drone_name,
                "before_s": before,
                "after_s": coarse_score(schedules),
                "accepted_alternative_target_basin": best[2],
            }
        )
    candidate = high_resolution_result(schedules)
    candidate["audit"] = {
        "type": "broad independent-pair trajectory basin audit",
        "incumbent_b1_s": incumbent["formal_b1"]["objective_sum_s"],
        "trace": trace,
    }
    output = PROJECT_ROOT / "results" / "audits" / "q5_broad.json"
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
