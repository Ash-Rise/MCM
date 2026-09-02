from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.optimize import brentq


GRAVITY = 9.8
CLOUD_RADIUS = 10.0
CLOUD_DESCENT_SPEED = 3.0
CLOUD_LIFETIME = 20.0
TARGET_RADIUS = 7.0
TARGET_HEIGHT = 10.0
TARGET_BASE_CENTER = np.array([0.0, 200.0, 0.0])


def missile_position(initial: np.ndarray, time: float) -> np.ndarray:
    """Position of a 300 m/s missile aimed at the false target at the origin."""
    initial = np.asarray(initial, dtype=float)
    return initial * (1.0 - 300.0 * time / np.linalg.norm(initial))


def explosion_point(
    drone_initial: np.ndarray,
    horizontal_velocity: np.ndarray,
    explosion_time: float,
    fuse_delay: float,
    gravity: float = GRAVITY,
) -> np.ndarray:
    """Explosion point for a bomb inheriting the drone's horizontal velocity."""
    drone_initial = np.asarray(drone_initial, dtype=float)
    horizontal_velocity = np.asarray(horizontal_velocity, dtype=float)
    point = drone_initial + horizontal_velocity * explosion_time
    point[2] = drone_initial[2] - 0.5 * gravity * fuse_delay**2
    return point


def cloud_center(
    initial_center: np.ndarray,
    time_since_explosion: float,
) -> np.ndarray:
    center = np.asarray(initial_center, dtype=float).copy()
    center[2] -= CLOUD_DESCENT_SPEED * time_since_explosion
    return center


def cylinder_surface_points(
    n_theta: int = 720,
    n_side_z: int = 31,
    n_cap_r: int = 15,
) -> np.ndarray:
    """Deterministic surface grid for the complete finite cylinder target."""
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)

    side = np.array(
        [
            [
                TARGET_RADIUS * cos_value,
                TARGET_BASE_CENTER[1] + TARGET_RADIUS * sin_value,
                z,
            ]
            for z in np.linspace(0.0, TARGET_HEIGHT, n_side_z)
            for cos_value, sin_value in zip(cos_theta, sin_theta, strict=True)
        ],
        dtype=float,
    )
    caps = np.array(
        [
            [
                radius * cos_value,
                TARGET_BASE_CENTER[1] + radius * sin_value,
                z,
            ]
            for z in (0.0, TARGET_HEIGHT)
            for radius in np.linspace(0.0, TARGET_RADIUS, n_cap_r)
            for cos_value, sin_value in zip(cos_theta, sin_theta, strict=True)
        ],
        dtype=float,
    )
    return np.vstack((side, caps))


def required_cloud_radius(
    observer: np.ndarray,
    cloud: np.ndarray,
    target_points: np.ndarray,
) -> float:
    """Largest cloud-to-sight-segment distance over the sampled full target."""
    observer = np.asarray(observer, dtype=float)
    cloud = np.asarray(cloud, dtype=float)
    segment = target_points - observer
    cloud_vector = cloud - observer
    fraction = np.sum(segment * cloud_vector, axis=1) / np.sum(segment**2, axis=1)
    fraction = np.clip(fraction, 0.0, 1.0)
    nearest = observer + fraction[:, None] * segment
    return float(np.linalg.norm(nearest - cloud, axis=1).max())


def shielding_intervals(
    required_radius: Callable[[float], float],
    start: float,
    end: float,
    radius: float = CLOUD_RADIUS,
    grid_step: float = 0.01,
    root_tolerance: float = 1e-11,
) -> list[tuple[float, float]]:
    """Locate intervals where the complete-target required radius is admissible."""
    times = np.arange(start, end + 0.5 * grid_step, grid_step)
    if times[-1] < end:
        times = np.append(times, end)
    values = np.array([required_radius(time) - radius for time in times])
    inside = values <= 0.0

    transitions = np.flatnonzero(inside[1:] != inside[:-1])
    roots = [
        brentq(
            lambda time: required_radius(time) - radius,
            float(times[index]),
            float(times[index + 1]),
            xtol=root_tolerance,
        )
        for index in transitions
    ]

    boundaries = [start, *roots, end]
    intervals: list[tuple[float, float]] = []
    for left, right in zip(boundaries[:-1], boundaries[1:], strict=True):
        midpoint = 0.5 * (left + right)
        if required_radius(midpoint) <= radius:
            intervals.append((left, right))
    return intervals


def interval_measure(intervals: list[tuple[float, float]]) -> float:
    return float(sum(right - left for left, right in intervals))
