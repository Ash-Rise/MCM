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
    TARGET_BASE_CENTER,
    cloud_center,
    cylinder_surface_points,
    missile_position,
    required_cloud_radii,
)
from solve_q2 import (  # noqa: E402
    DRONE_INITIAL,
    MISSILE_ARRIVAL,
    MISSILE_INITIAL,
    decode_sightline_parameters,
    strategy_duration,
    strategy_explosion,
)


TARGET_CENTER = TARGET_BASE_CENTER + np.array([0.0, 0.0, 5.0])
SEARCH_POINTS = cylinder_surface_points(24, 3, 2)
GRID_STEP = 0.1


def sampled_metrics(
    strategy: np.ndarray,
    target_points: np.ndarray = SEARCH_POINTS,
    grid_step: float = GRID_STEP,
) -> tuple[float, float]:
    explosion_time = strategy[2]
    explosion = strategy_explosion(strategy)
    end = min(explosion_time + CLOUD_LIFETIME, MISSILE_ARRIVAL, explosion_time + explosion[2] / 3.0)
    times = np.arange(explosion_time, end + 0.5 * grid_step, grid_step)
    observers = np.array([missile_position(MISSILE_INITIAL, time) for time in times])
    clouds = np.array([cloud_center(explosion, time - explosion_time) for time in times])
    radii = required_cloud_radii(observers, clouds, target_points)
    return float(np.count_nonzero(radii <= CLOUD_RADIUS) * grid_step), float(radii.min())


def optimize(seed: int, speed_cap: float) -> dict[str, float | list[float]]:
    def objective(parameters: np.ndarray) -> float:
        strategy = decode_sightline_parameters(parameters)
        if strategy is None:
            return 1e4
        duration, minimum_radius = sampled_metrics(strategy)
        speed_violation = max(0.0, strategy[1] - speed_cap)
        base = -100.0 - duration if duration > 0.0 else minimum_radius - CLOUD_RADIUS
        return base + 20.0 * speed_violation

    result = differential_evolution(
        objective,
        bounds=[(0.3, 3.0), (0.0, 6.0), (0.85, 0.9999)],
        seed=seed,
        popsize=6,
        maxiter=25,
        tol=1e-4,
        polish=False,
        x0=np.array([1.0634, 2.4856, 0.94568]),
    )
    strategy = decode_sightline_parameters(result.x)
    if strategy is None or strategy[1] > speed_cap + 1e-5:
        raise RuntimeError(f"No feasible q2 strategy for seed={seed}, cap={speed_cap}")
    duration, minimum_radius = sampled_metrics(strategy)
    return {
        "seed": seed,
        "speed_cap_m_s": speed_cap,
        "guided_parameters": result.x.tolist(),
        "strategy": strategy.tolist(),
        "sampled_duration_s": duration,
        "minimum_required_radius_m": minimum_radius,
    }


def main() -> None:
    multistart = [optimize(seed, 140.0) for seed in (101, 202, 303, 404, 505)]
    speed_sweep = [optimize(900 + int(cap), cap) for cap in (90.0, 100.0, 110.0, 120.0, 130.0, 135.0, 140.0)]
    refinement_points = cylinder_surface_points(180, 11, 5)
    refinement_screen = []
    for candidate in multistart + speed_sweep:
        duration, minimum_radius = sampled_metrics(
            np.asarray(candidate["strategy"]), refinement_points, 0.01
        )
        refinement_screen.append(
            {
                "seed": candidate["seed"],
                "speed_cap_m_s": candidate["speed_cap_m_s"],
                "speed_m_s": candidate["strategy"][1],
                "sampled_duration_s": duration,
                "minimum_required_radius_m": minimum_radius,
            }
        )
    working = json.loads((PROJECT_ROOT / "results" / "working" / "q2.json").read_text(encoding="utf-8"))
    working_strategy = np.array(
        [
            math.radians(working["heading_deg"]),
            working["speed_m_s"],
            working["explosion_time_s"],
            working["fuse_delay_s"],
        ]
    )
    boundary_points = cylinder_surface_points(360, 21, 11)
    local_speed_boundary = []
    for speed in (130.0, 134.0, 136.0, 138.0, 139.0, 139.5, 139.9, 140.0):
        strategy = working_strategy.copy()
        strategy[1] = speed
        duration, _ = strategy_duration(strategy, boundary_points, 0.01)
        local_speed_boundary.append({"speed_m_s": speed, "duration_s": duration})

    strongest_screen = max(refinement_screen, key=lambda item: item["sampled_duration_s"])
    candidate_sources = multistart + speed_sweep
    strongest_source = next(item for item in candidate_sources if item["seed"] == strongest_screen["seed"])
    strongest_duration, strongest_intervals = strategy_duration(
        np.asarray(strongest_source["strategy"]), boundary_points, 0.01
    )
    result = {
        "status": "audit",
        "purpose": "q2 multistart stability and speed-cap boundary evidence",
        "grid_step_s": GRID_STEP,
        "surface_points": int(len(SEARCH_POINTS)),
        "multistart": multistart,
        "speed_cap_sweep": speed_sweep,
        "refinement_screen": {
            "grid_step_s": 0.01,
            "surface_points": int(len(refinement_points)),
            "candidates": refinement_screen,
        },
        "local_speed_boundary": local_speed_boundary,
        "strongest_independent_challenger": {
            "seed": strongest_source["seed"],
            "strategy": strongest_source["strategy"],
            "duration_s": strongest_duration,
            "intervals_s": strongest_intervals,
        },
    }
    output = PROJECT_ROOT / "results" / "audits" / "q2_optimality.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
