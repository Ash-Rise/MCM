"""Apply only Problem B-specific layout adjustments to a profiled DOCX."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


TABLE_WIDTH_WEIGHTS = (
    (0.07, 0.13, 0.16, 0.11, 0.19, 0.34),
    (0.13, 0.67, 0.20),
    (0.07, 0.12, 0.12, 0.12, 0.10, 0.19, 0.13, 0.15),
    (0.08, 0.28, 0.10, 0.12, 0.14, 0.09, 0.09, 0.10),
    (0.09, 0.10, 0.25, 0.18, 0.20, 0.18),
    (0.40, 0.20, 0.20, 0.20),
)


def set_table_geometry(table, weights: tuple[float, ...], width_dxa: int) -> None:
    if len(table.columns) != len(weights):
        raise ValueError(f"Expected {len(weights)} columns, found {len(table.columns)}")
    widths = [round(width_dxa * weight / sum(weights)) for weight in weights]
    widths[-1] += width_dxa - sum(widths)
    table.autofit = False
    table_properties = table._tbl.tblPr
    table_width = table_properties.find(qn("w:tblW"))
    if table_width is None:
        table_width = OxmlElement("w:tblW")
        table_properties.append(table_width)
    table_width.set(qn("w:w"), str(width_dxa))
    table_width.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        column = OxmlElement("w:gridCol")
        column.set(qn("w:w"), str(width))
        grid.append(column)
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            cell_properties = cell._tc.get_or_add_tcPr()
            cell_width = cell_properties.find(qn("w:tcW"))
            if cell_width is None:
                cell_width = OxmlElement("w:tcW")
            else:
                cell_properties.remove(cell_width)
            conditional_format = cell_properties.find(qn("w:cnfStyle"))
            insertion_index = 1 if conditional_format is not None else 0
            cell_properties.insert(insertion_index, cell_width)
            cell_width.set(qn("w:w"), str(widths[index]))
            cell_width.set(qn("w:type"), "dxa")


def apply_project_layout(document) -> None:
    if len(document.tables) != len(TABLE_WIDTH_WEIGHTS):
        raise ValueError(
            f"Expected {len(TABLE_WIDTH_WEIGHTS)} tables, found {len(document.tables)}"
        )
    section = document.sections[0]
    content_width = int((section.page_width - section.left_margin - section.right_margin) / 635)
    for table_index, (table, weights) in enumerate(
        zip(document.tables, TABLE_WIDTH_WEIGHTS, strict=True)
    ):
        set_table_geometry(table, weights, content_width - 120)
        for row_index, row in enumerate(table.rows):
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = (
                        table_index != 1 and row_index < len(table.rows) - 1
                    )

    first_body_heading = next(
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.strip().endswith("问题重述")
    )
    first_body_heading.paragraph_format.page_break_before = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    document = Document(args.input)
    apply_project_layout(document)
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


if __name__ == "__main__":
    main()
