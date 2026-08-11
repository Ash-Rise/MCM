from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SOLUTION_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from ambulance_model import Call, problem_statement_path, read_problem  # noqa: E402
from run_emergency_experiments import (  # noqa: E402
    WARMUP_DAYS,
    generate_incident_calls,
    incident_rate_multiplier,
    summarize_incident,
    worst_start_hour,
)


class EmergencyExperimentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = read_problem(problem_statement_path(SOLUTION_ROOT))

    def test_fixed_warmup_is_thirty_days(self) -> None:
        self.assertEqual(WARMUP_DAYS, 30)

    def test_worst_start_maximizes_duration_mass(self) -> None:
        start = worst_start_hour(3.0)
        self.assertGreaterEqual(start, 0.0)
        self.assertLess(start, 24.0)
        grid = np.arange(0.0, 24.0, 0.25)
        candidate_masses = [
            worst_start_hour(3.0, candidate_start=float(candidate)) for candidate in grid
        ]
        self.assertAlmostEqual(max(candidate_masses), worst_start_hour(3.0, candidate_start=start), places=6)

    def test_incident_multiplier_is_five_only_in_zone_and_interval(self) -> None:
        multiplier = incident_rate_multiplier(zone=2, start_min=100.0, end_min=220.0, zone_count=10)
        np.testing.assert_array_equal(multiplier(99.9), np.ones(10))
        expected = np.ones(10)
        expected[2] = 5.0
        np.testing.assert_array_equal(multiplier(100.0), expected)
        np.testing.assert_array_equal(multiplier(219.9), expected)
        np.testing.assert_array_equal(multiplier(220.0), np.ones(10))

    def test_extra_calls_are_reproducible_and_inside_incident(self) -> None:
        first = generate_incident_calls(
            self.data,
            warmup_days=WARMUP_DAYS,
            incident_zone=3,
            start_hour=16.0,
            duration_hours=2.0,
            seed=41,
        )
        second = generate_incident_calls(
            self.data,
            warmup_days=WARMUP_DAYS,
            incident_zone=3,
            start_hour=16.0,
            duration_hours=2.0,
            seed=41,
        )
        self.assertEqual(first, second)
        start = WARMUP_DAYS * 1440.0 + 16.0 * 60.0
        end = start + 120.0
        self.assertTrue(all(call.zone == 3 for call in first))
        self.assertTrue(all(start <= call.arrival_min < end for call in first))

    def test_summary_keeps_delayed_incident_calls_and_excludes_later_arrivals(self) -> None:
        records = pd.DataFrame(
            [
                {"call_id": 0, "zone": 2, "arrival_min": 100.0, "dispatch_min": 105.0, "response_min": 9.0, "wait_min": 5.0},
                {"call_id": 1, "zone": 2, "arrival_min": 110.0, "dispatch_min": 260.0, "response_min": 154.0, "wait_min": 150.0},
                {"call_id": 2, "zone": 1, "arrival_min": 150.0, "dispatch_min": 155.0, "response_min": 8.0, "wait_min": 5.0},
                {"call_id": 3, "zone": 2, "arrival_min": 221.0, "dispatch_min": 221.0, "response_min": 4.0, "wait_min": 0.0},
            ]
        )
        summary = summarize_incident(records, incident_zone=2, start_min=100.0, end_min=220.0)
        self.assertEqual(summary["calls"], 3)
        self.assertEqual(summary["incident_zone_calls"], 2)
        self.assertEqual(summary["nonincident_zone_calls"], 1)
        self.assertAlmostEqual(summary["mean_response_min"], 57.0)
        self.assertEqual(summary["max_incident_queue"], 2)


if __name__ == "__main__":
    unittest.main()
