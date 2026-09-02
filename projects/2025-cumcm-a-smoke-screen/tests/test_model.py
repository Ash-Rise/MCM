from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from smoke_screen.model import (  # noqa: E402
    cylinder_surface_points,
    explosion_point,
    interval_measure,
    missile_position,
    required_cloud_radii,
    required_cloud_radius,
    shielding_intervals,
)


class ModelTests(unittest.TestCase):
    def test_missile_reaches_origin(self) -> None:
        initial = np.array([20000.0, 0.0, 2000.0])
        arrival = np.linalg.norm(initial) / 300.0
        np.testing.assert_allclose(missile_position(initial, arrival), np.zeros(3), atol=1e-10)

    def test_q1_explosion_point(self) -> None:
        point = explosion_point(
            np.array([17800.0, 0.0, 1800.0]),
            np.array([-120.0, 0.0, 0.0]),
            5.1,
            3.6,
        )
        np.testing.assert_allclose(point, np.array([17188.0, 0.0, 1736.496]), atol=1e-12)

    def test_surface_grid_respects_cylinder_bounds(self) -> None:
        points = cylinder_surface_points(36, 5, 4)
        radial = np.hypot(points[:, 0], points[:, 1] - 200.0)
        self.assertTrue(np.all(radial <= 7.0 + 1e-12))
        self.assertTrue(np.all((0.0 <= points[:, 2]) & (points[:, 2] <= 10.0)))

    def test_interval_location(self) -> None:
        intervals = shielding_intervals(lambda time: (time - 2.0) ** 2, 0.0, 4.0, radius=1.0)
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][0], 1.0, places=9)
        self.assertAlmostEqual(intervals[0][1], 3.0, places=9)
        self.assertAlmostEqual(interval_measure(intervals), 2.0, places=9)

    def test_vectorized_required_radius_matches_scalar(self) -> None:
        points = cylinder_surface_points(36, 5, 4)
        observers = np.array([[20000.0, 0.0, 2000.0], [19000.0, 600.0, 2100.0]])
        clouds = np.array([[17000.0, 0.0, 1700.0], [16500.0, 100.0, 1700.0]])
        vectorized = required_cloud_radii(observers, clouds, points, chunk_size=1)
        scalar = np.array(
            [required_cloud_radius(observer, cloud, points) for observer, cloud in zip(observers, clouds)]
        )
        np.testing.assert_allclose(vectorized, scalar, atol=1e-12)


if __name__ == "__main__":
    unittest.main()
