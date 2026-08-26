"""Minimal deterministic Problem C input-to-results pipeline. No paper or figures."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from data_io import load_problem_data, write_csv, write_json
from diagnose_faults import diagnose_components, summarize_distribution
from forecast_station import compare_candidates
from rank_repairs import rank_repairs


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
ASSIGNMENT_ROOT = SOLUTION_ROOT.parents[1]
DEFAULT_SUPPORTING_DOCX = ASSIGNMENT_ROOT / "problem-statements" / "problem-c-supporting-data.docx"


def _generation_long_rows(data: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component_index, component_id in enumerate(data.component_ids):
        for day_index, generation in enumerate(data.generation[component_index], start=1):
            rows.append(
                {
                    "component_id": component_id,
                    "day": day_index,
                    "generation_kwh": float(generation),
                }
            )
    return rows


def _weather_rows(data: Any) -> list[dict[str, Any]]:
    station = data.station_generation
    rows: list[dict[str, Any]] = []
    for index, weather in enumerate(data.weather):
        row = dict(weather)
        row["station_generation_kwh"] = float(station[index]) if index < 15 else ""
        rows.append(row)
    return rows


def reproduce(supporting_docx: Path, output_root: Path) -> dict[str, Any]:
    data = load_problem_data(supporting_docx)

    derived = output_root.parent / "data" / "derived"
    write_csv(derived / "component_parameters.csv", data.parameters)
    write_csv(derived / "component_daily_generation.csv", _generation_long_rows(data))
    write_csv(derived / "station_daily_weather.csv", _weather_rows(data))

    diagnosis_rows, diagnosis_summary = diagnose_components(data)
    task1 = output_root / "task-1"
    write_csv(task1 / "component_diagnosis.csv", diagnosis_rows)
    write_json(task1 / "fault_summary.json", diagnosis_summary)
    distributions: list[dict[str, Any]] = []
    for field in ("string", "azimuth_deg", "tilt_deg", "service_years"):
        distributions.extend(summarize_distribution(diagnosis_rows, field))
    write_csv(task1 / "fault_distributions.csv", distributions)
    write_csv(
        task1 / "shading_screen.csv",
        diagnosis_rows,
        fieldnames=[
            "component_id",
            "fault_class",
            "shading_suspect",
            "shading_screen_status",
            "config_dispersion",
            "config_cutoff",
            "config_anomaly_days",
            "global_dispersion",
            "global_cutoff",
            "global_anomaly_days",
        ],
    )

    forecast = compare_candidates(data)
    task2 = output_root / "task-2"
    write_csv(task2 / "candidate_metrics.csv", forecast["candidate_comparison"])
    write_csv(task2 / "loo_predictions.csv", forecast["loo_predictions"])
    write_json(task2 / "selected_model.json", forecast["selection"])
    write_json(task2 / "day16_forecast.json", forecast["day16_forecast"])

    repairs = rank_repairs(data, diagnosis_rows, forecast)
    task3 = output_root / "task-3"
    write_csv(task3 / "repair_ranking.csv", repairs["ranking"])
    write_csv(task3 / "priority_repairs.csv", repairs["priority_repairs"])
    write_json(task3 / "improvement_summary.json", repairs["summary"])

    manifest = {
        "supporting_data": str(supporting_docx.resolve()),
        "component_count": len(data.component_ids),
        "historical_day_count": data.generation.shape[1],
        "task1_reference_agreement_rate": diagnosis_summary["reference_agreement_rate"],
        "task2_technical_selection": forecast["selection"]["selected_candidate"],
        "task3_selected_components": repairs["summary"]["selected_component_ids"],
        "paper_generated": False,
        "figures_generated": False,
    }
    write_json(output_root / "implementation_run.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supporting-data", type=Path, default=DEFAULT_SUPPORTING_DOCX)
    parser.add_argument("--output-root", type=Path, default=SOLUTION_ROOT / "results")
    args = parser.parse_args()
    manifest = reproduce(args.supporting_data, args.output_root)
    print(f"completed Problem C minimal run; Task 2 technical selection: {manifest['task2_technical_selection']}")


if __name__ == "__main__":
    main()
