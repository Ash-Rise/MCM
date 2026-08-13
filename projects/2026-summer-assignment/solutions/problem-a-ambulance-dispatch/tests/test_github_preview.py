import importlib.util
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "paper" / "v2.5" / "A题论文(v2.5).md"
PREVIEW_PATH = PROJECT_ROOT / "paper" / "v2.5" / "A题论文(v2.5)-GitHub预览.md"
GENERATOR_PATH = PROJECT_ROOT / "src" / "generate_github_preview.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_github_preview", GENERATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_github_preview_is_reproducible_from_pandoc_source():
    module = _load_generator()
    source = SOURCE_PATH.read_text(encoding="utf-8")
    preview = PREVIEW_PATH.read_text(encoding="utf-8")

    assert preview == module.convert_for_github(source)
    assert preview.startswith(module.GENERATED_NOTICE)


def test_github_preview_uses_gfm_math_and_html_image_widths():
    module = _load_generator()
    source = SOURCE_PATH.read_text(encoding="utf-8")
    preview = module.convert_for_github(source)

    source_inline_count = len(module.INLINE_MATH_RE.findall(source))
    assert source_inline_count > 50
    assert preview.count("$`") == source_inline_count
    prose_without_fences = module.FENCED_BLOCK_RE.sub(
        "", preview.removeprefix(module.GENERATED_NOTICE)
    )
    prose_without_math = re.sub(
        r"\$`[^`\n]+`\$", "", prose_without_fences
    )
    prose_without_math = re.sub(
        r"\$\$.*?\$\$", "", prose_without_math, flags=re.DOTALL
    )
    assert "$" not in prose_without_math
    assert "{width=" not in preview
    source_image_count = len(module.IMAGE_WIDTH_RE.findall(source))
    preview_image_count = len(
        re.findall(r'<img src="[^"]+" width="\d+(?:\.\d+)?%"', preview)
    )
    assert source_image_count > 0
    assert preview_image_count == source_image_count
    assert preview.count("$$") == source.count("$$")


def test_github_preview_converts_pandoc_citation_superscripts():
    module = _load_generator()
    source = SOURCE_PATH.read_text(encoding="utf-8")
    preview = module.convert_for_github(source)

    assert len(module.PANDOC_SUPERSCRIPT_CITATION_RE.findall(source)) == 4
    assert not module.PANDOC_SUPERSCRIPT_CITATION_RE.search(preview)
    assert [int(number) for number in re.findall(r"<sup>\[(\d+)\]</sup>", preview)] == [
        2,
        1,
        3,
        4,
    ]


def test_converter_does_not_change_fenced_code_blocks():
    module = _load_generator()
    source = "正文$x_i$且引用^\\[1\\]^。\n\n```text\n原样$x_i$ ^\\[1\\]^ {width=82%}\n```\n"
    preview = module.convert_for_github(source)

    assert "正文$`x_i`$且引用<sup>[1]</sup>。" in preview
    assert "原样$x_i$ ^\\[1\\]^ {width=82%}" in preview
