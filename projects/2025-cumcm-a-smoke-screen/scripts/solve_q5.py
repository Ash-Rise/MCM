from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from smoke_screen.model import (  # noqa: E402
    CLOUD_LIFETIME,
    CLOUD_RADIUS,
    GRAVITY,
    TARGET_BASE_CENTER,
    cloud_center,
    cylinder_surface_points,
    explosion_point,
    interval_measure,
    merge_intervals,
    missile_position,
    required_cloud_radii,
    strategy_shielding_intervals,
)

MISSILES = {
    "M1": np.array([20000.0, 0.0, 2000.0]),
    "M2": np.array([19000.0, 600.0, 2100.0]),
    "M3": np.array([18000.0, -600.0, 1900.0]),
}
DRONES = {
    "FY1": np.array([17800.0, 0.0, 1800.0]),
    "FY2": np.array([12000.0, 1400.0, 1400.0]),
    "FY3": np.array([6000.0, -3000.0, 700.0]),
    "FY4": np.array([11000.0, 2000.0, 1800.0]),
    "FY5": np.array([13000.0, -2000.0, 1300.0]),
}
TARGET_CENTER = TARGET_BASE_CENTER + np.array([0.0, 0.0, 5.0])
SEARCH_POINTS = cylinder_surface_points(24, 3, 2)
GRID_STEP = 0.1


def decode_guided(drone: np.ndarray, missile_initial: np.ndarray, parameters: np.ndarray) -> np.ndarray | None:
    explosion_time, offset, fraction = parameters
    arrival = np.linalg.norm(missile_initial) / 300.0
    alignment_time = explosion_time + offset
    if explosion_time <= 0.0 or alignment_time >= arrival:
        return None
    missile = missile_position(missile_initial, alignment_time)
    aligned_cloud = TARGET_CENTER + fraction * (missile - TARGET_CENTER)
    explosion = aligned_cloud + np.array([0.0, 0.0, 3.0 * offset])
    displacement = explosion[:2] - drone[:2]
    speed = np.linalg.norm(displacement) / explosion_time
    if not 70.0 <= speed <= 140.0 or not 0.0 <= explosion[2] <= drone[2]:
        return None
    fuse = math.sqrt(2.0 * (drone[2] - explosion[2]) / GRAVITY)
    if fuse > explosion_time:
        return None
    heading = math.atan2(displacement[1], displacement[0]) % (2.0 * math.pi)
    return np.array([heading, speed, explosion_time, fuse])


def sampled_metrics(
    drone: np.ndarray, missile_initial: np.ndarray, strategy: np.ndarray
) -> tuple[float, float]:
    heading, speed, explosion_time, fuse = strategy
    velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
    explosion = explosion_point(drone, velocity, explosion_time, fuse)
    arrival = np.linalg.norm(missile_initial) / 300.0
    end = min(explosion_time + CLOUD_LIFETIME, arrival, explosion_time + explosion[2] / 3.0)
    times = np.arange(explosion_time, end + 0.5 * GRID_STEP, GRID_STEP)
    observers = np.array([missile_position(missile_initial, time) for time in times])
    clouds = np.array([cloud_center(explosion, time - explosion_time) for time in times])
    radii = required_cloud_radii(observers, clouds, SEARCH_POINTS)
    return float(np.count_nonzero(radii <= CLOUD_RADIUS) * GRID_STEP), float(radii.min())


def optimize_pair(drone_name: str, missile_name: str) -> np.ndarray | None:
    drone = DRONES[drone_name]
    missile = MISSILES[missile_name]
    pair_seed = 5000 + 100 * int(drone_name[-1]) + int(missile_name[-1])
    rng = np.random.default_rng(pair_seed)
    geometric_seeds = []
    for _ in range(40000):
        parameters = np.array(
            [rng.uniform(0.3, 32.0), rng.uniform(0.0, CLOUD_LIFETIME), rng.uniform(0.70, 0.9999)]
        )
        strategy = decode_guided(drone, missile, parameters)
        if strategy is None:
            continue
        duration, minimum_radius = sampled_metrics(drone, missile, strategy)
        geometric_seeds.append((duration, -minimum_radius, parameters))
        if len(geometric_seeds) >= 160:
            break
    if not geometric_seeds:
        return None
    x0 = max(geometric_seeds, key=lambda item: (item[0], item[1]))[2]

    def objective(parameters: np.ndarray) -> float:
        strategy = decode_guided(drone, missile, parameters)
        if strategy is None:
            return 1e4
        duration, minimum_radius = sampled_metrics(drone, missile, strategy)
        return -100.0 - duration if duration else minimum_radius - CLOUD_RADIUS

    result = differential_evolution(
        objective,
        [(0.3, 32.0), (0.0, CLOUD_LIFETIME), (0.70, 0.9999)],
        seed=pair_seed,
        popsize=6,
        maxiter=45,
        tol=1e-5,
        polish=False,
        x0=x0,
    )
    strategy = decode_guided(drone, missile, result.x)
    if strategy is None:
        raise RuntimeError(f"Optimization failed for {drone_name}-{missile_name}")
    return strategy


