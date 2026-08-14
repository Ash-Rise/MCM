from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

SOLUTION_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = SOLUTION_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from ambulance_model import (  # noqa: E402
    BUSY_MINUTES,
    Call,
    DAILY_CAP,
    DELAY_PENALTY_YUAN_PER_MINUTE,
    MINUTES_PER_DAY,
    _current_candidates,
    _known_wait,
    _predicted_zone_response,
    build_fleet,
    cumulative_response_loss,
    cumulative_response_losses,
    delay_penalty_cost,
    generate_calls,
    intraday_density,
    problem_statement_path,
    read_problem,
    simulate,
    solve_q1,
)


class AProblemTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.statement = problem_statement_path(SOLUTION_ROOT)
        cls.data = read_problem(cls.statement)

    def test_problem_statement_path_is_explicit_and_stable(self) -> None:
        self.assertEqual(
            self.statement.name,
            "problem-a-ambulance-dispatch-statement.docx",
        )
        self.assertEqual(self.statement.parent.name, "problem-statements")
        self.assertTrue(self.statement.is_file())

    def test_intraday_density_scalar_matches_vector_path(self) -> None:
        hours = np.array([-0.25, 0.0, 3.25, 9.0, 18.0, 24.25, 49.0])
        vector_values = np.asarray(intraday_density(hours), dtype=float)
        scalar_values = np.array([intraday_density(float(hour)) for hour in hours])

        self.assertTrue(all(type(intraday_density(float(hour))) is float for hour in hours))
        np.testing.assert_allclose(scalar_values, vector_values, rtol=1e-14, atol=1e-14)

    def test_q1_matches_frozen_contract(self) -> None:
        result = solve_q1(self.data)
        np.testing.assert_array_equal(result["vehicles"], [3, 2, 2, 2, 1, 2])
        np.testing.assert_array_equal(result["opened"], [1, 1, 1, 1, 1, 1])
        np.testing.assert_allclose(result["loads"], [36, 20, 24, 24, 12, 24], atol=1e-8)
        self.assertAlmostEqual(result["distance_mean"], 0.9415694291208043, places=10)
        self.assertAlmostEqual(result["service_radius_km"], 3.0, places=10)
        self.assertAlmostEqual(result["service_3km_coverage"], 121 / 140, places=10)
        self.assertAlmostEqual(result["strict_center_proxy_coverage"], 85 / 140, places=10)
        self.assertAlmostEqual(result["potential_3km_coverage"], 136 / 140, places=10)
        self.assertLessEqual(result["max_demand_residual"], 1e-8)
        self.assertLessEqual(result["max_capacity_violation"], 1e-8)
        np.testing.assert_allclose(
            self.data.hospital_distance,
            [3.2, 4.1, 5.8, 6.2, 7.5, 8.3, 5.1, 3.8, 9.2, 10.1],
        )
        np.testing.assert_allclose(self.data.area, [3, 2, 4, 5, 6, 7, 5, 3, 6, 4])
        np.testing.assert_allclose(self.data.population, [12, 6, 10, 8, 5, 3, 14, 9, 7, 2])
        np.testing.assert_allclose(
            self.data.demand_density,
            [28 / 3, 15 / 2, 18 / 4, 10 / 5, 8 / 6, 6 / 7, 20 / 5, 22 / 3, 9 / 6, 4 / 4],
        )

    def test_daily_cap_wait_crosses_midnight(self) -> None:
        ambulance = build_fleet(self.data)[0]
        ambulance.day_count = DAILY_CAP
        ambulance.busy_until = 1420.0
        self.assertAlmostEqual(_known_wait(ambulance, 1430.0, 1430.0), 10.0)
        self.assertAlmostEqual(_known_wait(ambulance, 1445.0, 1430.0), 0.0)

    def test_external_ambulances_activate_at_incident_start(self) -> None:
        fleet = build_fleet(
            self.data,
            external_sites=[2, 2],
            external_activation_min=100.0,
        )

        self.assertEqual(len(fleet), 14)
        self.assertEqual([ambulance.site for ambulance in fleet[-2:]], [2, 2])
        self.assertTrue(all(ambulance.external for ambulance in fleet[-2:]))
        self.assertTrue(all(ambulance.activation_min == 100.0 for ambulance in fleet[-2:]))
        self.assertEqual(len(_current_candidates(fleet, 99.0)), 12)
        self.assertEqual(len(_current_candidates(fleet, 100.0)), 14)

    def test_external_ambulance_is_invisible_to_forecast_before_activation(self) -> None:
        fleet = build_fleet(
            self.data,
            external_sites=[3],
            external_activation_min=100.0,
        )
        for ambulance in fleet[:-1]:
            ambulance.busy_until = 160.0

        before = _predicted_zone_response(
            self.data,
            fleet,
            zone=3,
            future_min=110.0,
            state_time_min=99.0,
            dispatched=None,
        )
        after = _predicted_zone_response(
            self.data,
            fleet,
            zone=3,
            future_min=110.0,
            state_time_min=100.0,
            dispatched=None,
        )

        self.assertGreater(before, after)
        self.assertAlmostEqual(after, 3.0)

    def test_queued_call_is_dispatched_when_external_ambulance_activates(self) -> None:
        calls = [Call(call_id, 99.0, 0) for call_id in range(13)]

        records, _ = simulate(
            self.data,
            calls,
            strategy="A",
            external_sites=[0],
            external_activation_min=100.0,
        )

        queued = records.loc[records["call_id"] == 12].iloc[0]
        self.assertEqual(int(queued["ambulance_id"]), 12)
        self.assertAlmostEqual(float(queued["dispatch_min"]), 100.0)
        self.assertAlmostEqual(float(queued["wait_min"]), 1.0)

    def test_counterfactual_loss_is_finite_and_nonnegative(self) -> None:
        fleet = build_fleet(self.data)
        fleet[1].busy_until = 25.0
        fleet[2].day_count = DAILY_CAP - 1
        value = cumulative_response_loss(self.data, fleet, fleet[2], 0.0)
        self.assertTrue(math.isfinite(value))
        self.assertGreaterEqual(value, 0.0)

    def test_batch_losses_match_scalar_reference(self) -> None:
        fleet = build_fleet(self.data)
        for ambulance in fleet:
            ambulance.busy_until = BUSY_MINUTES
        fleet[0].busy_until = 0.0
        fleet[-1].busy_until = 0.0
        candidates = [fleet[0], fleet[-1]]
        scalar = {
            ambulance.ambulance_id: cumulative_response_loss(self.data, fleet, ambulance, 0.0)
            for ambulance in candidates
        }
        batch = cumulative_response_losses(self.data, fleet, candidates, 0.0)
        self.assertGreater(max(scalar.values()), 0.0)
        for ambulance_id, expected in scalar.items():
            self.assertAlmostEqual(batch[ambulance_id], expected, places=10)

    def test_rate_multiplier_changes_future_loss_without_changing_default(self) -> None:
        fleet = build_fleet(self.data)
        for ambulance in fleet:
            ambulance.busy_until = BUSY_MINUTES
        fleet[0].busy_until = 0.0
        fleet[-1].busy_until = 0.0
        candidates = [fleet[0], fleet[-1]]

        baseline = cumulative_response_losses(self.data, fleet, candidates, 0.0)

        def incident_multiplier(_future_min: float) -> np.ndarray:
            multiplier = np.ones(len(self.data.zone_ids))
            multiplier[0] = 5.0
            return multiplier

        incident = cumulative_response_losses(
            self.data,
            fleet,
            candidates,
            0.0,
            rate_multiplier=incident_multiplier,
        )

        self.assertTrue(any(incident[key] > baseline[key] + 1e-9 for key in baseline))
        self.assertEqual(
            baseline,
            cumulative_response_losses(self.data, fleet, candidates, 0.0),
        )

    def test_common_calls_and_all_strategy_constraints(self) -> None:
        calls = generate_calls(self.data, days=2, seed=12345)
        self.assertEqual(len(calls), 280)
        configurations = {
            "A": {},
            "B": {"beta": 1.0, "delta": 1.0},
            "C": {"reserve_vector": [1, 0, 0, 0, 0, 0], "tau": 5.0},
        }
        for strategy, settings in configurations.items():
            with self.subTest(strategy=strategy):
                records, metrics = simulate(self.data, calls, strategy=strategy, **settings)
                self.assertEqual(len(records), len(calls))
                self.assertEqual(records["call_id"].tolist(), list(range(len(calls))))
                self.assertLessEqual(metrics["max_daily_dispatches_per_ambulance"], DAILY_CAP)
                self.assertTrue(np.isfinite(records["response_min"]).all())
                self.assertTrue((records["wait_min"] >= -1e-9).all())
                expected_costs = delay_penalty_cost(records["response_min"].to_numpy())
                self.assertAlmostEqual(
                    metrics["mean_delay_penalty_yuan_per_call"],
                    float(np.mean(expected_costs)),
                )
                self.assertAlmostEqual(
                    metrics["total_delay_penalty_yuan"],
                    float(np.sum(expected_costs)),
                )
                if strategy == "B":
                    self.assertTrue((records["c_loss_min"] >= -1e-9).all())

    def test_conditional_nhpp_generates_exactly_140_calls_each_day(self) -> None:
        days = 3
        calls = generate_calls(self.data, days=days, seed=20260811)
        arrivals = np.array([call.arrival_min for call in calls])
        arrival_days = np.floor(arrivals / MINUTES_PER_DAY).astype(int)

        self.assertEqual(len(calls), 140 * days)
        np.testing.assert_array_equal(np.bincount(arrival_days, minlength=days), [140] * days)
        self.assertTrue(np.all(np.diff(arrivals) >= 0.0))
        self.assertGreaterEqual(float(arrivals.min()), 0.0)
        self.assertLess(float(arrivals.max()), days * MINUTES_PER_DAY)

    def test_conditional_nhpp_is_reproducible_for_a_fixed_seed(self) -> None:
        first = generate_calls(self.data, days=2, seed=20260811)
        second = generate_calls(self.data, days=2, seed=20260811)

        self.assertEqual(first, second)

    def test_delay_penalty_charges_only_response_beyond_four_minutes(self) -> None:
        responses = np.array([3.5, 4.0, 5.25])
        costs = delay_penalty_cost(responses)

        np.testing.assert_allclose(
            costs,
            [0.0, 0.0, 1.25 * DELAY_PENALTY_YUAN_PER_MINUTE],
        )

    def test_busy_cycle_is_exactly_45_minutes(self) -> None:
        calls = generate_calls(self.data, days=1, seed=2026)
        records, _ = simulate(self.data, calls, strategy="A")
        for _, group in records.groupby("ambulance_id"):
            dispatches = group["dispatch_min"].to_numpy()
            if len(dispatches) > 1:
                self.assertTrue(np.all(np.diff(dispatches) >= BUSY_MINUTES - 1e-9))


if __name__ == "__main__":
    unittest.main()
