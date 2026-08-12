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
DOCX_PATH = PROJECT_ROOT / "paper" / "v2.4" / "A题论文(v2.4).docx"
MARKDOWN_PATH = PROJECT_ROOT / "paper" / "v2.4" / "A题论文(v2.4).md"
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
    assert body.paragraph_format.line_spacing == 1.5
    assert body.paragraph_format.line_spacing_rule == WD_LINE_SPACING.ONE_POINT_FIVE
    assert body._p.pPr.find(qn("w:snapToGrid")).get(qn("w:val")) == "0"
    assert body.runs[0].font.size == Pt(12)
    assert _east_asia_font(body.runs[0]) == "宋体"
    assert caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert caption.runs[0].font.size == Pt(10.5)
    table_paragraph = table.cell(0, 0).paragraphs[0]
    assert table_paragraph.runs[0].font.size == Pt(10.5)
    assert table_paragraph.paragraph_format.line_spacing == 1.15


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
        assert paragraph.paragraph_format.line_spacing == 1.5
        assert paragraph.paragraph_format.line_spacing_rule == WD_LINE_SPACING.ONE_POINT_FIVE


def test_caption_detection_does_not_center_narrative_sentences():
    module = _load_postprocessor()
    document = Document()
    caption = document.add_paragraph("表3 优化后的服务分配")
    narrative = document.add_paragraph("表3给出非零服务分配。")

    module._format_document_typography(document)

    assert caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert narrative.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY


def test_document_grid_matches_reference_body_line_pitch():
    module = _load_postprocessor()
    document = Document()

    module._set_document_line_grid(document)

    document_grid = document.sections[0]._sectPr.find(qn("w:docGrid"))
    assert document_grid is not None
    assert document_grid.get(qn("w:type")) == "lines"
    assert document_grid.get(qn("w:linePitch")) == "360"
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


def test_title_and_abstract_meet_frozen_review_contract():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    title, remainder = markdown.split("\n", maxsplit=1)
    abstract = remainder.split("## 摘 要", maxsplit=1)[1].split(
        "## 一、问题重述", maxsplit=1
    )[0]
    abstract_paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", abstract)
        if paragraph.strip() and not paragraph.startswith("**关键词：**")
    ]

    assert title == "# 基于容量约束运输规划与条件NHPP仿真的急救车辆配置调度优化"
    assert len(title.removeprefix("# ")) <= 32
    assert len(abstract_paragraphs) == 5
    assert all(f"针对任务{number}" in abstract for number in "一二三")
    assert "求解器状态为最优" in abstract
    assert "共同随机数" in abstract
    assert "适用边界" in abstract
    assert "$" not in abstract


def test_markdown_uses_chinese_top_level_headings_and_superscript_citations():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    expected_headings = (
        "## 一、问题重述",
        "## 二、问题分析",
        "## 三、模型假设",
        "## 四、符号说明",
        "## 五、任务一：容量约束站点与服务分配",
        "## 六、任务二：连续多日随机呼叫与车辆调度",
        "## 七、任务三：连续事故时长下的动态应急响应",
        "## 八、模型评价",
    )

    for heading in expected_headings:
        assert heading in markdown
    assert not re.search(r"^## [1-8] ", markdown, flags=re.MULTILINE)
    assert len(re.findall(r"\^\\\[[1-4]\\\]\^", markdown)) == 4
    body, references = markdown.split("## 参考文献", maxsplit=1)
    assert not re.search(r"(?<!\\)\[[1-4]\]", body)
    assert all(f"[{index}]" in references for index in range(1, 5))


def test_markdown_uses_standard_periodic_and_exponential_notation():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    body = markdown.split("## 参考文献", maxsplit=1)[0]

    assert r"\bmod" not in body
    assert r"\exp" not in body
    assert body.count(r"f(t\%24)") == 4
    assert r"\mathrm e^{-\frac{(t-\mu+24k)^2}{2\sigma^2}}" in body


