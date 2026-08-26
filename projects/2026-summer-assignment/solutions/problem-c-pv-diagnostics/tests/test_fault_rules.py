from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOLUTION_ROOT / "src"))

from data_io import load_problem_data  # noqa: E402
from diagnose_faults import (  # noqa: E402
    HOTSPOT,
    MICROCRACK,
    NORMAL,
    OUTSIDE_RULE,
    classify_deviation,
    diagnose_components,
)


SUPPORTING_DOCX = SOLUTION_ROOT.parents[1] / "problem-statements" / "problem-c-supporting-data.docx"


class FaultRuleTests(unittest.TestCase):
    def test_exact_boundaries(self) -> None:
        self.assertEqual(classify_deviation(-15.0), MICROCRACK)
        self.assertEqual(classify_deviation(-5.0), NORMAL)
        self.assertEqual(classify_deviation(5.0), NORMAL)
        self.assertEqual(classify_deviation(-15.0001), HOTSPOT)
        self.assertEqual(classify_deviation(5.0001), OUTSIDE_RULE)

    def test_reference_is_only_a_post_classification_check(self) -> None:
        data = load_problem_data(SUPPORTING_DOCX)
        rows, summary = diagnose_components(data)
        self.assertEqual(len(rows), 100)
        self.assertEqual(summary["reference_agreement_rate"], 1.0)
        self.assertEqual(sum(summary["class_counts"].values()), 100)
        self.assertTrue(all(row["fault_class"] != OUTSIDE_RULE for row in rows))
        self.assertTrue(all(row["fault_class"] in {NORMAL, MICROCRACK, HOTSPOT} for row in rows))


if __name__ == "__main__":
    unittest.main()
