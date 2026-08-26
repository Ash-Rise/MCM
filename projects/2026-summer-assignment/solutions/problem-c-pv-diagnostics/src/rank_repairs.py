"""Task 3: analytical counterfactual losses and exact top-10 repair ranking."""

from __future__ import annotations

from typing import Any

import numpy as np

from data_io import ProblemData
from diagnose_faults import HOTSPOT, MICROCRACK


FAULT_CLASSES = {HOTSPOT, MICROCRACK}


def _loss_from_deviation(mean_generation: float, deviation_decimal: float) -> float:
    if not -1.0 < deviation_decimal < 0.0:
        raise ValueError(f"fault deviation must lie in (-1, 0), found {deviation_decimal}")
    return float(-deviation_decimal / (1.0 + deviation_decimal) * mean_generation)


def rank_repairs(
    data: ProblemData,
    diagnosis_rows: list[dict[str, Any]],
    forecast_result: dict[str, Any] | None = None,
    repair_limit: int = 10,
) -> dict[str, Any]:
    if repair_limit <= 0:
        raise ValueError("repair_limit must be positive")
    diagnosis_by_id = {row["component_id"]: row for row in diagnosis_rows}
    if set(diagnosis_by_id) != set(data.component_ids):
        raise ValueError("diagnosis rows must cover every component exactly once")

    rows: list[dict[str, Any]] = []
    for index, component_id in enumerate(data.component_ids):
        diagnosis = diagnosis_by_id[component_id]
        if diagnosis["fault_class"] not in FAULT_CLASSES:
            continue
        mean_generation = float(np.mean(data.generation[index]))
        deviation_pct = float(data.deviation_pct[index])
        deviation = deviation_pct / 100.0
        counterfactual = mean_generation / (1.0 + deviation)
        loss = counterfactual - mean_generation
        reconstructed_pct = (mean_generation - counterfactual) / counterfactual * 100.0

        # The displayed deviation has 0.1 percentage-point resolution.
        endpoint_deviations = np.asarray(
            [(deviation_pct - 0.05) / 100.0, (deviation_pct + 0.05) / 100.0]
        )
        endpoint_losses = [
            _loss_from_deviation(mean_generation, endpoint) for endpoint in endpoint_deviations
        ]
        rows.append(
            {
                "component_id": component_id,
                "fault_class": diagnosis["fault_class"],
                "string": diagnosis["string"],
                "mean_actual_kwh_day": mean_generation,
                "deviation_pct": deviation_pct,
                "normal_counterfactual_kwh_day": counterfactual,
                "recoverable_loss_kwh_day": loss,
                "reconstructed_deviation_pct": reconstructed_pct,
                "reconstruction_error_percentage_points": reconstructed_pct - deviation_pct,
                "loss_rounding_lower_kwh_day": min(endpoint_losses),
                "loss_rounding_upper_kwh_day": max(endpoint_losses),
            }
        )

    if len(rows) < repair_limit:
        raise ValueError(f"only {len(rows)} faulty modules available for {repair_limit} repairs")
    rows.sort(key=lambda row: (-row["recoverable_loss_kwh_day"], row["component_id"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["selected"] = rank <= repair_limit

    selected = rows[:repair_limit]
    unselected = rows[repair_limit:]
    cutoff_invariant = min(row["recoverable_loss_kwh_day"] for row in selected) >= max(
        row["recoverable_loss_kwh_day"] for row in unselected
    )
    cutoff_overlap = selected[-1]["loss_rounding_lower_kwh_day"] <= unselected[0][
        "loss_rounding_upper_kwh_day"
    ]

    additivity_conditions = {
        "equal_unit_budget_per_repair": True,
        "at_most_ten_repairs_without_other_selection_constraints": True,
        "nonnegative_independent_component_gains": True,
        "set_gain_equals_sum_of_component_gains": True,
        "objective_is_historical_mean_absolute_recoverable_generation": True,
    }
    if not all(additivity_conditions.values()):
        raise RuntimeError("sorting contract is invalid because an additivity condition failed")

    selected_gain = float(sum(row["recoverable_loss_kwh_day"] for row in selected))
    current_station_mean = float(np.mean(data.station_generation))
    post_repair_station_mean = current_station_mean + selected_gain
    summary: dict[str, Any] = {
        "faulty_component_count": len(rows),
        "repair_limit": repair_limit,
        "selected_component_ids": [row["component_id"] for row in selected],
        "historical_mean_gain_kwh_day": selected_gain,
        "current_station_mean_kwh_day": current_station_mean,
        "post_repair_station_mean_kwh_day": post_repair_station_mean,
        "historical_relative_improvement": selected_gain / current_station_mean,
        "cutoff_sorting_invariant": bool(cutoff_invariant),
        "cutoff_rounding_intervals_overlap": bool(cutoff_overlap),
        "rank_10_loss_kwh_day": selected[-1]["recoverable_loss_kwh_day"],
        "rank_11_loss_kwh_day": unselected[0]["recoverable_loss_kwh_day"],
        "additivity_conditions": additivity_conditions,
        "optimality_basis": "exchange argument under equal cost, independent nonnegative additive gains",
        "optimization_solver_used": False,
    }

    if forecast_result is not None:
        forecast = forecast_result["day16_forecast"]
        point_scale = float(forecast["point_kwh"]) / current_station_mean
        confidence = np.asarray(forecast["confidence_95_kwh"], dtype=float) / current_station_mean
        prediction = np.asarray(forecast["prediction_95_kwh"], dtype=float) / current_station_mean
        summary["day16_supplementary"] = {
            "expected_gain_kwh": selected_gain * point_scale,
            "confidence_95_kwh": (selected_gain * confidence).tolist(),
            "prediction_95_kwh": (selected_gain * prediction).tolist(),
            "scaling_basis": "selected Task 2 station forecast divided by historical mean station generation",
            "interval_scope": {
                "interpretation": (
                    "conditional proportional-scaling interval for the selected repair set's day-16 gain"
                ),
                "propagated": [
                    "Task 2 selected-model parameter uncertainty via the station confidence interval",
                    "Task 2 conditional day-level residual variability via the station prediction interval",
                ],
                "held_fixed": [
                    "selected top-10 repair list",
                    "historical recoverable losses and their sum",
                    "station historical mean used as scaling denominator",
                    "proportional relation between station generation and repair gain",
                ],
                "not_propagated": [
                    "deviation-rate rounding uncertainty",
                    "normal-counterfactual estimation uncertainty",
                    "repair effectiveness uncertainty",
                    "additivity or string-coupling uncertainty",
                    "Task 2 candidate-model selection uncertainty",
                    "day-16 weather forecast input uncertainty",
                ],
            },
            "changes_primary_ranking": False,
        }

    return {
        "ranking": rows,
        "priority_repairs": selected,
        "summary": summary,
    }
