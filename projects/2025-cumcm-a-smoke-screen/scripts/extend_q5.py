from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from smoke_screen.model import (  # noqa: E402
    GRAVITY,
    cylinder_surface_points,
    explosion_point,
    interval_measure,
    merge_intervals,
    strategy_shielding_intervals,
)
from solve_q5 import DRONES, MISSILES, sampled_metrics  # noqa: E402


def optimize_candidate(
    drone_name: str,
    missile_name: str,
    heading: float,
    speed: float,
    base_release: float,
    seed: int,
) -> tuple[np.ndarray, float] | None:
    drone = DRONES[drone_name]
    missile = MISSILES[missile_name]
    arrival = np.linalg.norm(missile) / 300.0
    maximum_fuse = math.sqrt(2.0 * drone[2] / GRAVITY)

    def objective(parameters: np.ndarray) -> float:
        release, fuse = parameters
        explosion_time = release + fuse
        if abs(release - base_release) < 1.0 or explosion_time >= arrival:
            return 1e4
        strategy = np.array([heading, speed, explosion_time, fuse])
        duration, minimum_radius = sampled_metrics(drone, missile, strategy)
        return -100.0 - duration if duration else minimum_radius

    result = differential_evolution(
        objective,
        [(0.0, min(45.0, arrival - 0.1)), (0.0, maximum_fuse)],
        seed=seed,
        popsize=6,
        maxiter=40,
        tol=1e-5,
        polish=False,
    )
    release, fuse = result.x
    strategy = np.array([heading, speed, release + fuse, fuse])
    duration, _ = sampled_metrics(drone, missile, strategy)
    if duration <= 0.0 or abs(release - base_release) < 1.0:
        return None
    return strategy, duration


def main() -> None:
    base = json.loads((PROJECT_ROOT / "results" / "working" / "q5.json").read_text(encoding="utf-8"))
    if base.get("status") != "working_lower_bound_one_bomb_per_drone":
        raise RuntimeError("Run solve_q5.py immediately before extend_q5.py")
    validation_points = cylinder_surface_points(180, 11, 5)
    selected = []
    releases = {name: [] for name in DRONES}
    formal_intervals = {name: [] for name in MISSILES}
    trajectory = {}
    for record in base["records"]:
        drone_name = record["drone"]
        missile_name = record["assigned_missile"]
        heading = math.radians(record["heading_deg"])
        speed = record["speed_m_s"]
        strategy = np.array([heading, speed, record["explosion_time_s"], record["fuse_delay_s"]])
        trajectory[drone_name] = (heading, speed)
        releases[drone_name].append(record["release_time_s"])
        intervals = [tuple(interval) for interval in record["assigned_target_intervals_s"]]
        formal_intervals[missile_name].extend(intervals)
        selected.append((drone_name, missile_name, strategy, intervals, "base"))

    pool = []
    for drone_index, (drone_name, (heading, speed)) in enumerate(trajectory.items(), 1):
        base_release = releases[drone_name][0]
        for missile_index, missile_name in enumerate(MISSILES, 1):
            for run in range(3):
                candidate = optimize_candidate(
                    drone_name,
                    missile_name,
                    heading,
                    speed,
                    base_release,
                    6000 + 100 * drone_index + 10 * missile_index + run,
                )
                if candidate is None:
                    continue
                strategy, sampled_duration = candidate
                intervals = strategy_shielding_intervals(
                    DRONES[drone_name], MISSILES[missile_name], strategy, validation_points, 0.01
                )
                if intervals:
                    pool.append((drone_name, missile_name, strategy, intervals, sampled_duration))

    while True:
        current_score = sum(
            interval_measure(merge_intervals(intervals)) for intervals in formal_intervals.values()
        )
        best = None
        for candidate in pool:
            drone_name, missile_name, strategy, intervals, _ = candidate
            release = strategy[2] - strategy[3]
            if len(releases[drone_name]) >= 3 or any(abs(release - prior) < 1.0 for prior in releases[drone_name]):
                continue
            trial = {name: list(values) for name, values in formal_intervals.items()}
            trial[missile_name].extend(intervals)
            score = sum(interval_measure(merge_intervals(values)) for values in trial.values())
            gain = score - current_score
            if best is None or gain > best[0]:
                best = (gain, candidate)
        if best is None or best[0] <= 1e-6:
            break
        _, candidate = best
        pool = [item for item in pool if item is not candidate]
        drone_name, missile_name, strategy, intervals, _ = candidate
        releases[drone_name].append(float(strategy[2] - strategy[3]))
        formal_intervals[missile_name].extend(intervals)
        selected.append((drone_name, missile_name, strategy, intervals, "extension"))

    records = []
    physical_intervals = {name: [] for name in MISSILES}
    for drone_name in DRONES:
        drone_records = sorted(
            [item for item in selected if item[0] == drone_name], key=lambda item: item[2][2] - item[2][3]
        )
        for bomb_number, (_, missile_name, strategy, intervals, source) in enumerate(drone_records, 1):
            heading, speed, explosion_time, fuse = strategy
            release = explosion_time - fuse
            velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
            drone = DRONES[drone_name]
            for physical_missile_name, missile in MISSILES.items():
                physical_intervals[physical_missile_name].extend(
                    strategy_shielding_intervals(drone, missile, strategy, validation_points, 0.01)
                )
            records.append(
                {
                    "drone": drone_name,
                    "bomb": bomb_number,
                    "assigned_missile": missile_name,
                    "source": source,
                    "heading_deg": math.degrees(heading),
                    "speed_m_s": speed,
                    "release_time_s": release,
                    "fuse_delay_s": fuse,
                    "explosion_time_s": explosion_time,
                    "release_point_m": (drone + velocity * release).tolist(),
                    "explosion_point_m": explosion_point(drone, velocity, explosion_time, fuse).tolist(),
                    "assigned_target_intervals_s": intervals,
                }
            )
    formal_unions = {name: merge_intervals(values) for name, values in formal_intervals.items()}
    formal_score = sum(interval_measure(values) for values in formal_unions.values())
    physical_unions = {name: merge_intervals(values) for name, values in physical_intervals.items()}
    physical_score = sum(interval_measure(values) for values in physical_unions.values())
    result = {
        "status": "working_fixed_trajectory_extension",
        "formal_semantics": "DP-03/B1 assigned-target accounting",
        "optimality_claim": "none; greedy B1 extension of the enumerated one-bomb-per-drone lower bound",
        "records": records,
        "formal_b1": {
            "per_missile_union_intervals_s": formal_unions,
            "per_missile_durations_s": {name: interval_measure(values) for name, values in formal_unions.items()},
            "objective_sum_s": formal_score,
        },
        "supplemental_b2": {
            "role": "post-selection physical evaluation only; not used in ranking",
            "per_missile_union_intervals_s": physical_unions,
            "per_missile_durations_s": {name: interval_measure(values) for name, values in physical_unions.items()},
            "physical_sum_s": physical_score,
            "incidental_gain_over_b1_s": physical_score - formal_score,
        },
        "validation": {
            "surface_points": int(len(validation_points)),
            "selected_bombs": len(records),
            "release_gaps_s": {
                name: [right - left for left, right in zip(sorted(times)[:-1], sorted(times)[1:])]
                for name, times in releases.items()
            },
            "remaining_positive_candidate_pool": len(pool),
        },
    }
    output = PROJECT_ROOT / "results" / "working" / "q5.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
