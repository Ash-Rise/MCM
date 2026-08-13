from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


GENERATED_NOTICE = (
    "<!-- 由 src/generate_github_preview.py 根据同目录 Pandoc 源文件自动生成；请勿手工修改。 -->\n\n"
    "> 本文件用于 GitHub 在线预览；Word 转换请使用同目录的 Pandoc Markdown 源文件。\n\n"
)

# GitHub does not recognize a plain $...$ span when either delimiter directly
# touches CJK text.  Its documented $`...`$ form is unambiguous without adding
# visible spaces.  Display math ($$...$$) is deliberately excluded.
INLINE_MATH_RE = re.compile(
    r"(?<![\\$])\$(?![`$])(?P<math>[^\n$]+?)(?<![\\`$])\$(?!\$)"
)
IMAGE_WIDTH_RE = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)]+)\)"
    r"\{width=(?P<width>\d+(?:\.\d+)?)%\}"
)
FENCED_BLOCK_RE = re.compile(
    r"(^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n.*?"
    r"^[ \t]*(?P=fence)[ \t]*(?:\n|$))",
    flags=re.MULTILINE | re.DOTALL,
)


def _convert_prose(segment: str) -> str:
    def replace_image(match: re.Match[str]) -> str:
        src = html.escape(match.group("src"), quote=True)
        alt = html.escape(match.group("alt"), quote=True)
        width = match.group("width")
        return (
            '<p align="center">\n'
            f'  <img src="{src}" width="{width}%" alt="{alt}">\n'
            "</p>"
        )

    segment = IMAGE_WIDTH_RE.sub(replace_image, segment)
    return INLINE_MATH_RE.sub(lambda match: f"$`{match.group('math')}`$", segment)


def convert_for_github(source: str) -> str:
    parts: list[str] = []
    cursor = 0
    for fenced_block in FENCED_BLOCK_RE.finditer(source):
        parts.append(_convert_prose(source[cursor : fenced_block.start()]))
        parts.append(fenced_block.group(0))
        cursor = fenced_block.end()
    parts.append(_convert_prose(source[cursor:]))
    return GENERATED_NOTICE + "".join(parts)


def write_preview(source_path: Path, output_path: Path, *, check: bool = False) -> bool:
    rendered = convert_for_github(source_path.read_text(encoding="utf-8"))
    if check:
        return output_path.exists() and output_path.read_text(encoding="utf-8") == rendered
    output_path.write_text(rendered, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a GitHub-friendly preview from the Pandoc paper source."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit nonzero when the committed preview is stale.",
    )
    args = parser.parse_args()

    if not write_preview(args.source, args.output, check=args.check):
        print(f"stale GitHub preview: {args.output}")
        return 1
    print(f"GitHub preview {'matches' if args.check else 'written'}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
