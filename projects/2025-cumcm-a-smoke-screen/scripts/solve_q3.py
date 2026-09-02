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
    interval_measure,
    merge_intervals,
    missile_position,
    required_cloud_radii,
)
from solve_q2 import (  # noqa: E402
    DRONE_INITIAL,
    MAX_FUSE_DELAY,
    MISSILE_ARRIVAL,
    MISSILE_INITIAL,
    strategy_duration,
    strategy_explosion,
)


SEARCH_POINTS = cylinder_surface_points(24, 3, 2)
GRID_STEP = 0.1


def decode(parameters: np.ndarray) -> list[np.ndarray] | None:
    heading, speed, release_first, slack_12, slack_23, *delays = parameters
    releases = np.array(
        [release_first, release_first + 1.0 + slack_12, release_first + 2.0 + slack_12 + slack_23]
    )
    if np.any(releases < 0.0) or np.any(np.asarray(delays) > MAX_FUSE_DELAY):
        return None
    strategies = [
        np.array([heading, speed, release + delay, delay])
        for release, delay in zip(releases, delays, strict=True)
    ]
    if any(strategy[2] >= MISSILE_ARRIVAL for strategy in strategies):
        return None
    return strategies


def sampled_score(strategies: list[np.ndarray]) -> tuple[float, float, list[float]]:
    occupied: set[int] = set()
    individual: list[float] = []
    minimum_radii: list[float] = []
    for strategy in strategies:
        explosion_time = strategy[2]
        explosion = strategy_explosion(strategy)
        if explosion[2] < 0.0:
            return 0.0, 1e4, [0.0, 0.0, 0.0]
        end = min(
            explosion_time + CLOUD_LIFETIME,
            MISSILE_ARRIVAL,
            explosion_time + explosion[2] / 3.0,
        )
        times = np.arange(explosion_time, end + 0.5 * GRID_STEP, GRID_STEP)
        observers = np.array([missile_position(MISSILE_INITIAL, time) for time in times])
        clouds = np.array([cloud_center(explosion, time - explosion_time) for time in times])
        radii = required_cloud_radii(observers, clouds, SEARCH_POINTS)
        indices = np.rint(times[radii <= CLOUD_RADIUS] / GRID_STEP).astype(int)
        occupied.update(indices.tolist())
        individual.append(float(len(indices) * GRID_STEP))
        minimum_radii.append(float(radii.min()))
    return float(len(occupied) * GRID_STEP), float(sum(minimum_radii)), individual


def main() -> None:
    bounds = [
        (0.05, 0.18),
        (70.0, 140.0),
        (0.0, 0.8),
        (0.0, 2.0),
        (0.0, 4.0),
        (0.0, 2.0),
        (0.0, 2.0),
        (0.0, 6.0),
    ]
    seed_point = np.array(
        [0.1107592315, 120.5264562, 0.00471594, 0.00505364, 1.48584753, 0.06833961, 0.00316271, 5.9]
    )

    def objective(parameters: np.ndarray) -> float:
        strategies = decode(parameters)
        if strategies is None:
            return 1e4
        union_duration, radius_sum, individual = sampled_score(strategies)
        if union_duration > 0.0:
            return -100.0 - union_duration - 0.01 * sum(individual)
        return radius_sum

    baseline_parameters = np.array(
        [0.11075923153944182, 120.52645621748812, 0.004715939500424593,
         0.005053637186724469, 1.4858475343571313, 0.06833961469631866,
         0.0031627065227155526, 9.15402389513332]
    )
    baseline_strategies = decode(baseline_parameters)
    if baseline_strategies is None:
        raise RuntimeError("Stored Q3 baseline is infeasible")
    baseline_duration, _, baseline_individual = sampled_score(baseline_strategies)
    runs = [(baseline_duration, baseline_individual, baseline_parameters, baseline_strategies)]
    for seed in (3201, 3202, 3203):
        result = differential_evolution(
            objective,
            bounds=bounds,
            seed=seed,
            popsize=10,
            maxiter=80,
            tol=1e-5,
            polish=False,
            x0=seed_point,
        )
        strategies = decode(result.x)
        if strategies is None:
            raise RuntimeError("Q3 search returned an infeasible strategy")
        duration, _, individual = sampled_score(strategies)
        runs.append((duration, individual, result.x, strategies))

    validation_points = cylinder_surface_points(360, 21, 11)
    validated_runs = []
    for run in runs:
        run_intervals = [
            strategy_duration(strategy, validation_points, 0.01)[1] for strategy in run[3]
        ]
        run_union = merge_intervals([interval for intervals in run_intervals for interval in intervals])
        validated_runs.append((interval_measure(run_union), run, run_intervals))
    _, selected_run, individual_intervals = max(validated_runs, key=lambda item: item[0])
    _, _, parameters, strategies = selected_run
    union_intervals = merge_intervals([interval for intervals in individual_intervals for interval in intervals])

    bombs = []
    for number, (strategy, intervals) in enumerate(zip(strategies, individual_intervals, strict=True), 1):
        heading, speed, explosion_time, fuse_delay = strategy
        release_time = explosion_time - fuse_delay
        horizontal_velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
        release = DRONE_INITIAL + horizontal_velocity * release_time
        bombs.append(
            {
                "bomb": number,
                "release_time_s": release_time,
                "fuse_delay_s": fuse_delay,
                "explosion_time_s": explosion_time,
                "release_point_m": release.tolist(),
                "explosion_point_m": strategy_explosion(strategy).tolist(),
                "shielding_intervals_s": intervals,
                "individual_duration_s": interval_measure(intervals),
            }
        )

    result = {
        "status": "working",
        "optimality_claim": "none; three seeded differential-evolution runs and high-resolution validation",
        "model": "complete-cylinder line-of-sight shielding",
        "heading_deg": math.degrees(strategies[0][0]),
        "speed_m_s": strategies[0][1],
        "bombs": bombs,
        "union_intervals_s": union_intervals,
        "effective_shielding_duration_s": interval_measure(union_intervals),
        "validation": {
            "search_grid_step_s": GRID_STEP,
            "search_surface_points": int(len(SEARCH_POINTS)),
            "validation_surface_points": int(len(validation_points)),
            "multistart_sampled_durations_s": [run[0] for run in runs],
            "validated_candidate_union_durations_s": [run[0] for run in validated_runs],
            "release_gaps_s": [bombs[i + 1]["release_time_s"] - bombs[i]["release_time_s"] for i in range(2)],
            "search_parameters": parameters.tolist(),
        },
    }
    output = PROJECT_ROOT / "results" / "working" / "q3.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
