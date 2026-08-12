import importlib.util
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Pt
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCX_PATH = PROJECT_ROOT / "paper" / "A题论文(v2.1).docx"
MARKDOWN_PATH = PROJECT_ROOT / "paper" / "A题论文(v2.2).md"
POSTPROCESS_PATH = PROJECT_ROOT / "src" / "postprocess_paper_docx.py"


def _load_postprocessor():
    spec = importlib.util.spec_from_file_location("postprocess_paper_docx", POSTPROCESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {POSTPROCESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _style_num_id(style):
    p_pr = style.element.pPr
    if p_pr is None or p_pr.numPr is None or p_pr.numPr.numId is None:
        return None
    return p_pr.numPr.numId.val


def _page_field_count(footer):
    return len(footer._element.findall(".//" + qn("w:instrText")))


def _east_asia_font(run):
    return run._r.get_or_add_rPr().get_or_add_rFonts().get(qn("w:eastAsia"))


def test_paper_typography_matches_reference_document():
    module = _load_postprocessor()
    document = Document()
    heading = document.add_heading("1 问题重述", level=2)
    body = document.add_paragraph("正文段落")
    caption = document.add_paragraph("图1 测试图")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "表格文字"

    module._format_document_typography(document)

    assert heading.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert heading.runs[0].font.size == Pt(14)
    assert heading.runs[0].bold is True
    assert _east_asia_font(heading.runs[0]) == "黑体"
    assert body.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert body.style.name == "Body Text"
    assert body.paragraph_format.first_line_indent == Pt(24)
    assert body.paragraph_format.line_spacing == Pt(16)
    assert body.paragraph_format.line_spacing_rule == WD_LINE_SPACING.EXACTLY
    assert body._p.pPr.find(qn("w:snapToGrid")).get(qn("w:val")) == "0"
    assert body.runs[0].font.size == Pt(12)
    assert _east_asia_font(body.runs[0]) == "宋体"
    assert caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert caption.runs[0].font.size == Pt(10.5)
    assert table.cell(0, 0).paragraphs[0].runs[0].font.size == Pt(10.5)


def test_typography_normalizes_dangling_pandoc_body_styles():
    module = _load_postprocessor()
    document = Document()
    first = document.add_paragraph("标题后的首段")
    first._p.get_or_add_pPr().get_or_add_pStyle().val = "FirstParagraph"
    listed = document.add_paragraph("编号正文")
    listed_p_pr = listed._p.get_or_add_pPr()
    listed_p_pr.get_or_add_pStyle().val = "Compact"
    listed_p_pr.get_or_add_numPr().get_or_add_numId().val = 1

    module._format_document_typography(document)

    assert first.style.name == "Body Text"
    assert listed.style.name == "Body Text"
    assert listed._p.pPr.numPr.numId.val == 1
    for paragraph in (first, listed):
        assert paragraph.paragraph_format.line_spacing == Pt(16)
        assert paragraph.paragraph_format.line_spacing_rule == WD_LINE_SPACING.EXACTLY


def test_caption_detection_does_not_center_narrative_sentences():
    module = _load_postprocessor()
    document = Document()
    caption = document.add_paragraph("表3 优化后的服务分配")
    narrative = document.add_paragraph("表3给出非零服务分配。")

    module._format_document_typography(document)

    assert caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert narrative.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY


def test_document_grid_matches_exact_body_line_height():
    module = _load_postprocessor()
    document = Document()

    module._set_document_line_grid(document)

    document_grid = document.sections[0]._sectPr.find(qn("w:docGrid"))
    assert document_grid is not None
    assert document_grid.get(qn("w:type")) == "lines"
    assert document_grid.get(qn("w:linePitch")) == "320"
    assert document_grid.get(qn("w:charSpace")) == "0"


def test_disable_grid_places_snap_before_spacing_and_alignment():
    module = _load_postprocessor()
    document = Document()
    paragraph = document.add_paragraph("正文")
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    module._disable_paragraph_grid(paragraph)

    child_tags = [child.tag for child in paragraph._p.pPr]
    snap_index = child_tags.index(qn("w:snapToGrid"))
    assert snap_index < child_tags.index(qn("w:spacing"))
    assert snap_index < child_tags.index(qn("w:jc"))


def test_markdown_math_avoids_bare_star_superscripts():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    assert not re.search(r"\^\*", markdown)


def test_complete_docx_postprocessor_removes_heading_numbering_and_fixes_tables(tmp_path):
    module = _load_postprocessor()
    output = tmp_path / "complete-paper.docx"
    module.postprocess_docx(DOCX_PATH, output)

    document = Document(output)
    assert document.paragraphs[0].style.name == "Title"
    assert _style_num_id(document.styles["Heading 2"]) == 0
    assert _style_num_id(document.styles["Heading 3"]) == 0
    assert _page_field_count(document.sections[0].footer) == 1
    assert _page_field_count(document.sections[0].first_page_footer) == 1
    assert document.sections[0].footer.paragraphs[0].alignment == 1
    assert document.sections[0].first_page_footer.paragraphs[0].alignment == 1
    document_grid = document.sections[0]._sectPr.find(qn("w:docGrid"))
    assert document_grid is not None
    assert document_grid.get(qn("w:linePitch")) == "320"

    for paragraph in document.paragraphs:
        if paragraph.alignment != WD_ALIGN_PARAGRAPH.CENTER:
            continue
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style is not None else ""
        is_expected_center = (
            style_name in {"Title", "Heading 1", "Heading 2"}
            or module._is_figure_or_table_caption(text)
            or bool(paragraph._p.findall(".//" + qn("w:drawing")))
            or (not text and bool(paragraph._p.findall(".//" + qn("m:oMath"))))
        )
        assert is_expected_center, f"Unexpected centered paragraph: {text[:80]}"

    assert len(document.tables) == len(module.COMPLETE_TABLE_WIDTH_WEIGHTS)
    assert document.tables[0].cell(8, 2).text == "1/h，次/h"
    for table, weights in zip(
        document.tables, module.COMPLETE_TABLE_WIDTH_WEIGHTS, strict=True
    ):
        assert table._tbl.tblPr.find(qn("w:tblStyle")) is None
        tbl_w = table._tbl.tblPr.find(qn("w:tblW"))
        assert tbl_w is not None
        table_width = int(tbl_w.get(qn("w:w")))
        grid = [int(column.get(qn("w:w"))) for column in table._tbl.tblGrid.gridCol_lst]
        assert len(grid) == len(weights)
        assert sum(grid) == table_width
        for row in table.rows:
            widths = [int(cell._tc.tcPr.tcW.get(qn("w:w"))) for cell in row.cells]
            assert widths == grid
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    assert paragraph._p.pPr.find(qn("w:pStyle")) is None


def test_postprocessor_selects_complete_paper_table_geometry():
    module = _load_postprocessor()

    weights = module.table_width_weights_for_count(8)

    assert len(weights) == 8
    assert tuple(len(item) for item in weights) == (3, 6, 3, 4, 4, 5, 5, 5)


def test_postprocessor_rejects_unknown_table_count():
    module = _load_postprocessor()

    try:
        module.table_width_weights_for_count(7)
    except ValueError as error:
        assert "8 tables" in str(error)
    else:
        raise AssertionError("Unknown paper table count was accepted")


def test_rebind_conversion_manifest_tracks_postprocessed_output(tmp_path):
    module = _load_postprocessor()
    output = tmp_path / "complete.docx"
    output.write_bytes(b"postprocessed-docx")
    manifest_path = tmp_path / "intermediate.conversion.json"
    manifest_path.write_text(
        json.dumps(
            {
                "output": str(tmp_path / "intermediate.docx"),
                "output_sha256": "stale",
            }
        ),
        encoding="utf-8",
    )

    final_manifest = module.rebind_conversion_manifest(manifest_path, output)

    assert final_manifest == output.with_suffix(".conversion.json")
    data = json.loads(final_manifest.read_text(encoding="utf-8"))
    assert data["output"] == str(output.resolve())
    assert data["output_sha256"] == module.sha256_file(output)
    assert data["postprocess"]["tool"] == "src/postprocess_paper_docx.py"


def test_body_image_alt_text_uses_following_figure_caption(tmp_path):
    module = _load_postprocessor()
    image_path = tmp_path / "figure.png"
    Image.new("RGB", (4, 4), "white").save(image_path)
    document = Document()
    document.add_picture(str(image_path))
    document.add_paragraph("图1 测试图像")
    document.add_picture(str(image_path))
    document.add_paragraph("普通段落")

    assert module._set_body_image_alt_text(document) == 1
    properties = document.paragraphs[0]._p.find(".//" + qn("wp:docPr"))
    assert properties is not None
    assert properties.get("descr") == "图1 测试图像"
    assert properties.get("title") == "图1"
    untouched = document.paragraphs[2]._p.find(".//" + qn("wp:docPr"))
    assert untouched is not None
    assert untouched.get("descr") is None


def test_postprocessor_keeps_abstract_on_first_page():
    module = _load_postprocessor()
    document = Document()
    document.add_paragraph("摘要内容")
    body_heading = document.add_paragraph("1 问题重述")

    module._keep_abstract_on_first_page(document)

    assert body_heading.paragraph_format.page_break_before is True
