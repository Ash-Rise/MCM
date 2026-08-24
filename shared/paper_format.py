"""Apply the repository-wide paper formatting profile to a DOCX document."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


PROFILE_PATH = Path(__file__).resolve().parent / "templates" / "personal-paper-profile.yaml"
_ALIGNMENTS = {
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
}


def load_profile(path: Path = PROFILE_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        profile = yaml.safe_load(stream)
    if not isinstance(profile, dict):
        raise ValueError(f"Paper profile must be a mapping: {path}")
    return profile


def _remove_numbering(element) -> None:
    properties = element.get_or_add_pPr()
    numbering = properties.find(qn("w:numPr"))
    if numbering is not None:
        properties.remove(numbering)


def _set_run_format(run, typography: dict[str, Any], *, bold: bool | None = None) -> None:
    latin_font = typography["latin_font"]
    run.font.name = latin_font
    run.font.size = Pt(typography["size_pt"])
    run.font.color.rgb = RGBColor.from_string(typography["font_color_hex"])
    if bold is None:
        bold = typography.get("bold")
    if bold is not None:
        run.bold = bool(bold)
    fonts = run._r.get_or_add_rPr().get_or_add_rFonts()
    fonts.set(qn("w:ascii"), latin_font)
    fonts.set(qn("w:hAnsi"), latin_font)
    fonts.set(qn("w:eastAsia"), typography["east_asia_font"])


def _apply_paragraph_format(paragraph, typography: dict[str, Any]) -> None:
    paragraph.alignment = _ALIGNMENTS[typography["alignment"]]
    paragraph.paragraph_format.line_spacing = typography["line_spacing_multiple"]
    paragraph.paragraph_format.space_before = Pt(typography.get("space_before_pt", 0))
    paragraph.paragraph_format.space_after = Pt(typography.get("space_after_pt", 0))
    if "first_line_indent_pt" in typography:
        paragraph.paragraph_format.first_line_indent = Pt(typography["first_line_indent_pt"])
    for run in paragraph.runs:
        _set_run_format(run, typography)


def _set_document_grid(section, line_pitch: int) -> None:
    grid = section._sectPr.find(qn("w:docGrid"))
    if grid is None:
        grid = OxmlElement("w:docGrid")
        section._sectPr.append(grid)
    grid.set(qn("w:linePitch"), str(line_pitch))


def _set_page_gutter(section) -> None:
    margins = section._sectPr.find(qn("w:pgMar"))
    if margins is None:
        raise ValueError("Section page margins were not created")
    margins.set(qn("w:gutter"), "0")


def _set_page_field(footer) -> None:
    element = footer._element
    for child in list(element):
        element.remove(child)
    paragraph = OxmlElement("w:p")
    properties = OxmlElement("w:pPr")
    alignment = OxmlElement("w:jc")
    alignment.set(qn("w:val"), "center")
    properties.append(alignment)
    paragraph.append(properties)
    for field_type, instruction in (
        ("begin", None),
        (None, " PAGE "),
        ("separate", None),
    ):
        run = OxmlElement("w:r")
        if field_type is not None:
            field = OxmlElement("w:fldChar")
            field.set(qn("w:fldCharType"), field_type)
            run.append(field)
        else:
            text = OxmlElement("w:instrText")
            text.set(qn("xml:space"), "preserve")
            text.text = instruction
            run.append(text)
        paragraph.append(run)
    result_run = OxmlElement("w:r")
    result = OxmlElement("w:t")
    result.text = "1"
    result_run.append(result)
    paragraph.append(result_run)
    end_run = OxmlElement("w:r")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run.append(end)
    paragraph.append(end_run)
    element.append(paragraph)


def _set_cell_margins(cell, margins: dict[str, int]) -> None:
    properties = cell._tc.get_or_add_tcPr()
    container = properties.find(qn("w:tcMar"))
    if container is None:
        container = OxmlElement("w:tcMar")
        following_tags = {
            qn("w:textDirection"),
            qn("w:tcFitText"),
            qn("w:vAlign"),
            qn("w:hideMark"),
            qn("w:headers"),
            qn("w:cellIns"),
            qn("w:cellDel"),
            qn("w:cellMerge"),
            qn("w:tcPrChange"),
        }
        insertion_index = next(
            (index for index, child in enumerate(properties) if child.tag in following_tags),
            len(properties),
        )
        properties.insert(insertion_index, container)
    for name in ("top", "start", "bottom", "end"):
        node = container.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            container.append(node)
        node.set(qn("w:w"), str(margins[name]))
        node.set(qn("w:type"), "dxa")


def _set_cell_edge(cell, name: str, *, value: str, size: int = 0) -> None:
    properties = cell._tc.get_or_add_tcPr()
    borders = properties.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        following_tags = {
            qn("w:shd"),
            qn("w:noWrap"),
            qn("w:tcMar"),
            qn("w:textDirection"),
            qn("w:tcFitText"),
            qn("w:vAlign"),
            qn("w:hideMark"),
            qn("w:headers"),
            qn("w:cellIns"),
            qn("w:cellDel"),
            qn("w:cellMerge"),
            qn("w:tcPrChange"),
        }
        insertion_index = next(
            (index for index, child in enumerate(properties) if child.tag in following_tags),
            len(properties),
        )
        properties.insert(insertion_index, borders)
    edge = borders.find(qn(f"w:{name}"))
    if edge is None:
        edge = OxmlElement(f"w:{name}")
        borders.append(edge)
    edge.set(qn("w:val"), value)
    if value == "single":
        edge.set(qn("w:sz"), str(size))
        edge.set(qn("w:color"), "000000")


def _format_tables(document, profile: dict[str, Any]) -> None:
    table_profile = profile["tables"]
    text_profile = dict(profile["typography"]["table_text"])
    text_profile["latin_font"] = profile["typography"]["latin_font"]
    text_profile["font_color_hex"] = profile["typography"]["font_color_hex"]
    for table in document.tables:
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        for row_index, row in enumerate(table.rows):
            row_properties = row._tr.get_or_add_trPr()
            if table_profile["prevent_row_split"] and row_properties.find(qn("w:cantSplit")) is None:
                row_properties.append(OxmlElement("w:cantSplit"))
            if (
                row_index == 0
                and table_profile["repeat_header_row"]
                and row_properties.find(qn("w:tblHeader")) is None
            ):
                row_properties.append(OxmlElement("w:tblHeader"))
            for cell in row.cells:
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                _set_cell_margins(cell, table_profile["cell_margins_twips"])
                for edge_name in ("top", "start", "bottom", "end", "insideH", "insideV"):
                    _set_cell_edge(cell, edge_name, value="nil")
                if row_index == 0:
                    _set_cell_edge(
                        cell,
                        "top",
                        value="single",
                        size=table_profile["top_border_ooxml_size"],
                    )
                    _set_cell_edge(
                        cell,
                        "bottom",
                        value="single",
                        size=table_profile["header_bottom_border_ooxml_size"],
                    )
                if row_index == len(table.rows) - 1:
                    _set_cell_edge(
                        cell,
                        "bottom",
                        value="single",
                        size=table_profile["bottom_border_ooxml_size"],
                    )
                for paragraph in cell.paragraphs:
                    style = paragraph._p.get_or_add_pPr().find(qn("w:pStyle"))
                    if style is not None:
                        paragraph._p.get_or_add_pPr().remove(style)
                    _remove_numbering(paragraph._p)
                    paragraph.paragraph_format.first_line_indent = Pt(0)
                    _apply_paragraph_format(paragraph, text_profile)
                    for run in paragraph.runs:
                        _set_run_format(run, text_profile, bold=(row_index == 0))


def apply_profile(document, profile: dict[str, Any] | None = None) -> None:
    """Apply generic profile rules in place; project-specific layout comes later."""
    profile = profile or load_profile()
    page = profile["page"]
    for section in document.sections:
        section.page_width = Cm(page["width_cm"])
        section.page_height = Cm(page["height_cm"])
        section.top_margin = Cm(page["margins_cm"]["top"])
        section.bottom_margin = Cm(page["margins_cm"]["bottom"])
        section.left_margin = Cm(page["margins_cm"]["left"])
        section.right_margin = Cm(page["margins_cm"]["right"])
        section.header_distance = Cm(page["header_distance_cm"])
        section.footer_distance = Cm(page["footer_distance_cm"])
        section.different_first_page_header_footer = page["different_first_page"]
        _set_page_gutter(section)
        _set_document_grid(section, page["document_grid_line_pitch_twips"])
        _set_page_field(section.footer)
        if page["different_first_page"]:
            _set_page_field(section.first_page_footer)

    typography = profile["typography"]
    common_typography = {
        "latin_font": typography["latin_font"],
        "font_color_hex": typography["font_color_hex"],
    }
    for style_name in ("Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        try:
            _remove_numbering(document.styles[style_name].element)
        except KeyError:
            pass

    in_short_appendix = False
    for index, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style else ""
        if index == 0:
            _remove_numbering(paragraph._p)
            paragraph.paragraph_format.first_line_indent = Pt(0)
            title_profile = dict(typography["title"], **common_typography)
            _apply_paragraph_format(paragraph, title_profile)
            continue
        if style_name.startswith("Heading"):
            _remove_numbering(paragraph._p)
            paragraph.paragraph_format.first_line_indent = Pt(0)
            key = "heading_level_1" if style_name in {"Heading 1", "Heading 2"} else "heading_level_2_and_3"
            heading_profile = dict(typography[key], **common_typography)
            _apply_paragraph_format(paragraph, heading_profile)
            if text.startswith("附录"):
                in_short_appendix = True
            continue
        if paragraph._p.findall(".//" + qn("w:drawing")):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.keep_with_next = True
            continue
        if re.match(r"^[图表]\s*\d+\s", text):
            caption_profile = dict(typography["caption"], **common_typography)
            paragraph.paragraph_format.first_line_indent = Pt(0)
            paragraph.paragraph_format.keep_with_next = text.startswith("表 ")
            _apply_paragraph_format(paragraph, caption_profile)
            continue
        if re.match(r"^\[\d+\]", text):
            reference_profile = dict(
                typography["reference_and_short_appendix"],
                **common_typography,
            )
            paragraph.paragraph_format.left_indent = Pt(reference_profile["hanging_indent_pt"])
            paragraph.paragraph_format.first_line_indent = Pt(-reference_profile["hanging_indent_pt"])
            _apply_paragraph_format(paragraph, reference_profile)
            continue
        if not text and paragraph._p.findall(".//" + qn("m:oMath")):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.first_line_indent = Pt(0)
            continue
        if in_short_appendix:
            appendix_profile = dict(
                typography["reference_and_short_appendix"],
                **common_typography,
            )
            paragraph.paragraph_format.first_line_indent = Pt(0)
            _apply_paragraph_format(paragraph, appendix_profile)
            continue
        body_profile = dict(typography["body"], **common_typography)
        _apply_paragraph_format(paragraph, body_profile)
        if paragraph._p.get_or_add_pPr().find(qn("w:numPr")) is not None:
            paragraph.paragraph_format.first_line_indent = None
        if text.startswith("关键词"):
            paragraph.paragraph_format.first_line_indent = Pt(0)

    _format_tables(document, profile)
