from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOLUTION_ROOT / "src"))

from data_io import load_problem_data  # noqa: E402
from diagnose_faults import diagnose_components  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
