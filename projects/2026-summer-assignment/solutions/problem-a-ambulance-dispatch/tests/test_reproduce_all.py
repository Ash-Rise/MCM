from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pandas as pd

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SOLUTION_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from reproduce_all import (  # noqa: E402
    LEGACY_Q3_EVIDENCE_FILENAMES,
    q2_aggregates,
    rebuild_stage,
    remove_legacy_q3_outputs,
    verify_q3,
    verify_stage,
)
from generate_figures import q3_evidence_sources  # noqa: E402


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

    def test_task_three_rebuild_uses_duration_resolved_outputs(self) -> None:
        with (
            patch("reproduce_all.q2_aggregates", return_value=(pd.DataFrame(), pd.DataFrame())),
            patch("reproduce_all.emergency_summaries", return_value=(pd.DataFrame(), pd.DataFrame())),
            patch("reproduce_all.build_duration_table", return_value=pd.DataFrame()) as duration_table,
            patch("reproduce_all.build_citywide_duration_table", return_value=pd.DataFrame()) as citywide_table,
            patch("reproduce_all.build_response_surfaces", return_value=(pd.DataFrame(), pd.DataFrame())) as surfaces,
            patch("reproduce_all.build_scoped_paired_surfaces", return_value=pd.DataFrame()) as scoped_surfaces,
            patch.object(pd.DataFrame, "to_csv"),
            patch("pandas.read_csv", return_value=pd.DataFrame()),
        ):
            rebuild_stage(SOLUTION_ROOT, "all")

        duration_table.assert_called_once()
        citywide_table.assert_called_once()
        surfaces.assert_called_once()
        scoped_surfaces.assert_called_once()

    def test_task_three_verification_includes_external_support_evidence(self) -> None:
        with patch("reproduce_all.verify_external_support") as verify_external:
            verify_q3(SOLUTION_ROOT)

        verify_external.assert_called_once_with(SOLUTION_ROOT)

    def test_task_three_figures_reject_cross_duration_aggregate_sources(self) -> None:
        sources = q3_evidence_sources()
        self.assertEqual(
            sources,
            {
                "raw_q3_incident_load": "scenarios.csv",
                "process_q3_duration_zone": "response_surfaces.csv",
                "result_q3_response_curve": "response_surfaces.csv",
                "result_q3_paired_effect": "scoped_paired_response_surfaces.csv",
            },
        )
        self.assertFalse(any("aggregate" in source for source in sources.values()))

    def test_legacy_cross_duration_outputs_are_removed_by_exact_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for name in LEGACY_Q3_EVIDENCE_FILENAMES:
                (output / name).write_text("stale", encoding="utf-8")
            keep = output / "duration_table.csv"
            keep.write_text("current", encoding="utf-8")

            removed = remove_legacy_q3_outputs(output)

            self.assertEqual(set(removed), set(LEGACY_Q3_EVIDENCE_FILENAMES))
            self.assertTrue(keep.is_file())
            self.assertFalse(any((output / name).exists() for name in LEGACY_Q3_EVIDENCE_FILENAMES))


if __name__ == "__main__":
    unittest.main()
