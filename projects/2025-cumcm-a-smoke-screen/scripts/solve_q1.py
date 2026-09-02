from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from smoke_screen.model import (  # noqa: E402
    CLOUD_LIFETIME,
    CLOUD_RADIUS,
    cloud_center,
    cylinder_surface_points,
    explosion_point,
    interval_measure,
    missile_position,
    shielding_intervals,
)
from smoke_screen.model import required_cloud_radius as geometric_radius  # noqa: E402


MISSILE_INITIAL = np.array([20000.0, 0.0, 2000.0])
DRONE_INITIAL = np.array([17800.0, 0.0, 1800.0])
DRONE_VELOCITY = np.array([-120.0, 0.0, 0.0])
RELEASE_TIME = 1.5
FUSE_DELAY = 3.6
EXPLOSION_TIME = RELEASE_TIME + FUSE_DELAY


def required_radius(time: float, target_points: np.ndarray, center: np.ndarray) -> float:
    missile = missile_position(MISSILE_INITIAL, time)
    cloud = cloud_center(center, time - EXPLOSION_TIME)
    return geometric_radius(missile, cloud, target_points)


def refine_boundaries(
    intervals: list[tuple[float, float]],
    coarse_points: np.ndarray,
    fine_points: np.ndarray,
    center: np.ndarray,
) -> list[tuple[float, float]]:
    refined: list[tuple[float, float]] = []
    for left, right in intervals:
        new_boundaries = []
        for boundary in (left, right):
            bracket_left = max(EXPLOSION_TIME, boundary - 0.03)
            bracket_right = min(EXPLOSION_TIME + CLOUD_LIFETIME, boundary + 0.03)
            fine_function = lambda time: required_radius(time, fine_points, center) - CLOUD_RADIUS
            if fine_function(bracket_left) * fine_function(bracket_right) <= 0.0:
                boundary = brentq(fine_function, bracket_left, bracket_right, xtol=1e-12)
            new_boundaries.append(boundary)
        refined.append((new_boundaries[0], new_boundaries[1]))
    return refined


def main() -> None:
    center = explosion_point(
        DRONE_INITIAL,
        DRONE_VELOCITY,
        EXPLOSION_TIME,
        FUSE_DELAY,
    )
    release_point = DRONE_INITIAL + DRONE_VELOCITY * RELEASE_TIME

    coarse_points = cylinder_surface_points(720, 31, 15)
    coarse_intervals = shielding_intervals(
        lambda time: required_radius(time, coarse_points, center),
        EXPLOSION_TIME,
        EXPLOSION_TIME + CLOUD_LIFETIME,
        grid_step=0.01,
    )
    fine_points = cylinder_surface_points(1440, 61, 25)
    intervals = refine_boundaries(coarse_intervals, coarse_points, fine_points, center)

    endpoint_residuals = [
        required_radius(time, fine_points, center) - CLOUD_RADIUS
        for interval in intervals
        for time in interval
    ]
    result = {
        "status": "working",
        "model": "complete-cylinder line-of-sight shielding",
        "gravity_m_s2": 9.8,
        "release_time_s": RELEASE_TIME,
        "fuse_delay_s": FUSE_DELAY,
        "explosion_time_s": EXPLOSION_TIME,
        "release_point_m": release_point.tolist(),
        "explosion_point_m": center.tolist(),
        "shielding_intervals_s": [[left, right] for left, right in intervals],
        "effective_shielding_duration_s": interval_measure(intervals),
        "validation": {
            "coarse_surface_points": int(len(coarse_points)),
            "fine_surface_points": int(len(fine_points)),
            "coarse_duration_s": interval_measure(coarse_intervals),
            "fine_endpoint_residuals_m": endpoint_residuals,
        },
    }

    output = PROJECT_ROOT / "results" / "working" / "q1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
