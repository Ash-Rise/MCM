from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Twips


COMPLETE_TABLE_WIDTH_WEIGHTS = (
    (1.2, 4.4, 1.2),
    (0.9, 0.9, 1.2, 1.5, 1.5, 1.5),
    (1.0, 1.0, 1.0),
    (2.6, 1.4, 1.4, 1.4),
    (1.2, 1.7, 1.8, 3.1),
    (0.8, 1.0, 1.4, 1.8, 1.0),
    (0.8, 1.0, 1.0, 1.0, 2.0),
    (0.7, 1.0, 1.6, 1.0, 1.6),
)


def table_width_weights_for_count(table_count: int) -> tuple[tuple[float, ...], ...]:
    if table_count == len(COMPLETE_TABLE_WIDTH_WEIGHTS):
        return COMPLETE_TABLE_WIDTH_WEIGHTS
    raise ValueError(f"Expected 8 tables, found {table_count}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rebind_conversion_manifest(manifest_path: Path, output_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output"] = str(output_path.resolve())
    manifest["output_sha256"] = sha256_file(output_path)
    manifest["postprocess"] = {
        "tool": "src/postprocess_paper_docx.py",
        "source_manifest": manifest_path.name,
        "reason": (
            "Removed template numbering, applied exact table geometry, installed "
            "centered PAGE fields, kept the abstract on its own page, and added "
            "caption-derived alt text to body figures without changing paper content."
        ),
    }
    output_manifest = output_path.with_suffix(".conversion.json")
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_manifest


def _ensure_child(parent, tag: str):
    child = parent.find(qn(tag))
    if child is None:
        child = OxmlElement(tag)
        parent.append(child)
    return child


def _ensure_child_before(parent, tag: str, *successors: str):
    child = parent.find(qn(tag))
    if child is None:
        child = OxmlElement(tag)
        parent.insert_element_before(child, *successors)
    return child


def _set_width(parent, tag: str, width_dxa: int) -> None:
    width = _ensure_child(parent, tag)
    width.set(qn("w:type"), "dxa")
    width.set(qn("w:w"), str(width_dxa))


def _column_widths(weights: tuple[float, ...], total_width: int) -> list[int]:
    widths = [round(total_width * weight / sum(weights)) for weight in weights]
    widths[-1] += total_width - sum(widths)
    return widths


