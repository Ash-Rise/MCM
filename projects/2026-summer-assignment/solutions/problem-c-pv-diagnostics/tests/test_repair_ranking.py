from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOLUTION_ROOT / "src"))

from data_io import load_problem_data  # noqa: E402
from diagnose_faults import diagnose_components  # noqa: E402
from forecast_station import compare_candidates  # noqa: E402
from rank_repairs import rank_repairs  # noqa: E402


SUPPORTING_DOCX = SOLUTION_ROOT.parents[1] / "problem-statements" / "problem-c-supporting-data.docx"


class RepairRankingTests(unittest.TestCase):
    def test_analytical_counterfactual_and_top_ten_invariant(self) -> None:
        data = load_problem_data(SUPPORTING_DOCX)
        diagnosis, _ = diagnose_components(data)
        result = rank_repairs(data, diagnosis)
        ranking = result["ranking"]
        selected = result["priority_repairs"]
        self.assertEqual(len(selected), 10)
        self.assertTrue(result["summary"]["cutoff_sorting_invariant"])
        self.assertFalse(result["summary"]["optimization_solver_used"])
        self.assertGreaterEqual(
            min(row["recoverable_loss_kwh_day"] for row in selected),
            max(row["recoverable_loss_kwh_day"] for row in ranking[10:]),
        )
        self.assertTrue(
            all(abs(row["reconstruction_error_percentage_points"]) <= 1e-10 for row in ranking)
        )

    def test_day16_interval_metadata_limits_propagated_uncertainty(self) -> None:
        data = load_problem_data(SUPPORTING_DOCX)
        diagnosis, _ = diagnose_components(data)
        forecast = compare_candidates(data)
        result = rank_repairs(data, diagnosis, forecast)
        supplementary = result["summary"]["day16_supplementary"]
        scope = supplementary["interval_scope"]
        self.assertIn("repair effectiveness uncertainty", scope["not_propagated"])
        self.assertIn("historical recoverable losses and their sum", scope["held_fixed"])
        self.assertFalse(supplementary["changes_primary_ranking"])

    def test_day16_supplementary_result_keeps_historical_order_and_common_scale(self) -> None:
        data = load_problem_data(SUPPORTING_DOCX)
        diagnosis, _ = diagnose_components(data)
        historical = rank_repairs(data, diagnosis)
        forecast = compare_candidates(data)
        with_supplement = rank_repairs(data, diagnosis, forecast)

        self.assertEqual(
            historical["summary"]["selected_component_ids"],
            with_supplement["summary"]["selected_component_ids"],
        )
        self.assertEqual(
            [row["component_id"] for row in historical["ranking"]],
            [row["component_id"] for row in with_supplement["ranking"]],
        )

        historical_gain = historical["summary"]["historical_mean_gain_kwh_day"]
        station_mean = historical["summary"]["current_station_mean_kwh_day"]
        day16_forecast = forecast["day16_forecast"]
        supplementary = with_supplement["summary"]["day16_supplementary"]
        scale = day16_forecast["point_kwh"] / station_mean
        self.assertAlmostEqual(supplementary["expected_gain_kwh"], historical_gain * scale)
        for key in ("confidence_95_kwh", "prediction_95_kwh"):
            expected = [value * historical_gain / station_mean for value in day16_forecast[key]]
            for actual, target in zip(supplementary[key], expected):
                self.assertAlmostEqual(actual, target)


if __name__ == "__main__":
    unittest.main()
