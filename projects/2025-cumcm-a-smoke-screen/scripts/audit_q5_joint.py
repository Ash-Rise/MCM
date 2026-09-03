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
    CLOUD_LIFETIME,
    CLOUD_RADIUS,
    GRAVITY,
    cloud_center,
    cylinder_surface_points,
    explosion_point,
    interval_measure,
    merge_intervals,
    missile_position,
    required_cloud_radii,
    strategy_shielding_intervals,
)
from solve_q5 import DRONES, MISSILES  # noqa: E402

DT = 0.1
SEARCH_POINTS = cylinder_surface_points(24, 3, 2)


def strategy_mask(drone_name: str, missile_name: str, strategy: np.ndarray) -> tuple[set[int], float]:
    drone = DRONES[drone_name]
    missile = MISSILES[missile_name]
    heading, speed, explosion_time, fuse = strategy
    arrival = np.linalg.norm(missile) / 300.0
    maximum_fuse = math.sqrt(2.0 * drone[2] / GRAVITY)
    if not (70.0 <= speed <= 140.0 and 0.0 <= fuse <= min(explosion_time, maximum_fuse)):
        return set(), 1e4
    velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
    explosion = explosion_point(drone, velocity, explosion_time, fuse)
    if explosion_time >= arrival or explosion[2] < 0.0:
        return set(), 1e4
    end = min(explosion_time + CLOUD_LIFETIME, arrival, explosion_time + explosion[2] / 3.0)
    times = np.arange(explosion_time, end + 0.5 * DT, DT)
    observers = np.array([missile_position(missile, time) for time in times])
    clouds = np.array([cloud_center(explosion, time - explosion_time) for time in times])
    radii = required_cloud_radii(observers, clouds, SEARCH_POINTS)
    indices = np.rint(times[radii <= CLOUD_RADIUS] / DT).astype(int)
    return set(indices.tolist()), float(radii.min())


def decode(base_heading: float, parameters: np.ndarray) -> list[np.ndarray]:
    delta, speed, first, slack12, slack23, fuse1, fuse2, fuse3 = parameters
    heading = (base_heading + delta) % (2.0 * math.pi)
    releases = [first, first + 1.0 + slack12, first + 2.0 + slack12 + slack23]
    return [
        np.array([heading, speed, release + fuse, fuse])
        for release, fuse in zip(releases, (fuse1, fuse2, fuse3), strict=True)
    ]


def record_strategy(record: dict) -> np.ndarray:
    return np.array(
        [
            math.radians(record["heading_deg"]),
            record["speed_m_s"],
            record["explosion_time_s"],
            record["fuse_delay_s"],
        ]
    )


def coarse_score(schedules: dict[str, list[tuple[str, np.ndarray]]]) -> float:
    unions = {name: set() for name in MISSILES}
    for drone_name, bombs in schedules.items():
        for missile_name, strategy in bombs:
            mask, _ = strategy_mask(drone_name, missile_name, strategy)
            unions[missile_name].update(mask)
    return DT * sum(len(mask) for mask in unions.values())


def initial_parameters(records: list[dict]) -> tuple[float, np.ndarray, list[str]]:
    records = sorted(records, key=lambda item: item["release_time_s"])
    heading = math.radians(records[0]["heading_deg"])
    speed = records[0]["speed_m_s"]
    assignments = [record["assigned_missile"] for record in records]
    while len(records) < 3:
        last = records[-1]
        clone = dict(last)
        clone["release_time_s"] = last["release_time_s"] + 1.5
        clone["explosion_time_s"] = clone["release_time_s"] + clone["fuse_delay_s"]
        records.append(clone)
        assignments.append(assignments[-1])
    releases = [record["release_time_s"] for record in records]
    fuses = [record["fuse_delay_s"] for record in records]
    parameters = np.array(
        [0.0, speed, releases[0], releases[1] - releases[0] - 1.0,
         releases[2] - releases[1] - 1.0, *fuses]
    )
    return heading, parameters, assignments


