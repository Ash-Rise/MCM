from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, differential_evolution, minimize


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from smoke_screen.model import (  # noqa: E402
    CLOUD_LIFETIME,
    CLOUD_RADIUS,
    GRAVITY,
    TARGET_BASE_CENTER,
    cloud_center,
    cylinder_surface_points,
    interval_measure,
    missile_position,
    required_cloud_radius,
    shielding_intervals,
)


MISSILE_INITIAL = np.array([20000.0, 0.0, 2000.0])
DRONE_INITIAL = np.array([17800.0, 0.0, 1800.0])
TARGET_CENTER = TARGET_BASE_CENTER + np.array([0.0, 0.0, 5.0])
MISSILE_ARRIVAL = np.linalg.norm(MISSILE_INITIAL) / 300.0
MAX_FUSE_DELAY = math.sqrt(2.0 * DRONE_INITIAL[2] / GRAVITY)


def decode_sightline_parameters(parameters: np.ndarray) -> np.ndarray | None:
    """Map a geometry-guided search point to heading, speed, explosion, and fuse."""
    explosion_time, sightline_offset, sightline_fraction = parameters
    alignment_time = explosion_time + sightline_offset
    if explosion_time <= 0.0 or not 0.0 <= sightline_offset <= CLOUD_LIFETIME:
        return None
    if alignment_time >= MISSILE_ARRIVAL:
        return None

    missile = missile_position(MISSILE_INITIAL, alignment_time)
    aligned_center = TARGET_CENTER + sightline_fraction * (missile - TARGET_CENTER)
    explosion = aligned_center + np.array([0.0, 0.0, 3.0 * sightline_offset])

    horizontal_displacement = explosion[:2] - DRONE_INITIAL[:2]
    speed = np.linalg.norm(horizontal_displacement) / explosion_time
    if not 70.0 <= speed <= 140.0 or not 0.0 <= explosion[2] <= DRONE_INITIAL[2]:
        return None
    fuse_delay = math.sqrt(2.0 * (DRONE_INITIAL[2] - explosion[2]) / GRAVITY)
    if fuse_delay > explosion_time:
        return None
    heading = math.atan2(horizontal_displacement[1], horizontal_displacement[0]) % (
        2.0 * math.pi
    )
    return np.array([heading, speed, explosion_time, fuse_delay])


def strategy_explosion(strategy: np.ndarray) -> np.ndarray:
    heading, speed, explosion_time, fuse_delay = strategy
    explosion = DRONE_INITIAL + np.array(
        [
            speed * explosion_time * math.cos(heading),
            speed * explosion_time * math.sin(heading),
            0.0,
        ]
    )
    explosion[2] = DRONE_INITIAL[2] - 0.5 * GRAVITY * fuse_delay**2
    return explosion


def strategy_duration(
    strategy: np.ndarray,
    target_points: np.ndarray,
    grid_step: float,
) -> tuple[float, list[tuple[float, float]]]:
    heading, speed, explosion_time, fuse_delay = strategy
    if not (
        0.0 <= heading <= 2.0 * math.pi
        and 70.0 <= speed <= 140.0
        and 0.0 <= fuse_delay <= min(explosion_time, MAX_FUSE_DELAY)
        and explosion_time < MISSILE_ARRIVAL
    ):
        return 0.0, []

    explosion = strategy_explosion(strategy)
    if explosion[2] < 0.0:
        return 0.0, []
    end = min(
        explosion_time + CLOUD_LIFETIME,
        MISSILE_ARRIVAL,
        explosion_time + explosion[2] / 3.0,
    )
    radius_function = lambda time: required_cloud_radius(
        missile_position(MISSILE_INITIAL, time),
        cloud_center(explosion, time - explosion_time),
        target_points,
    )
    intervals = shielding_intervals(
        radius_function,
        explosion_time,
        end,
        grid_step=grid_step,
    )
    return interval_measure(intervals), intervals