def _set_cell_margins(cell, *, top: int = 80, bottom: int = 80, side: int = 100) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = _ensure_child_before(
        tc_pr,
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
    for name, value in (("top", top), ("left", side), ("bottom", bottom), ("right", side)):
        margin = _ensure_child(tc_mar, f"w:{name}")
        margin.set(qn("w:type"), "dxa")
        margin.set(qn("w:w"), str(value))


def _set_table_geometry(table, weights: tuple[float, ...], total_width: int) -> None:
    widths = _column_widths(weights, total_width)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_pr = table._tbl.tblPr
    table_style = tbl_pr.find(qn("w:tblStyle"))
    if table_style is not None:
        tbl_pr.remove(table_style)
    _set_width(tbl_pr, "w:tblW", total_width)
    layout = _ensure_child_before(
        tbl_pr,
        "w:tblLayout",
        "w:tblCellMar",
        "w:tblLook",
        "w:tblCaption",
        "w:tblDescription",
        "w:tblPrChange",
    )
    layout.set(qn("w:type"), "fixed")
    indent = _ensure_child_before(
        tbl_pr,
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
    indent.set(qn("w:w"), "120")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        column = OxmlElement("w:gridCol")
        column.set(qn("w:w"), str(width))
        grid.append(column)

    for column_index, width in enumerate(widths):
        table.columns[column_index].width = Twips(width)
    for row in table.rows:
        row.height = None
        for column_index, cell in enumerate(row.cells):
            cell.width = Twips(widths[column_index])
            _set_width(cell._tc.get_or_add_tcPr(), "w:tcW", widths[column_index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _set_table_borders(table) -> None:
    borders = _ensure_child_before(
        table._tbl.tblPr,
        "w:tblBorders",
        "w:shd",
        "w:tblLayout",
        "w:tblCellMar",
        "w:tblLook",
        "w:tblCaption",
        "w:tblDescription",
        "w:tblPrChange",
    )
    for child in list(borders):
        borders.remove(child)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = _ensure_child(borders, f"w:{edge}")
        if edge in ("top", "bottom"):
            border.set(qn("w:val"), "single")
            border.set(qn("w:sz"), "12")
            border.set(qn("w:color"), "000000")
        else:
            border.set(qn("w:val"), "nil")

    header_borders = _ensure_child(table.rows[0]._tr.get_or_add_trPr(), "w:tblHeader")
    header_borders.set(qn("w:val"), "true")
    for cell in table.rows[0].cells:
        tc_borders = _ensure_child_before(
            cell._tc.get_or_add_tcPr(),
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
        bottom = _ensure_child(tc_borders, "w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:color"), "000000")


def _remove_style_numbering(style) -> None:
    p_pr = style.element.get_or_add_pPr()
    num_pr = p_pr.get_or_add_numPr()
    num_id = num_pr.get_or_add_numId()
    num_id.val = 0


def _format_title(document) -> None:
    paragraph = document.paragraphs[0]
    try:
        title_style = document.styles["Title"]
    except KeyError:
        title_style = document.styles.add_style("Title", WD_STYLE_TYPE.PARAGRAPH)
    paragraph.style = title_style
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title = paragraph.text.replace("仿真的急救", "仿真的\n急救")
    paragraph.clear()
    run = paragraph.add_run(title)
    run.bold = True
    run.font.size = Pt(22)
    paragraph.paragraph_format.space_after = Pt(18)


def _set_body_image_alt_text(document) -> int:
    paragraphs = document.paragraphs
    updated = 0
    for index, paragraph in enumerate(paragraphs):
        drawing_properties = paragraph._p.findall(".//" + qn("wp:docPr"))
        if not drawing_properties:
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
            continue
        for properties in drawing_properties:
            properties.set("descr", caption)
            properties.set("title", caption.split(maxsplit=1)[0])
            updated += 1
    return updated


def _keep_abstract_on_first_page(document) -> None:
    for paragraph in document.paragraphs:
        if paragraph.text.strip().startswith("1 问题重述"):
            paragraph.paragraph_format.page_break_before = True
            return
    raise ValueError("Could not find the first body heading '1 问题重述'")


def _set_page_field(footer) -> None:
    element = footer._element
    for child in list(element):
        element.remove(child)
    paragraph = OxmlElement("w:p")
    p_pr = OxmlElement("w:pPr")
    alignment = OxmlElement("w:jc")
    alignment.set(qn("w:val"), "center")
    p_pr.append(alignment)
    paragraph.append(p_pr)
    for field_type, text in (("begin", None), (None, " PAGE "), ("separate", None)):
        run = OxmlElement("w:r")
        if field_type is not None:
            field_char = OxmlElement("w:fldChar")
            field_char.set(qn("w:fldCharType"), field_type)
            run.append(field_char)
        else:
            instruction = OxmlElement("w:instrText")
            instruction.set(qn("xml:space"), "preserve")
            instruction.text = text
            run.append(instruction)
        paragraph.append(run)
    value_run = OxmlElement("w:r")
    value = OxmlElement("w:t")
    value.text = "1"
    value_run.append(value)
    paragraph.append(value_run)
    end_run = OxmlElement("w:r")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run.append(end)
    paragraph.append(end_run)
    element.append(paragraph)


def postprocess_docx(input_path: Path, output_path: Path) -> None:
    document = Document(input_path)
    _format_title(document)
    _set_body_image_alt_text(document)
    _keep_abstract_on_first_page(document)
    _remove_style_numbering(document.styles["Heading 1"])
    _remove_style_numbering(document.styles["Heading 2"])
    _remove_style_numbering(document.styles["Heading 3"])
    for section in document.sections:
        _set_page_field(section.footer)
        _set_page_field(section.first_page_footer)

    table_width_weights = table_width_weights_for_count(len(document.tables))
    section = document.sections[0]
    content_width = int(
        round(
            (
                section.page_width
                - section.left_margin
                - section.right_margin
            )
            / 635
        )
    )
    table_width = content_width - 200
    for table, weights in zip(document.tables, table_width_weights, strict=True):
        _set_table_geometry(table, weights, table_width)
        _set_table_borders(table)
        for row_index, row in enumerate(table.rows):
            for column_index, cell in enumerate(row.cells):
                for paragraph in cell.paragraphs:
                    p_style = paragraph._p.pPr.find(qn("w:pStyle"))
                    if p_style is not None:
                        paragraph._p.pPr.remove(p_style)
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.paragraph_format.line_spacing = 1.0
                    paragraph.alignment = (
                        WD_ALIGN_PARAGRAPH.CENTER
                        if row_index == 0 or column_index != 1
                        else WD_ALIGN_PARAGRAPH.LEFT
                    )
                    for run in paragraph.runs:
                        run.font.size = Pt(9)
                        if row_index == 0:
                            run.bold = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Postprocess the complete paper DOCX")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    postprocess_docx(args.input, args.output)
    if args.manifest is not None:
        rebind_conversion_manifest(args.manifest, args.output)


if __name__ == "__main__":
    main()
