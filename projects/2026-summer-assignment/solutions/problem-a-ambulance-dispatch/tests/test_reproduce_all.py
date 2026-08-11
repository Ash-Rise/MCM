from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pandas as pd

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SOLUTION_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from reproduce_all import format_q3_report_row, q2_aggregates, rebuild_stage, verify_stage  # noqa: E402


class ReproduceAllTest(unittest.TestCase):
    def test_q1_q2_stage_never_calls_task_three_verification(self) -> None:
        with (
            patch("reproduce_all.verify_q1") as verify_q1,
            patch("reproduce_all.verify_q2") as verify_q2,
            patch("reproduce_all.verify_q3", side_effect=AssertionError("legacy q3 used")) as verify_q3,
            patch("reproduce_all.verify_figures") as verify_figures,
        ):
            verify_stage(SOLUTION_ROOT, "q1-q2")

        verify_q1.assert_called_once_with(SOLUTION_ROOT)
        verify_q2.assert_called_once_with(SOLUTION_ROOT)
        verify_figures.assert_called_once_with(SOLUTION_ROOT, questions=("q1", "q2"))
        verify_q3.assert_not_called()

    def test_q1_q2_rebuild_never_calls_task_three_aggregates(self) -> None:
        with (
            patch("reproduce_all.q2_aggregates", return_value=(pd.DataFrame(), pd.DataFrame())) as q2,
            patch("reproduce_all.emergency_summaries", side_effect=AssertionError("legacy q3 used")) as q3,
            patch.object(pd.DataFrame, "to_csv"),
            patch("pandas.read_csv", return_value=pd.DataFrame()),
        ):
            rebuild_stage(SOLUTION_ROOT, "q1-q2")

        q2.assert_called_once()
        q3.assert_not_called()

    def test_q2_aggregates_use_paired_seed_differences(self) -> None:
        rows = []
        for seed, offset in ((1, 0.0), (2, 1.0), (3, -1.0)):
            for candidate, difference in (
                ("A", 0.0),
                ("B_beta4_delta2", -0.25),
                ("C_r001000_tau7", -0.05),
            ):
                row = {metric: 1.0 for metric in (
                    "mean_delay_penalty_yuan_per_call",
                    "mean_daily_delay_penalty_yuan",
                    "strict_4min_rate",
                    "p90_response_min",
                    "p95_response_min",
                    "mean_wait_min",
                    "wait_probability",
                    "max_wait_min",
                    "max_queue",
                    "mean_end_backlog",
                    "regional_mean_gap_min",
                    "mean_ideal_chain_min",
                    "p95_ideal_chain_min",
                )}
                rows.append(
                    {
                        "candidate": candidate,
                        "seed": seed,
                        "mean_response_min": 5.0 + offset + difference,
                        **row,
                    }
                )

        summary, paired = q2_aggregates(pd.DataFrame(rows))
        self.assertEqual(len(summary), 42)
        differences = paired.set_index("comparison")["mean_difference_min"]
        self.assertAlmostEqual(differences["B_beta4_delta2-A"], -0.25)
        self.assertAlmostEqual(differences["C_r001000_tau7-A"], -0.05)
        self.assertTrue(np.isfinite(paired[["ci95_low", "ci95_high"]]).all().all())

    def test_q3_report_row_has_machine_checkable_rounding_and_valid_count(self) -> None:
        row = pd.Series(
            {
                "metric": "mean_response_min",
                "B_N_mean": 15.295128,
                "B_E_mean": 15.276950151,
                "mean_difference_B_E_minus_B_N": -0.018178,
                "ci95_low": -0.037230,
                "ci95_high": 0.000874,
                "valid_scenario_pairs": 592,
            }
        )
        self.assertEqual(
            format_q3_report_row(row),
            "| 全市事故期平均响应/min | 15.2951 | 15.2770 | "
            "$-0.0182\\ [-0.0372,\\ 0.0009]$ | 592 |",
        )


if __name__ == "__main__":
    unittest.main()