def main() -> None:
    search_points = cylinder_surface_points(72, 5, 2)

    def guided_objective(parameters: np.ndarray) -> float:
        strategy = decode_sightline_parameters(parameters)
        if strategy is None:
            return 0.0
        duration, _ = strategy_duration(strategy, search_points, 0.05)
        return -duration

    guided = differential_evolution(
        guided_objective,
        bounds=[(0.3, 3.0), (0.0, 6.0), (0.85, 0.9999)],
        seed=778,
        popsize=14,
        maxiter=80,
        tol=1e-6,
        polish=True,
        x0=np.array([1.0634, 2.4856, 0.94568]),
    )
    initial_strategy = decode_sightline_parameters(guided.x)
    if initial_strategy is None:
        raise RuntimeError("Geometry-guided search did not produce a feasible strategy")

    scale = np.array([0.01, 2.0, 0.1, 0.1])

    def local_objective(offset: np.ndarray) -> float:
        duration, _ = strategy_duration(
            initial_strategy + offset * scale,
            search_points,
            0.05,
        )
        return -duration

    local = minimize(
        local_objective,
        np.zeros(4),
        method="Nelder-Mead",
        options={"maxiter": 350, "xatol": 1e-7, "fatol": 1e-8, "adaptive": True},
    )
    strategy = initial_strategy + local.x * scale
    explosion = strategy_explosion(strategy)

    audit_rng = np.random.default_rng(20250902)
    audit_base, _ = strategy_duration(strategy, search_points, 0.05)
    audit_best = audit_base
    audit_feasible = 0
    for _ in range(400):
        perturbed = strategy + audit_rng.normal(size=4) * np.array([0.003, 0.5, 0.03, 0.02])
        perturbed[1] = np.clip(perturbed[1], 70.0, 140.0)
        perturbed_duration, _ = strategy_duration(perturbed, search_points, 0.05)
        if perturbed_duration > 0.0:
            audit_feasible += 1
        audit_best = max(audit_best, perturbed_duration)

    coarse_points = cylinder_surface_points(360, 21, 11)
    coarse_duration, coarse_intervals = strategy_duration(strategy, coarse_points, 0.01)
    fine_points = cylinder_surface_points(1440, 61, 25)
    fine_radius = lambda time: required_cloud_radius(
        missile_position(MISSILE_INITIAL, time),
        cloud_center(explosion, time - strategy[2]),
        fine_points,
    )
    fine_intervals = []
    for left, right in coarse_intervals:
        fine_intervals.append(
            (
                brentq(lambda time: fine_radius(time) - CLOUD_RADIUS, left - 0.03, left + 0.03),
                brentq(
                    lambda time: fine_radius(time) - CLOUD_RADIUS,
                    right - 0.03,
                    right + 0.03,
                ),
            )
        )

    heading, speed, explosion_time, fuse_delay = strategy
    release_time = explosion_time - fuse_delay
    release = DRONE_INITIAL + np.array(
        [speed * release_time * math.cos(heading), speed * release_time * math.sin(heading), 0.0]
    )
    result = {
        "status": "working_baseline",
        "optimality_claim": "none; geometry-guided global search plus local refinement",
        "model": "complete-cylinder line-of-sight shielding",
        "seed": 778,
        "heading_deg": math.degrees(heading) % 360.0,
        "speed_m_s": speed,
        "release_time_s": release_time,
        "fuse_delay_s": fuse_delay,
        "explosion_time_s": explosion_time,
        "release_point_m": release.tolist(),
        "explosion_point_m": explosion.tolist(),
        "shielding_intervals_s": [[left, right] for left, right in fine_intervals],
        "effective_shielding_duration_s": interval_measure(fine_intervals),
        "validation": {
            "coarse_surface_points": int(len(coarse_points)),
            "fine_surface_points": int(len(fine_points)),
            "coarse_duration_s": coarse_duration,
            "local_optimizer_success": bool(local.success),
            "local_optimizer_message": local.message,
            "local_perturbation_audit": {
                "seed": 20250902,
                "trials": 400,
                "feasible_trials": audit_feasible,
                "best_improvement_s": audit_best - audit_base,
            },
            "fine_endpoint_residuals_m": [
                fine_radius(time) - CLOUD_RADIUS
                for interval in fine_intervals
                for time in interval
            ],
        },
    }

    output = PROJECT_ROOT / "results" / "working" / "q2.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
