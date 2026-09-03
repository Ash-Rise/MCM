"""Apply project-specific layout to the Pandoc-generated CUMCM paper DOCX."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.oxml import parse_xml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "shared"))

import paper_format as shared_format  # noqa: E402


TABLE_WIDTH_WEIGHTS = (
    (0.14, 0.14, 0.72),
    (0.18, 0.62, 0.20),
    (0.42, 0.58),
    (0.07, 0.16, 0.17, 0.40, 0.20),
    (0.07, 0.15, 0.17, 0.40, 0.21),
    (0.12, 0.20, 0.18, 0.16, 0.34),
    (0.13, 0.18, 0.44, 0.25),
    (0.08, 0.72, 0.20),
    (0.10, 0.62, 0.28),
)

COMPACT_TABLE_INDICES = {3, 4, 6}

# Each tuple is (table index, column index, semantic child kind).  Pandoc keeps
# adjacent display-math objects and text runs as separate OOXML children but
# drops Markdown <br> tags inside table cells, so the formatter must restore
# the intended line boundaries without converting native equations to text.
COMPACT_CELL_BREAKS = (
    (3, 1, "mixed"),
    (3, 2, "math"),
    (3, 3, "math"),
    (3, 4, "text"),
    (4, 1, "mixed"),
    (4, 2, "math"),
    (4, 3, "math"),
    (4, 4, "text"),
    (6, 1, "math"),
    (6, 2, "math"),
    (6, 3, "text"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_child_before(parent, tag: str, *successors: str):
    child = parent.find(qn(tag))
    if child is None:
        child = OxmlElement(tag)
        parent.insert_element_before(child, *successors)
    return child


def _set_width(parent, tag: str, width_dxa: int) -> None:
    width = _ensure_child_before(
        parent,
        tag,
        "w:tblLayout",
        "w:tblCellMar",
        "w:tblLook",
        "w:tblCaption",
        "w:tblDescription",
        "w:tblPrChange",
    )
    width.set(qn("w:type"), "dxa")
    width.set(qn("w:w"), str(width_dxa))


def _set_cell_width(properties, width_dxa: int) -> None:
    width = properties.find(qn("w:tcW"))
    if width is None:
        width = OxmlElement("w:tcW")
        properties.insert_element_before(
            width,
            "w:gridSpan",
            "w:hMerge",
            "w:vMerge",
            "w:tcBorders",
            "w:shd",
            "w:noWrap",
            "w:tcMar",
            "w:textDirection",
            "w:tcFitText",
            "w:vAlign",
            "w:hideMark",
            "w:headers",
            "w:cellIns",
            "w:cellDel",
            "w:cellMerge",
            "w:tcPrChange",
        )
    width.set(qn("w:type"), "dxa")
    width.set(qn("w:w"), str(width_dxa))


def _set_table_geometry(table, weights: tuple[float, ...], width_dxa: int) -> None:
    if len(table.columns) != len(weights):
        raise ValueError(f"Expected {len(weights)} columns, found {len(table.columns)}")
    widths = [round(width_dxa * weight / sum(weights)) for weight in weights]
    widths[-1] += width_dxa - sum(widths)

    table.autofit = False
    properties = table._tbl.tblPr
    _set_width(properties, "w:tblW", width_dxa)
    layout = _ensure_child_before(
        properties,
        "w:tblLayout",
        "w:tblCellMar",
        "w:tblLook",
        "w:tblCaption",
        "w:tblDescription",
        "w:tblPrChange",
    )
    layout.set(qn("w:type"), "fixed")
    indent = _ensure_child_before(
        properties,
        "w:tblInd",
        "w:tblBorders",
        "w:shd",
        "w:tblLayout",
        "w:tblCellMar",
        "w:tblLook",
        "w:tblCaption",
        "w:tblDescription",
        "w:tblPrChange",
    )
    indent.set(qn("w:type"), "dxa")
    indent.set(qn("w:w"), "0")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        column = OxmlElement("w:gridCol")
        column.set(qn("w:w"), str(width))
        grid.append(column)

    for row in table.rows:
        for index, cell in enumerate(row.cells):
            _set_cell_width(cell._tc.get_or_add_tcPr(), widths[index])


def _set_table_font_size(table, half_points: int) -> None:
    for run in table._tbl.findall(".//" + qn("w:r")):
        properties = run.find(qn("w:rPr"))
        if properties is None:
            properties = OxmlElement("w:rPr")
            run.insert(0, properties)
        for tag in ("w:sz", "w:szCs"):
            size = properties.find(qn(tag))
            if size is None:
                size = OxmlElement(tag)
                properties.append(size)
            size.set(qn("w:val"), str(half_points))
    for math_run in table._tbl.findall(".//" + qn("m:r")):
        properties = math_run.find(qn("w:rPr"))
        if properties is None:
            properties = OxmlElement("w:rPr")
            math_run.insert(0, properties)
        for tag in ("w:sz", "w:szCs"):
            size = properties.find(qn(tag))
            if size is None:
                size = OxmlElement(tag)
                properties.append(size)
            size.set(qn("w:val"), str(half_points))


def _set_table_cell_margins(table, horizontal_dxa: int = 45) -> None:
    properties = table._tbl.tblPr
    margins = properties.find(qn("w:tblCellMar"))
    if margins is None:
        margins = OxmlElement("w:tblCellMar")
        properties.insert_element_before(
            margins,
            "w:tblLook",
            "w:tblCaption",
            "w:tblDescription",
            "w:tblPrChange",
        )
    for tag, width in (
        ("w:top", 0),
        ("w:left", horizontal_dxa),
        ("w:bottom", 0),
        ("w:right", horizontal_dxa),
    ):
        margin = margins.find(qn(tag))
        if margin is None:
            margin = OxmlElement(tag)
            margins.append(margin)
        margin.set(qn("w:type"), "dxa")
        margin.set(qn("w:w"), str(width))


def _insert_line_break_before(element) -> None:
    run = OxmlElement("w:r")
    run.append(OxmlElement("w:br"))
    element.addprevious(run)


def _restore_compact_table_line_breaks(document) -> None:
    """Restore semantic line breaks that Pandoc drops inside Markdown tables."""
    for table_index, column_index, child_kind in COMPACT_CELL_BREAKS:
        table = document.tables[table_index]
        for row in table.rows[1:]:
            paragraph = row.cells[column_index].paragraphs[0]
            if child_kind == "math":
                children = list(paragraph._p.findall(qn("m:oMath")))
                break_targets = children[1:]
            elif child_kind == "text":
                children = [
                    child
                    for child in paragraph._p.findall(qn("w:r"))
                    if child.find(qn("w:t")) is not None
                ]
                break_targets = children[1:]
            else:
                math_children = list(paragraph._p.findall(qn("m:oMath")))
                text_children = [
                    child
                    for child in paragraph._p.findall(qn("w:r"))
                    if child.find(qn("w:t")) is not None
                ]
                if len(math_children) != 1 or not text_children:
                    raise ValueError(
                        f"Unexpected mixed cell structure in table {table_index + 1}, "
                        f"column {column_index + 1}"
                    )
                break_targets = text_children[:1]

            if not break_targets:
                raise ValueError(
                    f"No line-break targets in table {table_index + 1}, "
                    f"column {column_index + 1}"
                )
            for target in break_targets:
                _insert_line_break_before(target)


def _remove_title_rule(document) -> None:
    title = document.paragraphs[0]
    for properties in (title._p.get_or_add_pPr(), document.styles["Title"].element.get_or_add_pPr()):
        borders = properties.find(qn("w:pBdr"))
        if borders is not None:
            properties.remove(borders)


def _fit_title_to_baseline_width(document) -> None:
    """Keep this all-CJK title on one line without changing the profile font size."""
    for run in document.paragraphs[0].runs:
        properties = run._r.get_or_add_rPr()
        scale = properties.find(qn("w:w"))
        if scale is None:
            scale = OxmlElement("w:w")
            properties.append(scale)
        scale.set(qn("w:val"), "94")


def _footnote_text_by_id(document) -> dict[str, str]:
    part = next(
        (
            related
            for related in document.part.related_parts.values()
            if str(related.partname) == "/word/footnotes.xml"
        ),
        None,
    )
    if part is None:
        return {}
    root = parse_xml(part.blob)
    return {
        footnote.get(qn("w:id")): "".join(
            node.text or "" for node in footnote.findall(".//" + qn("w:t"))
        )
        for footnote in root.findall(qn("w:footnote"))
    }


def _restore_superscript_citations(document) -> None:
    citation_text = _footnote_text_by_id(document)
    replaced = 0
    for paragraph in document.paragraphs:
        for run in list(paragraph._p.findall(qn("w:r"))):
            reference = run.find(qn("w:footnoteReference"))
            if reference is None:
                continue
            footnote_id = reference.get(qn("w:id"))
            number = citation_text.get(footnote_id, "").strip()
            if not re.fullmatch(r"\d+", number):
                raise ValueError(f"Unexpected inline footnote {footnote_id}: {number!r}")
            text = OxmlElement("w:t")
            text.text = f"[{number}]"
            run.remove(reference)
            run.append(text)
            properties = run.get_or_add_rPr()
            style = properties.find(qn("w:rStyle"))
            if style is not None:
                properties.remove(style)
            vertical = properties.find(qn("w:vertAlign"))
            if vertical is None:
                vertical = OxmlElement("w:vertAlign")
                properties.append(vertical)
            vertical.set(qn("w:val"), "superscript")

            following = run.getnext()
            if following is None or following.tag != qn("w:r"):
                raise ValueError("Citation footnote is not followed by the Markdown caret")
            following_text = following.find(qn("w:t"))
            if following_text is None or not (following_text.text or "").startswith("^"):
                raise ValueError("Citation footnote is not followed by the Markdown caret")
            following_text.text = (following_text.text or "")[1:]
            if not following_text.text:
                paragraph._p.remove(following)
            replaced += 1
    if replaced != 3:
        raise ValueError(f"Expected 3 citation markers, restored {replaced}")


def _set_keep_rules(document) -> None:
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style else ""
        if style_name.startswith("Heading"):
            paragraph.paragraph_format.keep_with_next = True
            paragraph.paragraph_format.keep_together = True
        elif re.match(r"^表\s*\d+\s", text):
            paragraph.paragraph_format.keep_with_next = True
            paragraph.paragraph_format.keep_together = True
        elif re.match(r"^图\s*\d+\s", text):
            paragraph.paragraph_format.keep_together = True
        elif paragraph._p.findall(".//" + qn("m:oMath")):
            paragraph.paragraph_format.keep_together = True


def _set_figure_alt_text(document) -> None:
    paragraphs = document.paragraphs
    for index, paragraph in enumerate(paragraphs):
        properties = paragraph._p.findall(".//" + qn("wp:docPr"))
        if not properties:
            continue
        caption = next(
            (
                candidate.text.strip()
                for candidate in paragraphs[index + 1 :]
                if candidate.text.strip()
            ),
            "",
        )
        if not caption.startswith("图"):
            raise ValueError(f"Figure at paragraph {index} is not followed by a caption")
        for item in properties:
            item.set("descr", caption)
            item.set("title", caption.split(maxsplit=1)[0])


def _request_field_update(document) -> None:
    settings = document.settings._element
    update = settings.find(qn("w:updateFields"))
    if update is None:
        update = OxmlElement("w:updateFields")
        settings.append(update)
    update.set(qn("w:val"), "true")


def apply_layout(document) -> None:
    _restore_superscript_citations(document)
    _restore_compact_table_line_breaks(document)
    shared_format.apply_profile(document)
    _remove_title_rule(document)
    _fit_title_to_baseline_width(document)

    profile = shared_format.load_profile()
    page = profile["page"]
    content_width = (
        page["width_twips"]
        - page["margins_twips"]["left"]
        - page["margins_twips"]["right"]
    )
    if len(document.tables) != len(TABLE_WIDTH_WEIGHTS):
        raise ValueError(
            f"Expected {len(TABLE_WIDTH_WEIGHTS)} tables, found {len(document.tables)}"
        )
    for index, (table, weights) in enumerate(
        zip(document.tables, TABLE_WIDTH_WEIGHTS, strict=True)
    ):
        _set_table_geometry(table, weights, content_width)
        if index in COMPACT_TABLE_INDICES:
            _set_table_font_size(table, 18)
            _set_table_cell_margins(table)

    _set_keep_rules(document)
    _set_figure_alt_text(document)
    _request_field_update(document)

    layout_errors = shared_format.validate_docx_layout(document)
    if layout_errors:
        raise ValueError("DOCX layout validation failed: " + "; ".join(layout_errors))

    title = document.paragraphs[0].text.strip()
    document.core_properties.title = title
    document.core_properties.subject = "2025 CUMCM A 题数学建模论文"
    document.core_properties.author = ""
    document.core_properties.last_modified_by = ""
    document.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER


def _update_manifest(manifest_path: Path, output_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output"] = str(output_path.resolve())
    manifest["output_sha256"] = _sha256(output_path)
    manifest.setdefault("postprocessing", []).append(
        {
            "tool": "scripts/format_paper_docx.py",
            "reason": (
                "Applied the repository formatting profile, portrait semantic table widths, "
                "pagination keep rules, layout invariants, figure alt text, and anonymous metadata."
            ),
        }
    )
    output_manifest = output_path.with_suffix(".conversion.json")
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    document = Document(args.input)
    apply_layout(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=args.output.parent, suffix=".docx", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        document.save(temporary_path)
        os.replace(temporary_path, args.output)
    finally:
        temporary_path.unlink(missing_ok=True)

    if args.manifest is not None:
        _update_manifest(args.manifest, args.output)


if __name__ == "__main__":
    main()
