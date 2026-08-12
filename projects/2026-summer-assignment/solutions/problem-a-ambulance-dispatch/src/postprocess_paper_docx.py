from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Twips


COMPLETE_TABLE_WIDTH_WEIGHTS = (
    (1.2, 4.4, 1.2),
    (1.0, 2.5, 3.5),
    (2.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
    (2.3, 4.7),
    (0.9, 0.9, 1.2, 1.5, 1.5, 1.5),
    (2.3, 4.7),
    (2.0, 1.9, 1.9, 1.9),
    (1.2, 1.7, 1.8, 3.1),
    (0.8, 1.0, 1.4, 1.8, 1.0),
    (1.8, 5.2),
    (0.8, 1.0, 1.0, 1.0, 2.0),
    (0.7, 1.0, 1.6, 1.0, 1.6),
)


def table_width_weights_for_count(table_count: int) -> tuple[tuple[float, ...], ...]:
    if table_count == len(COMPLETE_TABLE_WIDTH_WEIGHTS):
        return COMPLETE_TABLE_WIDTH_WEIGHTS
    raise ValueError(f"Expected 12 tables, found {table_count}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rebind_conversion_manifest(manifest_path: Path, output_path: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_path = Path(manifest["source"]) if manifest.get("source") else None
    if source_path is not None and source_path.exists():
        source_hash = sha256_file(source_path)
        manifest["source_sha256"] = source_hash
        manifest["project_sha256"] = source_hash
    manifest["output"] = str(output_path.resolve())
    manifest["output_sha256"] = sha256_file(output_path)
    manifest["postprocess"] = {
        "tool": "src/postprocess_paper_docx.py",
        "source_manifest": manifest_path.name,
        "reason": (
            "Removed template numbering, applied exact table geometry, installed "
            "centered PAGE fields, kept the abstract on its own page, and added "
            "caption-derived alt text to body figures. The current Markdown was "
            "synchronized with the reviewed Word baseline without changing results."
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
    # Some reference templates copy table borders into every row through
    # tblPrEx.  Those row-level exceptions override a clean table-level
    # three-line definition and render as a heavy rule after every row.
    for row in table.rows:
        for exception in list(row._tr.findall(qn("w:tblPrEx"))):
            row._tr.remove(exception)
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
            border.set(qn("w:sz"), "10")
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
        bottom.set(qn("w:sz"), "4")
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
    title = paragraph.text.replace("\n", "")
    paragraph.clear()
    run = paragraph.add_run(title)
    run.bold = True
    _set_run_font(run, east_asia="宋体", size=Pt(15))
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_after = Pt(3)


def _set_run_font(run, *, east_asia: str, size) -> None:
    run.font.name = "Times New Roman"
    run.font.size = size
    run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), east_asia)


def _merge_compound_math_scripts(document) -> int:
    """Keep compound OMML subscripts and superscripts horizontal in LibreOffice."""
    merged = 0
    for script_tag in ("m:sub", "m:sup"):
        for script in document.element.body.findall(".//" + qn(script_tag)):
            runs = list(script.findall(qn("m:r")))
            if len(runs) < 2:
                continue
            texts = [run.find(qn("m:t")) for run in runs]
            if any(text is None for text in texts):
                continue
            combined = "".join(text.text or "" for text in texts)
            if re.fullmatch(r"[A-Za-z0-9=(),*+\-]+", combined) is None:
                continue
            texts[0].text = combined
            for run in runs[1:]:
                script.remove(run)
            merged += 1
    return merged


ARRIVAL_RATE_TERM_REPLACEMENTS = (
    ("严格4 min响应率", "4分钟内到达率"),
    ("严格4 min率", "4分钟内到达率"),
    ("严格4分钟响应率", "4分钟内到达率"),
    ("严格4分钟率", "4分钟内到达率"),
    ("严格四分钟响应率", "4分钟内到达率"),
    ("严格四分钟率", "4分钟内到达率"),
)


def _replace_text_across_runs(paragraph_element, old: str, new: str) -> int:
    """Replace visible Word text without rebuilding runs or touching OMML."""
    replaced = 0
    while True:
        text_nodes = list(paragraph_element.findall(".//" + qn("w:t")))
        values = [node.text or "" for node in text_nodes]
        combined = "".join(values)
        start = combined.find(old)
        if start < 0:
            return replaced
        end = start + len(old)
        cursor = 0
        first_index = last_index = None
        first_offset = last_offset = 0
        for index, value in enumerate(values):
            next_cursor = cursor + len(value)
            if first_index is None and start < next_cursor:
                first_index = index
                first_offset = start - cursor
            if first_index is not None and end <= next_cursor:
                last_index = index
                last_offset = end - cursor
                break
            cursor = next_cursor
        if first_index is None or last_index is None:
            raise ValueError(f"Could not map replacement span for {old!r}")
        prefix = values[first_index][:first_offset]
        if first_index == last_index:
            suffix = values[first_index][last_offset:]
            text_nodes[first_index].text = prefix + new + suffix
        else:
            suffix = values[last_index][last_offset:]
            text_nodes[first_index].text = prefix + new
            for index in range(first_index + 1, last_index):
                text_nodes[index].text = ""
            text_nodes[last_index].text = suffix
        replaced += 1


def normalize_arrival_rate_terms(document) -> int:
    replaced = 0
    for paragraph in document.element.body.findall(".//" + qn("w:p")):
        for old, new in ARRIVAL_RATE_TERM_REPLACEMENTS:
            replaced += _replace_text_across_runs(paragraph, old, new)
    return replaced


def replace_body_figure_by_caption(document, caption_prefix: str, image_path: Path) -> None:
    paragraphs = document.paragraphs
    caption_index = next(
        (
            index
            for index, paragraph in enumerate(paragraphs)
            if paragraph.text.strip().startswith(caption_prefix)
        ),
        None,
    )
    if caption_index is None:
        raise ValueError(f"Could not find caption {caption_prefix!r}")
    for paragraph in reversed(paragraphs[:caption_index]):
        blip = paragraph._p.find(".//" + qn("a:blip"))
        if blip is None:
            continue
        relationship_id = blip.get(qn("r:embed"))
        document.part.rels[relationship_id].target_part._blob = image_path.read_bytes()
        return
    raise ValueError(f"Could not find image preceding caption {caption_prefix!r}")


def _disable_paragraph_grid(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    snap_to_grid = p_pr.find(qn("w:snapToGrid"))
    if snap_to_grid is not None:
        p_pr.remove(snap_to_grid)
    snap_to_grid = OxmlElement("w:snapToGrid")
    p_pr.insert_element_before(
        snap_to_grid,
        "w:spacing",
        "w:ind",
        "w:contextualSpacing",
        "w:mirrorIndents",
        "w:suppressOverlap",
        "w:jc",
        "w:textDirection",
        "w:textAlignment",
        "w:textboxTightWrap",
        "w:outlineLvl",
        "w:divId",
        "w:cnfStyle",
        "w:rPr",
        "w:sectPr",
        "w:pPrChange",
    )
    snap_to_grid.set(qn("w:val"), "0")


def _set_reference_body_spacing(paragraph, multiple: float = 1.5) -> None:
    paragraph.paragraph_format.line_spacing = multiple


def _set_document_line_grid(document, line_pitch: int = 360) -> None:
    """Match the reference document's 1.5-line page grid."""
    for section in document.sections:
        section_properties = section._sectPr
        document_grid = _ensure_child(section_properties, "w:docGrid")
        document_grid.set(qn("w:type"), "lines")
        document_grid.set(qn("w:linePitch"), str(line_pitch))
        document_grid.set(qn("w:charSpace"), "0")


def _is_figure_or_table_caption(text: str) -> bool:
    return re.match(r"^[图表]\s*\d+\s+\S", text) is not None


def _format_document_typography(document) -> None:
    body_style = document.styles["Body Text"]
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style is not None else ""
        if style_name == "Title":
            continue

        if style_name in {"Heading 1", "Heading 2"}:
            _disable_paragraph_grid(paragraph)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            paragraph.paragraph_format.space_before = Pt(2.5)
            paragraph.paragraph_format.space_after = Pt(2.5)
            for run in paragraph.runs:
                _set_run_font(run, east_asia="黑体", size=Pt(14))
                run.bold = True
            continue

        if style_name == "Heading 3":
            _disable_paragraph_grid(paragraph)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            paragraph.paragraph_format.space_before = Pt(2.5)
            paragraph.paragraph_format.space_after = Pt(2.5)
            for run in paragraph.runs:
                _set_run_font(run, east_asia="宋体", size=Pt(12))
                run.bold = True
            continue

        # Pandoc may emit dangling FirstParagraph/Compact style references.
        # Normalize all non-heading content so renderers cannot inherit different line grids.
        paragraph.style = body_style

        if _is_figure_or_table_caption(text):
            _disable_paragraph_grid(paragraph)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Pt(0)
            _set_reference_body_spacing(paragraph)
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.keep_with_next = True
            for run in paragraph.runs:
                _set_run_font(run, east_asia="宋体", size=Pt(10.5))
            continue

        if re.match(r"^\[\d+\]", text):
            _disable_paragraph_grid(paragraph)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.left_indent = Pt(21)
            paragraph.paragraph_format.first_line_indent = Pt(-21)
            _set_reference_body_spacing(paragraph, 1.25)
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            for run in paragraph.runs:
                _set_run_font(run, east_asia="宋体", size=Pt(10.5))
            continue

        if text.startswith("三问结果文件分别位于"):
            _disable_paragraph_grid(paragraph)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            paragraph.paragraph_format.first_line_indent = Pt(21)
            _set_reference_body_spacing(paragraph, 1.25)
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            for run in paragraph.runs:
                _set_run_font(run, east_asia="宋体", size=Pt(10.5))
            continue

        if paragraph._p.findall(".//" + qn("w:drawing")):
            _disable_paragraph_grid(paragraph)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            continue

        if not text:
            if paragraph._p.findall(".//" + qn("m:oMath")):
                _disable_paragraph_grid(paragraph)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.first_line_indent = Pt(0)
                _set_reference_body_spacing(paragraph)
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
            continue

        _disable_paragraph_grid(paragraph)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _set_reference_body_spacing(paragraph)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        p_pr = paragraph._p.pPr
        is_list = p_pr is not None and p_pr.numPr is not None
        paragraph.paragraph_format.first_line_indent = None if is_list else Pt(24)
        if text.startswith("关键词"):
            paragraph.paragraph_format.first_line_indent = Pt(0)
        for run in paragraph.runs:
            _set_run_font(run, east_asia="宋体", size=Pt(12))

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _disable_paragraph_grid(paragraph)
                    _set_reference_body_spacing(paragraph, 1.15)
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)
                    for run in paragraph.runs:
                        _set_run_font(run, east_asia="宋体", size=Pt(10.5))


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
        if re.match(r"^(?:1\s+|一、)问题重述", paragraph.text.strip()):
            paragraph.paragraph_format.page_break_before = True
            return
    raise ValueError("Could not find the first body heading for 问题重述")


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
    _merge_compound_math_scripts(document)
    _set_document_line_grid(document)
    _format_document_typography(document)
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
    for table_index, (table, weights) in enumerate(
        zip(document.tables, table_width_weights, strict=True)
    ):
        current_table_width = content_width if table_index == 6 else table_width
        _set_table_geometry(table, weights, current_table_width)
        _set_table_borders(table)
        for row_index, row in enumerate(table.rows):
            for column_index, cell in enumerate(row.cells):
                if table_index == 6:
                    _set_cell_margins(cell, top=60, bottom=60, side=35)
                    _ensure_child_before(
                        cell._tc.get_or_add_tcPr(),
                        "w:noWrap",
                        "w:tcMar",
                        "w:textDirection",
                        "w:tcFitText",
                        "w:vAlign",
                    )
                for paragraph in cell.paragraphs:
                    p_style = paragraph._p.pPr.find(qn("w:pStyle"))
                    if p_style is not None:
                        paragraph._p.pPr.remove(p_style)
                    paragraph.paragraph_format.space_before = Pt(0)
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.paragraph_format.line_spacing = 1.15
                    if row_index == 0:
                        paragraph.paragraph_format.keep_with_next = True
                    contains_math = bool(
                        paragraph._p.findall(".//" + qn("m:oMath"))
                    )
                    is_algorithm_table = table_index in {3, 5, 9}
                    if (
                        row_index != 0
                        and (
                            (is_algorithm_table and column_index in {0, 1})
                            or (table_index == 0 and column_index == 1)
                        )
                    ):
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    else:
                        paragraph.alignment = (
                            WD_ALIGN_PARAGRAPH.CENTER
                            if (
                                table_index == 6
                                or row_index == 0
                                or column_index != 1
                                or contains_math
                            )
                            else WD_ALIGN_PARAGRAPH.LEFT
                        )
                    for run in paragraph.runs:
                        _set_run_font(run, east_asia="宋体", size=Pt(10))
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
