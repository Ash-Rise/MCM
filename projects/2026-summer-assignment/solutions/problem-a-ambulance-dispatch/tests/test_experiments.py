from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SOLUTION_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from run_experiments import (  # noqa: E402
    _mser5_deletion,
    b_candidates,
    b_fine_candidates,
    c_candidates,
    daily_diagnostics,
    detect_warmup,
    stage_result_path,
)


class FullExperimentTest(unittest.TestCase):
    def test_parameter_counts_match_frozen_contract(self) -> None:
        self.assertEqual(len(b_candidates()), 20)
        self.assertEqual(len(c_candidates()), 235)
        self.assertEqual(len({candidate["candidate"] for candidate in c_candidates()}), 235)

    def test_b_fine_grid_is_local_and_excludes_coarse_duplicates(self) -> None:
        fine = b_fine_candidates("B_beta1_delta1")
        pairs = {(candidate["beta"], candidate["delta"]) for candidate in fine}
        self.assertEqual(pairs, {(0.75, 0.75), (0.75, 1.0), (0.75, 1.25), (1.0, 0.75), (1.0, 1.25), (1.5, 0.75), (1.5, 1.0), (1.5, 1.25)})

    def test_daily_diagnostics_tracks_backlog_and_busy_at_midnight(self) -> None:
        records = pd.DataFrame(
            [
                {"call_id": 0, "arrival_min": 10.0, "dispatch_min": 20.0, "response_min": 4.0},
                {"call_id": 1, "arrival_min": 1400.0, "dispatch_min": 1420.0, "response_min": 6.0},
                {"call_id": 2, "arrival_min": 1430.0, "dispatch_min": 1450.0, "response_min": 8.0},
                {"call_id": 3, "arrival_min": 1500.0, "dispatch_min": 1500.0, "response_min": 3.0},
            ]
        )
        daily = daily_diagnostics(records, total_days=2)
        self.assertAlmostEqual(daily.loc[0, "mean_response_min"], 6.0)
        self.assertEqual(daily.loc[0, "end_backlog"], 1)
        self.assertEqual(daily.loc[0, "busy_at_midnight"], 1)
        self.assertAlmostEqual(daily.loc[1, "mean_response_min"], 3.0)
        self.assertEqual(daily.loc[1, "end_backlog"], 0)
        self.assertEqual(daily.loc[1, "busy_at_midnight"], 0)

    def test_constant_daily_series_has_minimum_evidence_warmup(self) -> None:
        series = np.column_stack(
            [np.full(90, 2.0), np.full(90, 4.0), np.full(90, 7.0)]
        )
        self.assertEqual(detect_warmup(series), 0)

    def test_stationary_noise_is_not_mistaken_for_initialization_bias(self) -> None:
        rng = np.random.default_rng(20260811)
        stable = np.column_stack(
            [
                11.0 + rng.normal(0.0, 2.0, 90),
                1.4 + rng.normal(0.0, 0.35, 90),
                23.0 + rng.normal(0.0, 4.7, 90),
            ]
        )
        warmup = detect_warmup(stable)
        self.assertGreaterEqual(warmup, 0)
        self.assertLessEqual(warmup, 90)

    def test_transient_bias_delays_warmup(self) -> None:
        rng = np.random.default_rng(7)
        stable = np.column_stack(
            [
                11.0 + rng.normal(0.0, 0.2, 90),
                1.4 + rng.normal(0.0, 0.05, 90),
                23.0 + rng.normal(0.0, 0.4, 90),
            ]
        )
        stable[:25] += np.array([5.0, 0.8, 10.0])
        self.assertGreaterEqual(detect_warmup(stable), 25)

    def test_slow_transient_requests_longer_pilot(self) -> None:
        days = np.arange(90)
        slow = 10.0 + 10.0 * np.exp(-days / 30.0) + 0.2 * np.sin(days)
        _, at_boundary = _mser5_deletion(slow)
        self.assertTrue(at_boundary)

    def test_stage_result_path_binds_warmup_length(self) -> None:
        root = Path("results")
        self.assertEqual(stage_result_path(root, "tuning", 15), root / "tuning_W015.csv")
        self.assertNotEqual(
            stage_result_path(root, "tuning", 15),
            stage_result_path(root, "tuning", 20),
        )


if __name__ == "__main__":
    unittest.main()
