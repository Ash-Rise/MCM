from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from solve_q4 import DRONES, sampled_metrics  # noqa: E402


def main() -> None:
    working = json.loads(
        (PROJECT_ROOT / "results" / "working" / "q4.json").read_text(encoding="utf-8")
    )
    rng = np.random.default_rng(20250903)
    audits = []
    for record in working["records"]:
        drone_name = record["drone"]
        strategy = np.array(
            [
                math.radians(record["heading_deg"]),
                record["speed_m_s"],
                record["explosion_time_s"],
                record["fuse_delay_s"],
            ]
        )
        base_duration, _ = sampled_metrics(DRONES[drone_name], strategy)
        best_duration = base_duration
        feasible = 0
        for _ in range(600):
            candidate = strategy + rng.normal(size=4) * np.array([0.012, 3.0, 0.25, 0.20])
            candidate[0] %= 2.0 * math.pi
            candidate[1] = np.clip(candidate[1], 70.0, 140.0)
            if candidate[3] < 0.0 or candidate[3] > candidate[2]:
                continue
            duration, _ = sampled_metrics(DRONES[drone_name], candidate)
            if duration > 0.0:
                feasible += 1
            best_duration = max(best_duration, duration)
        audits.append(
            {
                "drone": drone_name,
                "baseline_sampled_duration_s": base_duration,
                "trials": 600,
                "feasible_trials": feasible,
                "best_sampled_improvement_s": best_duration - base_duration,
                "solver_multistart_sampled_durations_s": working["validation"][
                    "multistart_sampled_durations_s"
                ][drone_name],
            }
        )
    intervals = [record["shielding_intervals_s"][0] for record in working["records"]]
    gaps = [intervals[index + 1][0] - intervals[index][1] for index in range(2)]
    result = {
        "status": "audit",
        "purpose": "Q4 independent-component stability and non-overlap check",
        "working_union_duration_s": working["effective_shielding_duration_s"],
        "component_audits": audits,
        "inter_component_gaps_s": gaps,
        "decomposition_valid": all(gap > 0.0 for gap in gaps),
        "conclusion": (
            "no_local_challenger" if all(item["best_sampled_improvement_s"] <= 1e-12 for item in audits)
            else "local_challenger_requires_refinement"
        ),
    }
    output = PROJECT_ROOT / "results" / "audits" / "q4_stability.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
