from __future__ import annotations

import sys
import unittest
from pathlib import Path


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOLUTION_ROOT / "src"))

from data_io import EXPECTED_IDS, load_problem_data  # noqa: E402


SUPPORTING_DOCX = SOLUTION_ROOT.parents[1] / "problem-statements" / "problem-c-supporting-data.docx"


class DataContractTests(unittest.TestCase):
    def test_authoritative_supporting_data_shape_and_alignment(self) -> None:
        data = load_problem_data(SUPPORTING_DOCX)
        self.assertEqual(data.component_ids, EXPECTED_IDS)
        self.assertEqual(data.generation.shape, (100, 15))
        self.assertEqual(data.deviation_pct.shape, (100,))
        self.assertEqual(len(data.weather), 16)
        self.assertEqual(len(data.reference_labels), 100)
        self.assertAlmostEqual(data.station_generation[0], data.generation[:, 0].sum())


if __name__ == "__main__":
    unittest.main()
