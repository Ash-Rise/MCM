"""Independent numerical and contract checks for the Problem B exact solver."""

from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOLVER_PATH = PROJECT_ROOT / "src" / "solve_problem_b.py"
SPEC = importlib.util.spec_from_file_location("solve_problem_b", SOLVER_PATH)
assert SPEC and SPEC.loader
solver = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = solver
SPEC.loader.exec_module(solver)


class ProblemBSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = solver.load_data(PROJECT_ROOT / "data" / "problem_b_data.json")

    def test_source_docx_hash_matches_data_contract(self) -> None:
        source = (PROJECT_ROOT / self.data["source_docx"]).resolve()
        self.assertEqual(solver.sha256_file(source), self.data["source_sha256"])

    def test_normal_solution_is_global_optimum_of_all_eight_combinations(self) -> None:
        best, candidates = solver.solve(self.data, "normal", frozenset())
        self.assertEqual(len(candidates), 8)
        self.assertEqual(sum(value.feasible for value in candidates), 8)
        self.assertEqual(
            {route.vehicle: route.route for route in best.routes},
            {
                "A": (0, 1, 4, 6, 0),
                "B": (0, 2, 5, 8, 0),
                "C": (0, 3, 9, 7, 0),
            },
        )
        self.assertEqual(best.late_count, 0)
        self.assertEqual(best.early_count, 0)
        self.assertTrue(math.isclose(best.distance_km, 103.87130557672644, abs_tol=1e-10))
        self.assertTrue(math.isclose(best.total_cost_yuan, 415.48522230690576, abs_tol=1e-10))

    def test_route_distances_match_independent_hand_calculation(self) -> None:
        expected = {
            "A": 29.94967372041929,
            "B": 41.25468518266346,
            "C": 32.66694667364369,
        }
        routes = {
            "A": (0, 1, 4, 6, 0),
            "B": (0, 2, 5, 8, 0),
            "C": (0, 3, 9, 7, 0),
        }
        for vehicle, route in routes.items():
            result = solver.evaluate_route(self.data, vehicle, route)
            self.assertTrue(math.isclose(result.distance_km, expected[vehicle], abs_tol=1e-10))
            self.assertLessEqual(result.distance_km, self.data["max_route_km"])
            self.assertLessEqual(result.demand_boxes, self.data["vehicle_capacity_boxes"])

    def test_vehicle_b_arrival_times_match_independent_calculation(self) -> None:
        route = solver.evaluate_route(self.data, "B", (0, 2, 5, 8, 0))
        store_stops = {stop.node: stop for stop in route.stops if stop.node_type == "store"}
        self.assertEqual(solver.format_clock(store_stops[5].arrival_minute), "04:52:18")
        self.assertEqual(solver.format_clock(store_stops[8].arrival_minute), "05:23:35")
        self.assertEqual(store_stops[5].late + store_stops[8].late, 0)

    def test_literal_closure_has_zero_effect_on_optimum(self) -> None:
        normal, _ = solver.solve(self.data, "normal", frozenset())
        disrupted, candidates = solver.solve(
            self.data, "disrupted", frozenset({tuple(self.data["closed_arc"])})
        )
        self.assertEqual(len(candidates), 8)
        self.assertEqual(sum(value.feasible for value in candidates), 4)
        self.assertEqual(
            {route.vehicle: route.route for route in disrupted.routes},
            {route.vehicle: route.route for route in normal.routes},
        )
        self.assertTrue(math.isclose(disrupted.total_cost_yuan - normal.total_cost_yuan, 0.0))
        self.assertFalse(any((2, 8) in tuple(zip(route.route, route.route[1:])) for route in disrupted.routes))

    def test_route_using_closed_arc_is_rejected(self) -> None:
        route = solver.evaluate_route(
            self.data,
            "B",
            (0, 2, 8, 5, 0),
            frozenset({(2, 8)}),
        )
        self.assertFalse(route.feasible)
        self.assertIn("closed_arc:2->8", route.violations)

    def test_service_time_zero_lateness_threshold(self) -> None:
        normal_threshold, normal = solver.maximum_zero_late_service_minutes(
            self.data, frozenset()
        )
        disrupted_threshold, disrupted = solver.maximum_zero_late_service_minutes(
            self.data, frozenset({(2, 8)})
        )
        expected = 345.0 - (
            270.0
            + 60.0
            * (
                math.hypot(10.0, 4.0)
                + math.hypot(2.0, 1.0)
                + math.hypot(18.0, 3.0)
            )
            / 35.0
        )
        self.assertTrue(math.isclose(normal_threshold, expected, abs_tol=2e-9))
        self.assertTrue(math.isclose(disrupted_threshold, normal_threshold, abs_tol=1e-9))
        self.assertEqual(normal.late_count, 0)
        self.assertEqual(disrupted.late_count, 0)


if __name__ == "__main__":
    unittest.main()