def optimize_drone(
    drone_name: str,
    schedules: dict[str, list[tuple[str, np.ndarray]]],
    base_heading: float,
    x0: np.ndarray,
    assignments: list[str],
    seed: int,
    maxiter: int = 28,
    population_size: int = 56,
) -> tuple[float, list[np.ndarray]]:
    maximum_fuse = math.sqrt(2.0 * DRONES[drone_name][2] / GRAVITY)
    bounds = [
        (-0.6, 0.6), (70.0, 140.0), (0.0, 40.0), (0.0, 16.0), (0.0, 16.0),
        (0.0, maximum_fuse), (0.0, maximum_fuse), (0.0, maximum_fuse),
    ]
    lower = np.array([item[0] for item in bounds])
    upper = np.array([item[1] for item in bounds])
    x0 = np.clip(x0, lower, upper)
    rng = np.random.default_rng(seed)
    scales = np.array([0.12, 8.0, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    population = np.clip(x0 + rng.normal(size=(population_size, 8)) * scales, lower, upper)
    population[0] = x0
    base_other = {name: bombs for name, bombs in schedules.items() if name != drone_name}
    base_unions = {name: set() for name in MISSILES}
    for other_drone, bombs in base_other.items():
        for missile_name, strategy in bombs:
            mask, _ = strategy_mask(other_drone, missile_name, strategy)
            base_unions[missile_name].update(mask)

    def candidate_score(strategies: list[np.ndarray]) -> float:
        unions = {name: set(mask) for name, mask in base_unions.items()}
        for missile_name, strategy in zip(assignments, strategies, strict=True):
            mask, _ = strategy_mask(drone_name, missile_name, strategy)
            unions[missile_name].update(mask)
        return DT * sum(len(mask) for mask in unions.values())

    def objective(parameters: np.ndarray) -> float:
        strategies = decode(base_heading, parameters)
        hard_score = candidate_score(strategies)
        if hard_score > 0.0:
            return -hard_score
        radius_sum = sum(
            strategy_mask(drone_name, missile_name, strategy)[1]
            for missile_name, strategy in zip(assignments, strategies, strict=True)
        )
        return radius_sum

    result = differential_evolution(
        objective,
        bounds,
        seed=seed,
        init=population,
        maxiter=maxiter,
        tol=1e-5,
        polish=False,
        updating="immediate",
    )
    strategies = decode(base_heading, result.x)
    return candidate_score(strategies), strategies


def high_resolution_result(schedules: dict[str, list[tuple[str, np.ndarray]]]) -> dict:
    points = cylinder_surface_points(180, 11, 5)
    formal = {name: [] for name in MISSILES}
    physical = {name: [] for name in MISSILES}
    records = []
    for drone_name, bombs in schedules.items():
        ordered = sorted(bombs, key=lambda item: item[1][2] - item[1][3])
        drone = DRONES[drone_name]
        for number, (assigned, strategy) in enumerate(ordered, 1):
            heading, speed, explosion_time, fuse = strategy
            release = explosion_time - fuse
            velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
            assigned_intervals = strategy_shielding_intervals(
                drone, MISSILES[assigned], strategy, points, 0.01
            )
            formal[assigned].extend(assigned_intervals)
            for missile_name, missile in MISSILES.items():
                physical[missile_name].extend(
                    strategy_shielding_intervals(drone, missile, strategy, points, 0.01)
                )
            records.append(
                {
                    "drone": drone_name,
                    "bomb": number,
                    "assigned_missile": assigned,
                    "heading_deg": math.degrees(heading),
                    "speed_m_s": speed,
                    "release_time_s": release,
                    "fuse_delay_s": fuse,
                    "explosion_time_s": explosion_time,
                    "release_point_m": (drone + velocity * release).tolist(),
                    "explosion_point_m": explosion_point(drone, velocity, explosion_time, fuse).tolist(),
                    "assigned_target_intervals_s": assigned_intervals,
                }
            )
    formal_unions = {name: merge_intervals(values) for name, values in formal.items()}
    physical_unions = {name: merge_intervals(values) for name, values in physical.items()}
    formal_score = sum(interval_measure(values) for values in formal_unions.values())
    physical_score = sum(interval_measure(values) for values in physical_unions.values())
    return {
        "status": "working_joint_coordinate_candidate",
        "formal_semantics": "DP-03/B1 assigned-target accounting",
        "optimality_claim": "none; coordinate-wise joint trajectory and three-bomb refinement",
        "records": records,
        "formal_b1": {
            "per_missile_union_intervals_s": formal_unions,
            "per_missile_durations_s": {
                name: interval_measure(values) for name, values in formal_unions.items()
            },
            "objective_sum_s": formal_score,
        },
        "supplemental_b2": {
            "role": "post-selection physical evaluation only; not used in ranking",
            "per_missile_union_intervals_s": physical_unions,
            "per_missile_durations_s": {
                name: interval_measure(values) for name, values in physical_unions.items()
            },
            "physical_sum_s": physical_score,
            "incidental_gain_over_b1_s": physical_score - formal_score,
        },
        "validation": {"surface_points": int(len(points)), "selected_bombs": len(records)},
    }


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
    initial_coarse = coarse_score(schedules)
    trace = []
    for index, drone_name in enumerate(DRONES, 1):
        base_heading, x0, assignments = initial_parameters(grouped[drone_name])
        patterns = [assignments]
        if len(grouped[drone_name]) < 3:
            patterns = [assignments[:2] + [missile_name] for missile_name in MISSILES]
        before = coarse_score(schedules)
        best = (before, schedules[drone_name], assignments)
        for pattern_index, pattern in enumerate(patterns):
            score, strategies = optimize_drone(
                drone_name, schedules, base_heading, x0, pattern,
                7000 + 100 * index + pattern_index,
            )
            if score > best[0]:
                best = (score, list(zip(pattern, strategies, strict=True)), pattern)
        if best[0] > before:
            schedules[drone_name] = best[1]
        trace.append(
            {"drone": drone_name, "before_s": before, "after_s": coarse_score(schedules),
             "assignments": best[2]}
        )
    candidate = high_resolution_result(schedules)
    candidate["audit"] = {
        "incumbent_b1_s": incumbent["formal_b1"]["objective_sum_s"],
        "initial_coarse_s": initial_coarse,
        "coordinate_trace": trace,
    }
    audit_path = PROJECT_ROOT / "results" / "audits" / "q5_joint.json"
    audit_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if candidate["formal_b1"]["objective_sum_s"] > incumbent["formal_b1"]["objective_sum_s"] + 1e-6:
        (PROJECT_ROOT / "results" / "working" / "q5.json").write_text(
            json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps({"incumbent_b1_s": incumbent["formal_b1"]["objective_sum_s"],
                      "candidate_b1_s": candidate["formal_b1"]["objective_sum_s"],
                      "trace": trace}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