def main() -> None:
    validation_points = cylinder_surface_points(180, 11, 5)
    pair_data = {}
    for drone_name, missile_name in itertools.product(DRONES, MISSILES):
        strategy = optimize_pair(drone_name, missile_name)
        if strategy is None:
            continue
        intervals = strategy_shielding_intervals(
            DRONES[drone_name], MISSILES[missile_name], strategy, validation_points, 0.01
        )
        pair_data[(drone_name, missile_name)] = (strategy, intervals)

    best = None
    for assigned_missiles in itertools.product(MISSILES, repeat=len(DRONES)):
        assignment = dict(zip(DRONES, assigned_missiles, strict=True))
        if any((drone_name, missile_name) not in pair_data for drone_name, missile_name in assignment.items()):
            continue
        formal_unions = {}
        for missile_name in MISSILES:
            intervals = [
                interval
                for drone_name, assigned in assignment.items()
                if assigned == missile_name
                for interval in pair_data[(drone_name, assigned)][1]
            ]
            formal_unions[missile_name] = merge_intervals(intervals)
        score = sum(interval_measure(intervals) for intervals in formal_unions.values())
        if best is None or score > best[0]:
            best = (score, assignment, formal_unions)
    if best is None:
        raise RuntimeError("No Q5 assignment evaluated")
    formal_score, assignment, formal_unions = best

    records = []
    physical_intervals = {missile_name: [] for missile_name in MISSILES}
    for drone_name, assigned in assignment.items():
        strategy, assigned_intervals = pair_data[(drone_name, assigned)]
        drone = DRONES[drone_name]
        heading, speed, explosion_time, fuse = strategy
        release_time = explosion_time - fuse
        velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
        for missile_name, missile in MISSILES.items():
            physical_intervals[missile_name].extend(
                strategy_shielding_intervals(drone, missile, strategy, validation_points, 0.01)
            )
        records.append(
            {
                "drone": drone_name,
                "assigned_missile": assigned,
                "heading_deg": math.degrees(heading),
                "speed_m_s": speed,
                "release_time_s": release_time,
                "fuse_delay_s": fuse,
                "explosion_time_s": explosion_time,
                "release_point_m": (drone + velocity * release_time).tolist(),
                "explosion_point_m": explosion_point(drone, velocity, explosion_time, fuse).tolist(),
                "assigned_target_intervals_s": assigned_intervals,
            }
        )
    physical_unions = {
        missile_name: merge_intervals(intervals) for missile_name, intervals in physical_intervals.items()
    }
    physical_score = sum(interval_measure(intervals) for intervals in physical_unions.values())
    result = {
        "status": "working_lower_bound_one_bomb_per_drone",
        "formal_semantics": "DP-03/B1 assigned-target accounting",
        "optimality_claim": "none; exact enumeration of assignments over independently optimized one-bomb pair candidates",
        "records": records,
        "formal_b1": {
            "per_missile_union_intervals_s": formal_unions,
            "per_missile_durations_s": {
                name: interval_measure(intervals) for name, intervals in formal_unions.items()
            },
            "objective_sum_s": formal_score,
        },
        "supplemental_b2": {
            "role": "post-selection physical evaluation only; not used in ranking",
            "per_missile_union_intervals_s": physical_unions,
            "per_missile_durations_s": {
                name: interval_measure(intervals) for name, intervals in physical_unions.items()
            },
            "physical_sum_s": physical_score,
            "incidental_gain_over_b1_s": physical_score - formal_score,
        },
        "validation": {
            "surface_points": int(len(validation_points)),
            "assignment_combinations": 3 ** len(DRONES),
            "candidate_scope": "one bomb per drone; remaining allowed bombs not yet optimized",
            "available_pair_candidates": [f"{drone}-{missile}" for drone, missile in pair_data],
        },
    }
    output = PROJECT_ROOT / "results" / "working" / "q5.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
