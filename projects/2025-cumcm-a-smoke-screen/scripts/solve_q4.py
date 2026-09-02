from __future__ import annotations

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

MISSILE = np.array([20000.0, 0.0, 2000.0])
DRONES = {
    "FY1": np.array([17800.0, 0.0, 1800.0]),
    "FY2": np.array([12000.0, 1400.0, 1400.0]),
    "FY3": np.array([6000.0, -3000.0, 700.0]),
}
TARGET_CENTER = TARGET_BASE_CENTER + np.array([0.0, 0.0, 5.0])
ARRIVAL = np.linalg.norm(MISSILE) / 300.0
SEARCH_POINTS = cylinder_surface_points(24, 3, 2)
GRID_STEP = 0.1


def decode_guided(drone: np.ndarray, parameters: np.ndarray) -> np.ndarray | None:
    explosion_time, offset, fraction = parameters
    alignment_time = explosion_time + offset
    if explosion_time <= 0.0 or alignment_time >= ARRIVAL:
        return None
    missile = missile_position(MISSILE, alignment_time)
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


def sampled_metrics(drone: np.ndarray, strategy: np.ndarray) -> tuple[float, float]:
    heading, speed, explosion_time, fuse = strategy
    velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
    explosion = explosion_point(drone, velocity, explosion_time, fuse)
    end = min(explosion_time + CLOUD_LIFETIME, ARRIVAL, explosion_time + explosion[2] / 3.0)
    times = np.arange(explosion_time, end + 0.5 * GRID_STEP, GRID_STEP)
    observers = np.array([missile_position(MISSILE, time) for time in times])
    clouds = np.array([cloud_center(explosion, time - explosion_time) for time in times])
    radii = required_cloud_radii(observers, clouds, SEARCH_POINTS)
    return float(np.count_nonzero(radii <= CLOUD_RADIUS) * GRID_STEP), float(radii.min())


def optimize_drone(name: str, drone: np.ndarray) -> tuple[np.ndarray, list[float]]:
    rng = np.random.default_rng(4000 + int(name[-1]))
    seeds = []
    for _ in range(50000):
        parameters = np.array(
            [rng.uniform(0.3, 30.0), rng.uniform(0.0, CLOUD_LIFETIME), rng.uniform(0.70, 0.9999)]
        )
        strategy = decode_guided(drone, parameters)
        if strategy is None:
            continue
        duration, minimum_radius = sampled_metrics(drone, strategy)
        seeds.append((duration, -minimum_radius, parameters))
        if len(seeds) >= 250:
            break
    if not seeds:
        raise RuntimeError(f"No feasible geometric seed found for {name}")
    seed_point = max(seeds, key=lambda item: (item[0], item[1]))[2]
    runs = []
    for seed in (4101, 4102, 4103):
        def objective(parameters: np.ndarray) -> float:
            strategy = decode_guided(drone, parameters)
            if strategy is None:
                return 1e4
            duration, minimum_radius = sampled_metrics(drone, strategy)
            return -100.0 - duration if duration else minimum_radius - CLOUD_RADIUS

        result = differential_evolution(
            objective,
            [(0.3, 30.0), (0.0, CLOUD_LIFETIME), (0.70, 0.9999)],
            seed=seed + int(name[-1]) * 10,
            popsize=7,
            maxiter=55,
            tol=1e-5,
            polish=False,
            x0=seed_point,
        )
        strategy = decode_guided(drone, result.x)
        if strategy is not None:
            runs.append((sampled_metrics(drone, strategy)[0], strategy))
    if not runs:
        raise RuntimeError(f"No feasible strategy found for {name}")
    return max(runs, key=lambda item: item[0])[1], [run[0] for run in runs]


def main() -> None:
    validation_points = cylinder_surface_points(360, 21, 11)
    records = []
    all_intervals = []
    multistart = {}
    for name, drone in DRONES.items():
        strategy, run_durations = optimize_drone(name, drone)
        if name == "FY1":
            accepted_q2 = json.loads(
                (PROJECT_ROOT / "results" / "accepted" / "q2.json").read_text(encoding="utf-8")
            )
            strategy = np.array(
                [
                    math.radians(accepted_q2["heading_deg"]),
                    accepted_q2["speed_m_s"],
                    accepted_q2["explosion_time_s"],
                    accepted_q2["fuse_delay_s"],
                ]
            )
        intervals = strategy_shielding_intervals(drone, MISSILE, strategy, validation_points, 0.01)
        all_intervals.extend(intervals)
        multistart[name] = run_durations
        heading, speed, explosion_time, fuse = strategy
        release_time = explosion_time - fuse
        velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
        records.append(
            {
                "drone": name,
                "heading_deg": math.degrees(heading),
                "speed_m_s": speed,
                "release_time_s": release_time,
                "fuse_delay_s": fuse,
                "explosion_time_s": explosion_time,
                "release_point_m": (drone + velocity * release_time).tolist(),
                "explosion_point_m": explosion_point(drone, velocity, explosion_time, fuse).tolist(),
                "shielding_intervals_s": intervals,
                "individual_duration_s": interval_measure(intervals),
            }
        )
    union = merge_intervals(all_intervals)
    result = {
        "status": "working_individual_best_combination",
        "optimality_claim": "none; independent multistart strategies combined and evaluated by union",
        "model": "complete-cylinder line-of-sight shielding",
        "records": records,
        "union_intervals_s": union,
        "effective_shielding_duration_s": interval_measure(union),
        "validation": {
            "validation_surface_points": int(len(validation_points)),
            "multistart_sampled_durations_s": multistart,
        },
    }
    output = PROJECT_ROOT / "results" / "working" / "q4.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
