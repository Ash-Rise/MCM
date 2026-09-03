from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from smoke_screen.model import (  # noqa: E402
    cylinder_surface_points,
    interval_measure,
    merge_intervals,
    strategy_shielding_intervals,
)
from solve_q5 import DRONES, MISSILES  # noqa: E402


def strategy(record: dict) -> np.ndarray:
    return np.array(
        [
            math.radians(record["heading_deg"]),
            record["speed_m_s"],
            record["explosion_time_s"],
            record["fuse_delay_s"],
        ]
    )


def main() -> None:
    source_path = PROJECT_ROOT / "results" / "working" / "q5.json"
    accepted_path = PROJECT_ROOT / "results" / "accepted" / "q5.json"
    frozen_path = PROJECT_ROOT / "results" / "frozen" / "q5.json"
    data = json.loads(source_path.read_text(encoding="utf-8"))
    previous_objective = data["formal_b1"]["objective_sum_s"]
    points = cylinder_surface_points(180, 11, 5)

    retained = []
    removed = []
    for record in data["records"]:
        if record["assigned_target_intervals_s"]:
            retained.append(record)
            continue
        physical = {
            missile_name: strategy_shielding_intervals(
                DRONES[record["drone"]], missile, strategy(record), points, 0.01
            )
            for missile_name, missile in MISSILES.items()
        }
        if any(physical.values()):
            retained.append(record)
        else:
            removed.append(
                {
                    "drone": record["drone"],
                    "bomb": record["bomb"],
                    "assigned_missile": record["assigned_missile"],
                    "reason": "zero B1 contribution and zero physical shielding for all three missiles",
                }
            )

    formal = {name: [] for name in MISSILES}
    physical = {name: [] for name in MISSILES}
    for record in retained:
        current_strategy = strategy(record)
        assigned = record["assigned_missile"]
        assigned_intervals = strategy_shielding_intervals(
            DRONES[record["drone"]], MISSILES[assigned], current_strategy, points, 0.01
        )
        record["assigned_target_intervals_s"] = assigned_intervals
        formal[assigned].extend(assigned_intervals)
        for missile_name, missile in MISSILES.items():
            physical[missile_name].extend(
                strategy_shielding_intervals(
                    DRONES[record["drone"]], missile, current_strategy, points, 0.01
                )
            )

    formal_unions = {name: merge_intervals(values) for name, values in formal.items()}
    physical_unions = {name: merge_intervals(values) for name, values in physical.items()}
    formal_score = sum(interval_measure(values) for values in formal_unions.values())
    physical_score = sum(interval_measure(values) for values in physical_unions.values())
    if abs(formal_score - previous_objective) > 1e-9:
        raise RuntimeError(
            f"Q5 cleanup changed B1 objective: {previous_objective} -> {formal_score}"
        )

    data["records"] = retained
    data["formal_b1"] = {
        "per_missile_union_intervals_s": formal_unions,
        "per_missile_durations_s": {
            name: interval_measure(values) for name, values in formal_unions.items()
        },
        "objective_sum_s": formal_score,
    }
    data["supplemental_b2"] = {
        "role": "post-selection physical evaluation only; not used in ranking",
        "per_missile_union_intervals_s": physical_unions,
        "per_missile_durations_s": {
            name: interval_measure(values) for name, values in physical_unions.items()
        },
        "physical_sum_s": physical_score,
        "incidental_gain_over_b1_s": physical_score - formal_score,
    }
    data["validation"]["selected_bombs"] = len(retained)
    data["cleanup"] = {
        "removed_actions": removed,
        "criterion": "remove only actions with zero B1 and zero B2 contribution",
        "b1_before_s": previous_objective,
        "b1_after_s": formal_score,
    }
    data["status"] = "accepted_best_found"
    data["acceptance_evidence"] = [
        "results/audits/q5_joint.json",
        "results/audits/q5_broad.json",
        "results/audits/q5_assignments.json",
    ]
    accepted_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    frozen = dict(data)
    frozen["status"] = "frozen"
    frozen["frozen_from"] = "results/accepted/q5.json"
    frozen_path.write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data["cleanup"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
