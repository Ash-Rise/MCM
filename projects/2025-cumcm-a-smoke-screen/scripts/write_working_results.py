from __future__ import annotations

import json
import shutil
from pathlib import Path

import openpyxl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = PROJECT_ROOT / "problem-statements" / "attachments"
OUTPUT = PROJECT_ROOT / "results" / "working"


def duration(intervals: list[list[float]]) -> float:
    return sum(right - left for left, right in intervals)


def copy_template(name: str):
    target = OUTPUT / name
    shutil.copyfile(TEMPLATES / name, target)
    workbook = openpyxl.load_workbook(target)
    return target, workbook, workbook.active


def write_q3() -> None:
    data = json.loads((OUTPUT / "q3.json").read_text(encoding="utf-8"))
    target, workbook, sheet = copy_template("result1.xlsx")
    for row, bomb in enumerate(data["bombs"], 2):
        values = [
            data["heading_deg"], data["speed_m_s"], bomb["bomb"],
            *bomb["release_point_m"], *bomb["explosion_point_m"], bomb["individual_duration_s"],
        ]
        for column, value in enumerate(values, 1):
            sheet.cell(row, column, value)
    workbook.save(target)


def write_q4() -> None:
    data = json.loads((OUTPUT / "q4.json").read_text(encoding="utf-8"))
    target, workbook, sheet = copy_template("result2.xlsx")
    for row, record in enumerate(data["records"], 2):
        values = [
            record["drone"], record["heading_deg"], record["speed_m_s"],
            *record["release_point_m"], *record["explosion_point_m"], record["individual_duration_s"],
        ]
        for column, value in enumerate(values, 1):
            sheet.cell(row, column, value)
    workbook.save(target)


def write_q5() -> None:
    data = json.loads((OUTPUT / "q5.json").read_text(encoding="utf-8"))
    target, workbook, sheet = copy_template("result3.xlsx")
    by_key = {(record["drone"], record["bomb"]): record for record in data["records"]}
    for row in range(2, 17):
        key = (sheet.cell(row, 1).value, sheet.cell(row, 4).value)
        record = by_key.get(key)
        if record is None:
            continue
        values = [
            record["drone"], record["heading_deg"], record["speed_m_s"], record["bomb"],
            *record["release_point_m"], *record["explosion_point_m"],
            duration(record["assigned_target_intervals_s"]), record["assigned_missile"],
        ]
        for column, value in enumerate(values, 1):
            sheet.cell(row, column, value)
    workbook.save(target)


def validate() -> None:
    expected = {"result1.xlsx": (3, 10), "result2.xlsx": (3, 10), "result3.xlsx": (12, 12)}
    for name, (filled_rows, columns) in expected.items():
        sheet = openpyxl.load_workbook(OUTPUT / name, data_only=False).active
        rows = [row for row in range(2, sheet.max_row + 1) if sheet.cell(row, columns).value is not None]
        if len(rows) != filled_rows:
            raise RuntimeError(f"{name}: expected {filled_rows} filled result rows, found {len(rows)}")


if __name__ == "__main__":
    write_q3()
    write_q4()
    write_q5()
    validate()
    print("working result1.xlsx, result2.xlsx, and result3.xlsx written and reloaded")
