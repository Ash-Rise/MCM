"""Regression checks for the final Problem C DOCX resource contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from zipfile import ZipFile

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "shared"))

from paper_format import load_profile, validate_docx_resources  # noqa: E402


DOCX_PATH = PROJECT_ROOT / "paper.docx"


class ProblemCPaperDocxFormatTests(unittest.TestCase):
    def test_docx_has_profile_owned_theme_styles_and_font_table(self) -> None:
        document = Document(DOCX_PATH)
        self.assertEqual(validate_docx_resources(document, load_profile()), [])
        with ZipFile(DOCX_PATH) as archive:
            self.assertNotIn(b"Aptos", archive.read("word/theme/theme1.xml"))
            self.assertNotIn(b"Aptos", archive.read("word/fontTable.xml"))


if __name__ == "__main__":
    unittest.main()
