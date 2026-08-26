from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOLUTION_ROOT / "src"))

from data_io import load_problem_data  # noqa: E402
from forecast_station import (  # noqa: E402
    CandidateSpec,
    M0,
    M1,
    M2,
    _design_matrix,
    _fit,
    compare_candidates,
)


SUPPORTING_DOCX = SOLUTION_ROOT.parents[1] / "problem-statements" / "problem-c-supporting-data.docx"


class ForecastValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = compare_candidates(load_problem_data(SUPPORTING_DOCX))

    def test_all_required_candidates_share_the_same_loo_protocol(self) -> None:
        comparison = self.result["candidate_comparison"]
        names = {row["candidate"] for row in comparison}
        self.assertTrue({"M0", "M1", "M2"}.issubset(names))
        loo = self.result["loo_predictions"]
        for name in names:
            self.assertEqual(sum(row["candidate"] == name for row in loo), 15)

    def test_selection_and_intervals_follow_contract(self) -> None:
        comparison = self.result["candidate_comparison"]
        selected = [row for row in comparison if row["selected_by_contract"]]
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0]["eligible"])
        forecast = self.result["day16_forecast"]
        selection = self.result["selection"]
        self.assertTrue(forecast["interval_point_locked_to_selected_model"])
        self.assertAlmostEqual(
            forecast["point_kwh"],
            selection["day16_point_from_selected_fit_kwh"],
        )
        self.assertEqual(forecast["point_model_coefficients"], selection["coefficients"])
        self.assertIn("HC3", forecast["interval_method"])
        correlations = forecast["absolute_residual_irradiation_spearman"]
        self.assertLess(
            abs(correlations["normalized_y_over_h_scale"]),
            abs(correlations["raw_scale"]),
        )
        pi_low, pi_high = forecast["prediction_95_kwh"]
        ci_low, ci_high = forecast["confidence_95_kwh"]
        point = forecast["point_kwh"]
        self.assertLessEqual(pi_low, ci_low)
        self.assertLessEqual(ci_low, point)
        self.assertLessEqual(point, ci_high)
        self.assertLessEqual(ci_high, pi_high)
        self.assertIn("day-16 weather forecast input uncertainty", forecast["uncertainty_scope"]["not_propagated"])

    def test_day16_point_and_bootstrap_keep_the_selected_full_fit_identity(self) -> None:
        data = load_problem_data(SUPPORTING_DOCX)
        result = compare_candidates(data)
        selection = result["selection"]
        forecast = result["day16_forecast"]

        specs = {
            "M0": M0,
            "M1": M1,
            "M2": M2,
            "M2_T": CandidateSpec("M2_T", "M2", ("temperature",), 2),
            "M2_W": CandidateSpec("M2_W", "M2", ("wind",), 2),
        }
        spec = specs[selection["selected_candidate"]]
        historical = data.historical_weather
        irradiation = np.asarray([row["irradiation_kwh_m2"] for row in historical])
        temperature = np.asarray([row["temperature_c"] for row in historical])
        wind = np.asarray([row["wind_m_s"] for row in historical])
        temperature_ref = float(np.mean(temperature))
        wind_ref = float(np.mean(wind))
        x = _design_matrix(spec, irradiation, temperature, wind, temperature_ref, wind_ref)
        fit = _fit(spec, x, data.station_generation)
        day16 = data.day16_weather
        x16 = _design_matrix(
            spec,
            np.asarray([day16["irradiation_kwh_m2"]]),
            np.asarray([day16["temperature_c"]]),
            np.asarray([day16["wind_m_s"]]),
            temperature_ref,
            wind_ref,
        )[0]

        expected_coefficients = {
            name: float(value)
            for name, value in zip(spec.parameter_names, fit["coefficients"])
        }
        expected_point = float(x16 @ fit["coefficients"])
        self.assertEqual(selection["coefficients"], expected_coefficients)
        self.assertEqual(forecast["point_model_coefficients"], expected_coefficients)
        self.assertAlmostEqual(selection["day16_point_from_selected_fit_kwh"], expected_point)
        self.assertAlmostEqual(forecast["point_kwh"], expected_point)
        self.assertEqual(forecast["candidate"], selection["selected_candidate"])
        self.assertEqual(
            forecast["bootstrap_sensitivity"]["point_model_refit"],
            "same selected candidate definition on original Y scale",
        )


if __name__ == "__main__":
    unittest.main()
