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
import run_emergency_experiments as emergency  # noqa: E402
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

    def test_any_duration_inside_continuous_domain_is_legal(self) -> None:
        self.assertTrue(hasattr(emergency, "validate_duration"))
        self.assertEqual(emergency.validate_duration(3.25), 3.25)
        with self.assertRaises(ValueError):
            emergency.validate_duration(0.49)
        with self.assertRaises(ValueError):
            emergency.validate_duration(12.01)

    def test_six_legacy_durations_are_only_the_initial_design(self) -> None:
        self.assertEqual(emergency.INITIAL_DURATIONS_HOURS, (0.5, 1.0, 2.0, 4.0, 8.0, 12.0))
        self.assertGreater(emergency.MAX_DURATION_NODES, len(emergency.INITIAL_DURATIONS_HOURS))
        self.assertEqual(emergency.DURATION_DOMAIN_HOURS, (0.5, 12.0))

    def test_arbitrary_selected_duration_builds_all_zone_scenarios(self) -> None:
        self.assertTrue(hasattr(emergency, "build_scenarios"))
        scenarios = emergency.build_scenarios(self.data, [3.25])
        self.assertEqual(len(scenarios), 10)
        self.assertEqual(set(scenarios["duration_hours"]), {3.25})
        self.assertEqual(set(scenarios["incident_zone"]), set(range(1, 11)))
        self.assertTrue(scenarios["start_hour"].between(0.0, 24.0, inclusive="left").all())

    @staticmethod
    def _synthetic_replicates() -> pd.DataFrame:
        rows = []
        for duration in (0.5, 1.0, 2.0, 4.0, 8.0, 12.0):
            for seed in (1, 2, 3, 4):
                for mode, shift in (("B_N", 0.0), ("B_E", -0.15 * duration - 0.005 * seed)):
                    response = 5.0 + 0.12 * duration + 0.03 * seed + shift
                    rows.append(
                        {
                            "mode": mode,
                            "incident_zone": 1,
                            "duration_hours": duration,
                            "start_hour": 17.0,
                            "seed": seed,
                            "call_digest": f"{duration}-{seed}",
                            "mean_response_min": response,
                            "p95_response_min": response + 2.0,
                            "strict_4min_rate": 0.5 - 0.01 * duration - 0.005 * seed,
                            "max_incident_queue": 1.0 + 0.2 * duration + 0.1 * seed,
                            "incident_zone_mean_response_min": response + 0.5 * shift,
                            "nonincident_zone_mean_response_min": response - 0.25 * shift,
                            "max_daily_dispatches_per_ambulance": 12,
                        }
                    )
        return pd.DataFrame(rows)

    @staticmethod
    def _synthetic_scoped_replicates() -> pd.DataFrame:
        rows = []
        for duration in (0.5, 1.0, 2.0, 4.0, 8.0, 12.0):
            for seed in (1, 2, 3, 4):
                for zone in range(1, 11):
                    local_calls = 2 + zone
                    other_calls = 20 - zone
                    for mode, shift in (("B_N", 0.0), ("B_E", -0.02 * duration)):
                        rows.append(
                            {
                                "mode": mode,
                                "incident_zone": zone,
                                "duration_hours": duration,
                                "seed": seed,
                                "incident_zone_calls": local_calls,
                                "incident_zone_mean_response_min": 5.0 + 0.1 * zone + shift,
                                "nonincident_zone_calls": other_calls,
                                "nonincident_zone_mean_response_min": 6.0 - 0.05 * zone + shift,
                            }
                        )
        return pd.DataFrame(rows)

    def test_adaptive_design_targets_curvature_and_uncertainty(self) -> None:
        self.assertTrue(hasattr(emergency, "select_adaptive_midpoints"))
        durations = np.array([0.5, 1.0, 2.0, 4.0, 8.0, 12.0])
        rows = []
        for duration, mean in zip(durations, [0, 0, 0, 10, 10, 10], strict=True):
            rows.append(
                {
                    "curve_id": "curvature",
                    "duration_hours": duration,
                    "mean": mean,
                    "ci_half_width": 0.01,
                }
            )
        for duration in durations:
            rows.append(
                {
                    "curve_id": "uncertainty",
                    "duration_hours": duration,
                    "mean": 0.0,
                    "ci_half_width": 5.0 if duration >= 8.0 else 0.01,
                }
            )
        selected = emergency.select_adaptive_midpoints(
            pd.DataFrame(rows), durations, max_new_points=2
        )
        self.assertIn(10.0, set(selected["duration_hours"]))
        self.assertTrue(set(selected["duration_hours"]) & {1.5, 3.0, 6.0})
        self.assertTrue(set(selected["reason"]) <= {"high_curvature", "high_uncertainty", "wide_interval"})

    def test_acquisition_curves_cover_zones_modes_and_metrics(self) -> None:
        self.assertTrue(hasattr(emergency, "build_acquisition_curves"))
        curves = emergency.build_acquisition_curves(self._synthetic_replicates())
        self.assertEqual(
            set(curves["metric"]),
            {"mean_response_min", "p95_response_min", "strict_4min_rate", "max_incident_queue"},
        )
        self.assertEqual(set(curves["mode"]), {"B_N", "B_E", "B_E-B_N"})
        self.assertTrue(curves["mean"].between(-1.2, 1.2).all())
        self.assertTrue(curves["ci_half_width"].between(0.0, 1.2).all())

    def test_response_surface_has_replication_level_confidence_bands(self) -> None:
        self.assertTrue(hasattr(emergency, "build_response_surfaces"))
        grid = np.array([0.5, 1.25, 2.0, 4.0, 8.0, 12.0])
        absolute, paired = emergency.build_response_surfaces(
            self._synthetic_replicates(), evaluation_grid=grid
        )
        curve = absolute[
            (absolute["incident_zone"] == 1)
            & (absolute["mode"] == "B_N")
            & (absolute["metric"] == "mean_response_min")
        ]
        self.assertEqual(set(curve["duration_hours"]), set(grid))
        self.assertTrue((curve["replications"] == 4).all())
        self.assertTrue((curve["ci95_low"] < curve["mean"]).all())
        self.assertTrue((curve["ci95_high"] > curve["mean"]).all())
        self.assertEqual(curve.loc[curve["duration_hours"] == 1.25, "sampled_node"].item(), False)
        effect = paired[
            (paired["incident_zone"] == 1)
            & (paired["metric"] == "mean_response_min")
        ]
        self.assertEqual(set(effect["duration_hours"]), set(grid))
        self.assertTrue((effect["replications"] == 4).all())

    def test_default_response_surface_grid_contains_every_sampled_node(self) -> None:
        replicates = self._synthetic_replicates()
        absolute, paired = emergency.build_response_surfaces(replicates)
        sampled = set(replicates["duration_hours"].unique())
        absolute_nodes = absolute.loc[absolute["sampled_node"], "duration_hours"]
        paired_nodes = paired.loc[paired["sampled_node"], "duration_hours"]
        self.assertEqual(set(absolute_nodes), sampled)
        self.assertEqual(set(paired_nodes), sampled)

    def test_scoped_paired_surfaces_keep_every_duration_separate(self) -> None:
        self.assertTrue(hasattr(emergency, "build_scoped_paired_surfaces"))
        grid = np.array([0.5, 1.0, 3.0, 12.0])
        surface = emergency.build_scoped_paired_surfaces(
            self._synthetic_scoped_replicates(), evaluation_grid=grid
        )
        self.assertEqual(
            set(surface["metric"]),
            {"incident_zone_mean_response_min", "nonincident_zone_mean_response_min"},
        )
        self.assertEqual(set(surface["duration_hours"]), set(grid))
        self.assertTrue((surface["replications"] == 4).all())
        self.assertTrue((surface["incident_zone_scenarios"] == 10).all())
        self.assertEqual(
            set(surface.loc[surface["sampled_node"], "duration_hours"]),
            {0.5, 1.0, 12.0},
        )
        local = surface[
            (surface["metric"] == "incident_zone_mean_response_min")
            & (surface["duration_hours"] == 12.0)
        ].iloc[0]
        short = surface[
            (surface["metric"] == "incident_zone_mean_response_min")
            & (surface["duration_hours"] == 0.5)
        ].iloc[0]
        self.assertLess(local["mean_difference_B_E_minus_B_N"], short["mean_difference_B_E_minus_B_N"])

    def test_scoped_paired_surfaces_weight_all_calls_across_ten_scenarios(self) -> None:
        rows = []
        for duration in (0.5, 12.0):
            for seed in (1, 2):
                for zone in range(1, 11):
                    calls = 10 if zone == 1 else 1
                    effect = 2.0 if zone == 1 else 0.0
                    for mode, response in (("B_N", 5.0), ("B_E", 5.0 + effect)):
                        rows.append(
                            {
                                "mode": mode,
                                "incident_zone": zone,
                                "duration_hours": duration,
                                "seed": seed,
                                "incident_zone_calls": calls,
                                "incident_zone_mean_response_min": response,
                                "nonincident_zone_calls": calls,
                                "nonincident_zone_mean_response_min": response,
                            }
                        )
        surface = emergency.build_scoped_paired_surfaces(
            pd.DataFrame(rows), evaluation_grid=np.array([0.5, 12.0])
        )
        expected = 20.0 / 19.0
        np.testing.assert_allclose(
            surface["mean_difference_B_E_minus_B_N"], expected, rtol=0.0, atol=1e-12
        )

    def test_scoped_paired_surfaces_reject_missing_incident_zone_scenario(self) -> None:
        damaged = self._synthetic_scoped_replicates()
        damaged = damaged[
            ~(
                (damaged["duration_hours"] == 0.5)
                & (damaged["seed"] == 1)
                & (damaged["incident_zone"] == 10)
            )
        ]
        with self.assertRaisesRegex(AssertionError, "all ten incident-zone scenarios"):
            emergency.build_scoped_paired_surfaces(damaged)

    def test_scoped_paired_surfaces_reject_mismatched_policy_call_counts(self) -> None:
        damaged = self._synthetic_scoped_replicates()
        mask = (
            (damaged["duration_hours"] == 0.5)
            & (damaged["seed"] == 1)
            & (damaged["incident_zone"] == 10)
            & (damaged["mode"] == "B_E")
        )
        damaged.loc[mask, "incident_zone_calls"] += 1
        with self.assertRaisesRegex(AssertionError, "identical scoped call counts"):
            emergency.build_scoped_paired_surfaces(damaged)

    def test_duration_table_never_aggregates_across_duration(self) -> None:
        self.assertTrue(hasattr(emergency, "build_duration_table"))
        table = emergency.build_duration_table(self._synthetic_replicates())
        self.assertIn("duration_hours", table.columns)
        self.assertEqual(set(table["duration_hours"]), {0.5, 1.0, 2.0, 4.0, 8.0, 12.0})
        self.assertEqual(
            table.groupby(["incident_zone", "duration_hours", "metric"]).size().max(),
            1,
        )
        self.assertNotIn("overall", set(table.columns))

    def test_citywide_duration_table_averages_all_ten_scenarios_within_seed(self) -> None:
        self.assertTrue(hasattr(emergency, "build_citywide_duration_table"))
        table = emergency.build_citywide_duration_table(
            self._synthetic_scoped_replicates(), metric="incident_zone_mean_response_min"
        )
        self.assertEqual(set(table["duration_hours"]), {0.5, 1.0, 2.0, 4.0, 8.0, 12.0})
        self.assertTrue((table["replications"] == 4).all())
        self.assertTrue((table["incident_zone_scenarios"] == 10).all())
        expected = -0.02 * table["duration_hours"].to_numpy(dtype=float)
        np.testing.assert_allclose(
            table["mean_difference_B_E_minus_B_N"], expected, rtol=0.0, atol=1e-12
        )

    def test_citywide_duration_table_rejects_incomplete_scenario_sets(self) -> None:
        damaged = self._synthetic_scoped_replicates()
        damaged = damaged[
            ~(
                (damaged["duration_hours"] == 0.5)
                & (damaged["seed"] == 1)
                & (damaged["incident_zone"] == 10)
            )
        ]
        with self.assertRaisesRegex(AssertionError, "all ten incident-zone scenarios"):
            emergency.build_citywide_duration_table(
                damaged, metric="incident_zone_mean_response_min"
            )

    def test_frozen_initial_replicates_pass_strict_reuse_validation(self) -> None:
        self.assertTrue(hasattr(emergency, "validate_initial_reuse"))
        output = SOLUTION_ROOT / "results" / "task-3"
        replicates = pd.read_csv(output / "replicates.csv")
        scenarios = pd.read_csv(output / "scenarios.csv")
        initial = set(emergency.INITIAL_DURATIONS_HOURS)
        emergency.validate_initial_reuse(
            replicates[replicates["duration_hours"].isin(initial)],
            scenarios[scenarios["duration_hours"].isin(initial)],
        )

    def test_initial_reuse_rejects_a_mismatched_paired_call_stream(self) -> None:
        self.assertTrue(hasattr(emergency, "validate_initial_reuse"))
        output = SOLUTION_ROOT / "results" / "task-3"
        replicates = pd.read_csv(output / "replicates.csv")
        scenarios = pd.read_csv(output / "scenarios.csv")
        initial = set(emergency.INITIAL_DURATIONS_HOURS)
        damaged = replicates[replicates["duration_hours"].isin(initial)].copy()
        damaged.loc[damaged.index[0], "call_digest"] = "mismatched-call-stream"
        with self.assertRaisesRegex(AssertionError, "identical calls"):
            emergency.validate_initial_reuse(
                damaged,
                scenarios[scenarios["duration_hours"].isin(initial)],
            )


if __name__ == "__main__":
    unittest.main()