def test_arrival_rate_term_normalization_preserves_run_structure():
    module = _load_postprocessor()
    document = Document()
    paragraph = document.add_paragraph()
    first = paragraph.add_run("纵轴为严格4")
    paragraph.add_run(" ")
    last = paragraph.add_run("min响应率，继续说明。")
    first.bold = True
    last.italic = True

    assert module.normalize_arrival_rate_terms(document) == 1
    assert paragraph.text == "纵轴为4分钟内到达率，继续说明。"
    assert len(paragraph.runs) == 3
    assert paragraph.runs[0].bold is True
    assert paragraph.runs[2].italic is True


def test_markdown_has_algorithm_design_for_all_three_tasks():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    assert markdown.count("算法设计") == 3
    assert "### 5.5 算法设计" in markdown
    assert "### 6.7 算法设计" in markdown
    assert "### 7.5 算法设计" in markdown
    assert markdown.count("| Step ") == 20
    assert "表2 任务一混合整数线性规划模型" in markdown
    assert "表4 任务一算法步骤" in markdown
    assert "表6 任务二算法步骤" in markdown
    assert "表10 任务三算法步骤" in markdown


def test_figure_numbers_are_continuous_and_appendix_matches():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    captions = [
        int(number)
        for number in re.findall(r"^图(\d+)\s", markdown, flags=re.MULTILINE)
    ]

    assert captions == list(range(1, 12))
    assert "图1至图11均由" in markdown


def test_task_one_uses_only_planning_coverage_and_compact_capacity_proof():
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    task_one = markdown.split("## 五、任务一", 1)[1].split("## 六、任务二", 1)[0]

    assert "表3 各建站规模运力可行性" in task_one
    assert "| 最大配车/辆 | 3 | 5 | 7 | 9 | 11 | 12 |" in task_one
    assert "严格4 min中心代理" not in task_one
    assert "0.75 km" not in task_one
    assert "60.714%" not in task_one
    assert "3 km规划服务覆盖率为86.429%" in task_one


