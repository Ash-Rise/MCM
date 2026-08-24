"""Build the Problem B DOCX from paper.md without a machine-specific manifest."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document

from postprocess_paper_docx import apply_project_layout


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = PROJECT_ROOT / "paper"
SOURCE_PATH = PAPER_DIR / "paper.md"
DEFAULT_OUTPUT = PAPER_DIR / "paper.docx"


def repository_root() -> Path:
    for candidate in (PROJECT_ROOT, *PROJECT_ROOT.parents):
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError("Cannot locate repository root containing AGENTS.md")


def resolve_executable(command: str) -> str:
    resolved = shutil.which(command)
    if resolved is None:
        raise RuntimeError(
            f"Cannot find {command!r}; install Pandoc 3.x and add it to PATH, "
            "or pass --pandoc with an executable path"
        )
    return resolved


def build_document(*, pandoc: str, profile_path: Path, output: Path) -> None:
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(SOURCE_PATH)
    if not profile_path.is_file():
        raise FileNotFoundError(profile_path)

    shared_path = repository_root() / "shared"
    if str(shared_path) not in sys.path:
        sys.path.insert(0, str(shared_path))
    from paper_format import apply_profile, load_profile

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="problem-b-paper-", dir=output.parent) as temp_dir:
        temp_root = Path(temp_dir)
        raw_docx = temp_root / "pandoc.docx"
        formatted_docx = temp_root / "formatted.docx"
        command = [
            resolve_executable(pandoc),
            "--from=markdown",
            "--to=docx",
            "--standalone",
            "--fail-if-warnings",
            "--resource-path=.",
            SOURCE_PATH.name,
            "--output",
            str(raw_docx),
        ]
        completed = subprocess.run(
            command,
            cwd=PAPER_DIR,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Pandoc failed with exit code {completed.returncode}: {details}")

        document = Document(raw_docx)
        apply_profile(document, load_profile(profile_path))
        apply_project_layout(document)
        document.save(formatted_docx)
        os.replace(formatted_docx, output)


def main() -> None:
    default_profile = (
        repository_root() / "shared" / "templates" / "personal-paper-profile.yaml"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandoc", default="pandoc", help="Pandoc executable or command on PATH")
    parser.add_argument("--profile", type=Path, default=default_profile)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_document(pandoc=args.pandoc, profile_path=args.profile, output=args.output)
    print(f"wrote {args.output.resolve()}")


if __name__ == "__main__":
    main()
