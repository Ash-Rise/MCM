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

from smoke_screen.model import cylinder_surface_points, interval_measure, merge_intervals  # noqa: E402
from solve_q2 import (  # noqa: E402
    DRONE_INITIAL,
    MAX_FUSE_DELAY,
    strategy_duration,
    strategy_explosion,
)
from solve_q3 import decode, sampled_score  # noqa: E402


def search(seed: int, x0: np.ndarray) -> tuple[float, int, np.ndarray, list[np.ndarray]]:
    bounds = [
        (0.0, 2.0 * math.pi), (70.0, 140.0), (0.0, 10.0), (0.0, 10.0),
        (0.0, 10.0), (0.0, MAX_FUSE_DELAY), (0.0, MAX_FUSE_DELAY),
        (0.0, MAX_FUSE_DELAY),
    ]
    lower = np.array([item[0] for item in bounds])
    upper = np.array([item[1] for item in bounds])
    rng = np.random.default_rng(seed)
    scales = np.array([0.35, 12.0, 0.8, 0.8, 0.8, 1.2, 1.2, 1.2])
    population = np.clip(x0 + rng.normal(size=(56, 8)) * scales, lower, upper)
    population[0] = np.clip(x0, lower, upper)

    def objective(parameters: np.ndarray) -> float:
        strategies = decode(parameters)
        if strategies is None:
            return 1e4
        union_duration, radius_sum, individual = sampled_score(strategies)
        active = sum(value > 0.0 for value in individual)
        if active:
            return -100.0 * active - union_duration
        return radius_sum

    result = differential_evolution(
        objective,
        bounds,
        seed=seed,
        init=population,
        maxiter=32,
        tol=1e-5,
        polish=False,
    )
    strategies = decode(result.x)
    if strategies is None:
        raise RuntimeError("Q3 global audit returned infeasible strategies")
    duration, _, individual = sampled_score(strategies)
    return duration, sum(value > 0.0 for value in individual), result.x, strategies


def main() -> None:
    incumbent = json.loads(
        (PROJECT_ROOT / "results" / "working" / "q3.json").read_text(encoding="utf-8")
    )
    east = np.asarray(incumbent["validation"]["search_parameters"], dtype=float)
    west = np.array([3.137, 137.0, 1.05, 0.01, 0.0, 4.10, 4.69, 5.13])
    north = np.array([0.5 * math.pi, 105.0, 1.0, 0.5, 0.5, 2.0, 3.0, 4.0])
    south = np.array([1.5 * math.pi, 105.0, 1.0, 0.5, 0.5, 2.0, 3.0, 4.0])
    seeds = [east, west, north, south]
    runs = [search(8001 + index, start) for index, start in enumerate(seeds)]

    screen_points = cylinder_surface_points(180, 11, 5)
    screened = []
    for sampled_duration, active, parameters, strategies in runs:
        intervals = [strategy_duration(strategy, screen_points, 0.01)[1] for strategy in strategies]
        union = merge_intervals([item for values in intervals for item in values])
        screened.append(
            {
                "sampled_duration_s": sampled_duration,
                "active_bombs_in_search": active,
                "parameters": parameters.tolist(),
                "screen_union_duration_s": interval_measure(union),
                "screen_individual_durations_s": [interval_measure(values) for values in intervals],
            }
        )
    best = max(screened, key=lambda item: item["screen_union_duration_s"])
    best_strategies = decode(np.asarray(best["parameters"]))
    if best_strategies is None:
        raise RuntimeError("Best Q3 audit parameters are infeasible")
    fine_points = cylinder_surface_points(360, 21, 11)
    fine_individual = [
        strategy_duration(strategy, fine_points, 0.01)[1] for strategy in best_strategies
    ]
    fine_union = merge_intervals([item for values in fine_individual for item in values])
    fine_duration = interval_measure(fine_union)
    result = {
        "status": "audit",
        "purpose": "Q3 broad-basin test of whether the third-bomb zero contribution is regional",
        "incumbent_union_duration_s": incumbent["effective_shielding_duration_s"],
        "runs": screened,
        "best_screened_union_duration_s": best["screen_union_duration_s"],
        "best_screened_active_bombs": sum(
            value > 0.0 for value in best["screen_individual_durations_s"]
        ),
        "best_fine_union_duration_s": fine_duration,
        "conclusion": (
            "challenger_found" if best["screen_union_duration_s"] > incumbent["effective_shielding_duration_s"]
            else "no_challenger_in_tested_basins"
        ),
    }
    output = PROJECT_ROOT / "results" / "audits" / "q3_global.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if fine_duration > incumbent["effective_shielding_duration_s"] + 1e-6:
        bombs = []
        for number, (strategy, intervals) in enumerate(
            zip(best_strategies, fine_individual, strict=True), 1
        ):
            heading, speed, explosion_time, fuse = strategy
            release_time = explosion_time - fuse
            velocity = np.array([speed * math.cos(heading), speed * math.sin(heading), 0.0])
            bombs.append(
                {
                    "bomb": number,
                    "release_time_s": release_time,
                    "fuse_delay_s": fuse,
                    "explosion_time_s": explosion_time,
                    "release_point_m": (DRONE_INITIAL + velocity * release_time).tolist(),
                    "explosion_point_m": strategy_explosion(strategy).tolist(),
                    "shielding_intervals_s": intervals,
                    "individual_duration_s": interval_measure(intervals),
                }
            )
        working = {
            "status": "working_broad_basin_candidate",
            "optimality_claim": "none; broad-basin three-bomb search with high-resolution validation",
            "model": "complete-cylinder line-of-sight shielding",
            "heading_deg": math.degrees(best_strategies[0][0]),
            "speed_m_s": best_strategies[0][1],
            "bombs": bombs,
            "union_intervals_s": fine_union,
            "effective_shielding_duration_s": fine_duration,
            "validation": {
                "search_audit": "results/audits/q3_global.json",
                "validation_surface_points": int(len(fine_points)),
                "release_gaps_s": [
                    bombs[index + 1]["release_time_s"] - bombs[index]["release_time_s"]
                    for index in range(2)
                ],
                "search_parameters": best["parameters"],
            },
        }
        (PROJECT_ROOT / "results" / "working" / "q3.json").write_text(
            json.dumps(working, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