def test_complete_docx_postprocessor_removes_heading_numbering_and_fixes_tables(tmp_path):
    module = _load_postprocessor()
    output = tmp_path / "complete-paper.docx"
    module.postprocess_docx(DOCX_PATH, output)

    document = Document(output)
    assert document.paragraphs[0].style.name == "Title"
    assert document.paragraphs[0].runs[0].font.size == Pt(15)
    assert _style_num_id(document.styles["Heading 2"]) == 0
    assert _style_num_id(document.styles["Heading 3"]) == 0
    assert _page_field_count(document.sections[0].footer) == 1
    assert _page_field_count(document.sections[0].first_page_footer) == 1
    assert document.sections[0].footer.paragraphs[0].alignment == 1
    assert document.sections[0].first_page_footer.paragraphs[0].alignment == 1
    document_grid = document.sections[0]._sectPr.find(qn("w:docGrid"))
    assert document_grid is not None
    assert document_grid.get(qn("w:linePitch")) == "360"

    display_math_paragraphs = [
        paragraph
        for paragraph in document.paragraphs
        if not paragraph.text.strip()
        and paragraph._p.findall(".//" + qn("m:oMath"))
    ]
    assert display_math_paragraphs
    assert all(
        paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
        for paragraph in display_math_paragraphs
    )
    table_math_paragraphs = [
        paragraph
        for table in document.tables
        for row in table.rows
        for cell in row.cells
        for paragraph in cell.paragraphs
        if paragraph._p.findall(".//" + qn("m:oMath"))
    ]
    assert table_math_paragraphs
    allowed_left_math_ids = {
        id(paragraph._p)
        for table_index in (3, 5, 9)
        for row in document.tables[table_index].rows[1:]
        for column_index in (0, 1)
        for paragraph in row.cells[column_index].paragraphs
        if paragraph._p.findall(".//" + qn("m:oMath"))
    }
    allowed_left_math_ids.update(
        id(paragraph._p)
        for row in document.tables[0].rows[1:]
        for paragraph in row.cells[1].paragraphs
        if paragraph._p.findall(".//" + qn("m:oMath"))
    )
    assert all(
        paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
        or id(paragraph._p) in allowed_left_math_ids
        for paragraph in table_math_paragraphs
    )
    horizontal_scripts = [
        script
        for script_tag in ("m:sub", "m:sup")
        for script in document.element.body.findall(".//" + qn(script_tag))
        if "".join(script.itertext())
        in {"ij", "ea", "i=1", "j=1", "i(e),j(a)", "wait", "resp"}
    ]
    assert horizontal_scripts
    assert all(len(script.findall(qn("m:r"))) == 1 for script in horizontal_scripts)

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
        table_borders = table._tbl.tblPr.find(qn("w:tblBorders"))
        assert table_borders is not None
        assert table_borders.find(qn("w:top")).get(qn("w:sz")) == "10"
        assert table_borders.find(qn("w:bottom")).get(qn("w:sz")) == "10"
        header_bottom = table.rows[0].cells[0]._tc.tcPr.find(
            qn("w:tcBorders")
        ).find(qn("w:bottom"))
        assert header_bottom.get(qn("w:sz")) == "4"
        tbl_w = table._tbl.tblPr.find(qn("w:tblW"))
        assert tbl_w is not None
        table_width = int(tbl_w.get(qn("w:w")))
        grid = [int(column.get(qn("w:w"))) for column in table._tbl.tblGrid.gridCol_lst]
        assert len(grid) == len(weights)
        assert sum(grid) == table_width
        for row in table.rows:
            assert row._tr.find(qn("w:tblPrEx")) is None
            widths = [int(cell._tc.tcPr.tcW.get(qn("w:w"))) for cell in row.cells]
            assert widths == grid
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    assert paragraph._p.pPr.find(qn("w:pStyle")) is None
                    for run in paragraph.runs:
                        assert run.font.size == Pt(10)

    evaluation_table = document.tables[6]
    assert all(
        cell._tc.tcPr.find(qn("w:noWrap")) is not None
        for row in evaluation_table.rows
        for cell in row.cells
    )
    assert all(
        paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
        for row in evaluation_table.rows
        for cell in row.cells
        for paragraph in cell.paragraphs
    )

    for algorithm_table in (document.tables[3], document.tables[5], document.tables[9]):
        assert all(
            paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER
            for cell in algorithm_table.rows[0].cells
            for paragraph in cell.paragraphs
        )
        assert all(
            paragraph.alignment == WD_ALIGN_PARAGRAPH.LEFT
            for row in algorithm_table.rows[1:]
            for cell in row.cells
            for paragraph in cell.paragraphs
        )

    symbol_table = document.tables[0]
    assert all(
        paragraph.alignment == WD_ALIGN_PARAGRAPH.LEFT
        for row in symbol_table.rows[1:]
        for paragraph in row.cells[1].paragraphs
    )

def test_postprocessor_selects_complete_paper_table_geometry():
    module = _load_postprocessor()

    weights = module.table_width_weights_for_count(12)

    assert len(weights) == 12
    assert tuple(len(item) for item in weights) == (3, 3, 7, 2, 6, 2, 4, 4, 5, 2, 5, 5)


def test_postprocessor_rejects_unknown_table_count():
    module = _load_postprocessor()

    try:
        module.table_width_weights_for_count(10)
    except ValueError as error:
        assert "12 tables" in str(error)
    else:
        raise AssertionError("Unknown paper table count was accepted")


def test_rebind_conversion_manifest_tracks_postprocessed_output(tmp_path):
    module = _load_postprocessor()
    source = tmp_path / "paper.md"
    source.write_text("updated source", encoding="utf-8")
    output = tmp_path / "complete.docx"
    output.write_bytes(b"postprocessed-docx")
    manifest_path = tmp_path / "intermediate.conversion.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": str(source),
                "source_sha256": "stale-source",
                "project_sha256": "stale-project",
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
    assert data["source_sha256"] == module.sha256_file(source)
    assert data["project_sha256"] == module.sha256_file(source)
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
    body_heading = document.add_paragraph("一、问题重述")

    module._keep_abstract_on_first_page(document)

    assert body_heading.paragraph_format.page_break_before is True
