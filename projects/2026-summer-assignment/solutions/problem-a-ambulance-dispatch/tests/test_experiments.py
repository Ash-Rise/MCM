from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SOLUTION_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from run_experiments import (  # noqa: E402
    FINAL_MEASURE_DAYS,
    FINAL_REPLICATIONS,
    FIXED_WARMUP_DAYS,
    TUNING_MEASURE_DAYS,
    TUNING_REPLICATIONS,
    _append_rows,
    b_candidates,
    b_fine_candidates,
    c_candidates,
    daily_diagnostics,
    select_c,
    stage_result_path,
)

from ambulance_model import delay_penalty_cost  # noqa: E402


class FullExperimentTest(unittest.TestCase):
    def test_append_rows_preserves_existing_csv_header_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "results.csv"
            _append_rows(
                path,
                [
                    {
                        "candidate": "A",
                        "strategy": "A",
                        "mean_c_loss_min": None,
                        "reserve_dispatches": None,
                    }
                ],
            )
            _append_rows(
                path,
                [
                    {
                        "candidate": "C",
                        "strategy": "C",
                        "reserve_dispatches": 17,
                        "mean_c_loss_min": 2.5,
                    }
                ],
            )

            appended = pd.read_csv(path)
            self.assertEqual(appended.loc[1, "reserve_dispatches"], 17)
            self.assertEqual(appended.loc[1, "mean_c_loss_min"], 2.5)

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

    def test_daily_diagnostics_reports_four_minute_excess_cost(self) -> None:
        records = pd.DataFrame(
            [
                {"call_id": 0, "arrival_min": 10.0, "dispatch_min": 10.0, "response_min": 4.0},
                {"call_id": 1, "arrival_min": 20.0, "dispatch_min": 20.0, "response_min": 5.5},
                {"call_id": 2, "arrival_min": 1450.0, "dispatch_min": 1450.0, "response_min": 6.0},
            ]
        )
        daily = daily_diagnostics(records, total_days=2)

        self.assertAlmostEqual(
            daily.loc[0, "total_delay_penalty_yuan"],
            float(delay_penalty_cost(5.5)),
        )
        self.assertAlmostEqual(
            daily.loc[1, "total_delay_penalty_yuan"],
            float(delay_penalty_cost(6.0)),
        )

    def test_fixed_warmup_contract_is_thirty_days(self) -> None:
        self.assertEqual(FIXED_WARMUP_DAYS, 30)

    def test_compact_experiment_contract(self) -> None:
        self.assertEqual(TUNING_REPLICATIONS, 3)
        self.assertEqual(TUNING_MEASURE_DAYS, 7)
        self.assertEqual(FINAL_REPLICATIONS, 30)
        self.assertEqual(FINAL_MEASURE_DAYS, 30)

    def test_select_c_returns_best_reserve_even_when_all_are_slower_than_a(self) -> None:
        rows = []
        for seed in range(3):
            rows.extend(
                [
                    {
                        "candidate": "A",
                        "strategy": "A",
                        "seed": seed,
                        "mean_response_min": 5.0,
                        "strict_4min_rate": 0.50,
                        "p95_response_min": 8.0,
                        "regional_mean_gap_min": 2.0,
                    },
                    {
                        "candidate": "C_slow",
                        "strategy": "C",
                        "seed": seed,
                        "mean_response_min": 5.4,
                        "strict_4min_rate": 0.49,
                        "p95_response_min": 9.0,
                        "regional_mean_gap_min": 2.2,
                    },
                    {
                        "candidate": "C_best",
                        "strategy": "C",
                        "seed": seed,
                        "mean_response_min": 5.2,
                        "strict_4min_rate": 0.48,
                        "p95_response_min": 8.5,
                        "regional_mean_gap_min": 2.1,
                    },
                ]
            )

        self.assertEqual(select_c(pd.DataFrame(rows)), "C_best")

    def test_stage_result_path_binds_warmup_length(self) -> None:
        root = Path("results")
        self.assertEqual(stage_result_path(root, "tuning", 15), root / "tuning_W015.csv")
        self.assertNotEqual(
            stage_result_path(root, "tuning", 15),
            stage_result_path(root, "tuning", 20),
        )


if __name__ == "__main__":
    unittest.main()
