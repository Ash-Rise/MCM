"""Task 2: unified comparison of M0/M1/M2 and day-16 uncertainty."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import lsq_linear
from scipy.stats import spearmanr, t as student_t

from data_io import ProblemData


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    family: str
    terms: tuple[str, ...]
    complexity_order: int

    @property
    def parameter_names(self) -> tuple[str, ...]:
        if self.family == "M0":
            return ("beta_H",)
        if self.family == "M1":
            return ("alpha", "beta_H")
        names = ["beta_0"]
        if "temperature" in self.terms:
            names.append("beta_T")
        if "wind" in self.terms:
            names.append("beta_W")
        return tuple(names)


M0 = CandidateSpec("M0", "M0", (), 0)
M1 = CandidateSpec("M1", "M1", (), 1)
M2 = CandidateSpec("M2", "M2", ("temperature", "wind"), 2)


def _design_matrix(
    spec: CandidateSpec,
    irradiation: np.ndarray,
    temperature: np.ndarray,
    wind: np.ndarray,
    temperature_ref: float,
    wind_ref: float,
) -> np.ndarray:
    h = np.asarray(irradiation, dtype=float)
    if spec.family == "M0":
        return h[:, None]
    if spec.family == "M1":
        return np.column_stack([np.ones_like(h), h])
    columns = [h]
    if "temperature" in spec.terms:
        columns.append(h * (np.asarray(temperature, dtype=float) - temperature_ref))
    if "wind" in spec.terms:
        columns.append(h * (np.asarray(wind, dtype=float) - wind_ref))
    return np.column_stack(columns)


def _standardized_condition_number(spec: CandidateSpec, x: np.ndarray) -> float:
    diagnostic = x[:, 1:] if spec.family == "M1" else x
    if diagnostic.shape[1] <= 1:
        return 1.0
    centered = diagnostic - diagnostic.mean(axis=0)
    scale = centered.std(axis=0, ddof=1)
    if np.any(scale <= np.finfo(float).eps):
        return float("inf")
    return float(np.linalg.cond(centered / scale))


def _fit(spec: CandidateSpec, x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    rank = int(np.linalg.matrix_rank(x))
    if spec.family == "M2":
        lower = [0.0]
        upper = [np.inf]
        if "temperature" in spec.terms:
            lower.append(-np.inf)
            upper.append(0.0)
        if "wind" in spec.terms:
            lower.append(0.0)
            upper.append(np.inf)
        solution = lsq_linear(x, y, bounds=(np.asarray(lower), np.asarray(upper)), method="trf")
        if not solution.success:
            raise RuntimeError(f"{spec.name} constrained fit failed: {solution.message}")
        coefficients = solution.x
    else:
        coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ coefficients
    residuals = y - fitted
    return {
        "coefficients": coefficients,
        "fitted": fitted,
        "residuals": residuals,
        "rank": rank,
        "condition_number": _standardized_condition_number(spec, x),
    }


def _regression_interval(
    spec: CandidateSpec,
    x: np.ndarray,
    y: np.ndarray,
    fit: dict[str, Any],
    x0: np.ndarray,
    confidence: float = 0.95,
) -> dict[str, float]:
    n, p = x.shape
    dof = n - p
    if dof <= 0:
        raise ValueError("not enough residual degrees of freedom")
    residual_sum_squares = float(np.sum(np.square(fit["residuals"])))
    mse = residual_sum_squares / dof
    xtx_inverse = np.linalg.pinv(x.T @ x)
    leverage = float(x0 @ xtx_inverse @ x0)
    mean_se = float(np.sqrt(max(0.0, mse * leverage)))
    prediction_se = float(np.sqrt(max(0.0, mse * (1.0 + leverage))))
    quantile = float(student_t.ppf((1.0 + confidence) / 2.0, dof))
    point = float(x0 @ fit["coefficients"])
    return {
        "point": point,
        "confidence_lower": point - quantile * mean_se,
        "confidence_upper": point + quantile * mean_se,
        "prediction_lower": point - quantile * prediction_se,
        "prediction_upper": point + quantile * prediction_se,
        "degrees_of_freedom": dof,
        "residual_mse": mse,
    }


def _bootstrap_interval_sensitivity(
    spec: CandidateSpec,
    x: np.ndarray,
    y: np.ndarray,
    fit: dict[str, Any],
    x0: np.ndarray,
    samples: int = 500,
    seed: int = 2026,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    centered_residuals = fit["residuals"] - np.mean(fit["residuals"])
    mean_predictions: list[float] = []
    realized_predictions: list[float] = []
    for _ in range(samples):
        resampled = rng.choice(centered_residuals, size=len(y), replace=True)
        synthetic_y = fit["fitted"] + resampled
        synthetic_fit = _fit(spec, x, synthetic_y)
        point = float(x0 @ synthetic_fit["coefficients"])
        mean_predictions.append(point)
        realized_predictions.append(point + float(rng.choice(centered_residuals)))
    return {
        "samples": samples,
        "seed": seed,
        "confidence_lower": float(np.quantile(mean_predictions, 0.025)),
        "confidence_upper": float(np.quantile(mean_predictions, 0.975)),
        "prediction_lower": float(np.quantile(realized_predictions, 0.025)),
        "prediction_upper": float(np.quantile(realized_predictions, 0.975)),
    }


def _hc3_scaled_residual_interval(
    x: np.ndarray,
    y: np.ndarray,
    fit: dict[str, Any],
    x0: np.ndarray,
    residual_scale: np.ndarray,
    forecast_scale: float,
    confidence: float = 0.95,
) -> dict[str, float]:
    """Keep the selected point model fixed and adjust only its uncertainty estimate."""

    n, p = x.shape
    dof = n - p
    if dof <= 0:
        raise ValueError("not enough residual degrees of freedom")
    if np.any(residual_scale <= 0) or forecast_scale <= 0:
        raise ValueError("scaled-residual interval requires positive scale values")

    xtx_inverse = np.linalg.pinv(x.T @ x)
    leverage = np.einsum("ij,jk,ik->i", x, xtx_inverse, x)
    leverage_denominator = np.maximum(1.0 - leverage, np.finfo(float).eps)
    hc3_adjusted = fit["residuals"] / leverage_denominator
    meat = x.T @ (np.square(hc3_adjusted)[:, None] * x)
    hc3_covariance = xtx_inverse @ meat @ xtx_inverse
    mean_variance = float(max(0.0, x0 @ hc3_covariance @ x0))

    normalized_residuals = fit["residuals"] / residual_scale
    conditional_residual_variance = float(
        forecast_scale * forecast_scale * np.sum(np.square(normalized_residuals)) / dof
    )
    quantile = float(student_t.ppf((1.0 + confidence) / 2.0, dof))
    point = float(x0 @ fit["coefficients"])
    mean_se = float(np.sqrt(mean_variance))
    prediction_se = float(np.sqrt(mean_variance + conditional_residual_variance))
    return {
        "point": point,
        "confidence_lower": point - quantile * mean_se,
        "confidence_upper": point + quantile * mean_se,
        "prediction_lower": point - quantile * prediction_se,
        "prediction_upper": point + quantile * prediction_se,
        "degrees_of_freedom": dof,
        "parameter_variance_method": "HC3 sandwich covariance on selected full-data fit",
        "conditional_residual_variance_kwh2": conditional_residual_variance,
    }


def _scaled_residual_bootstrap_sensitivity(
    spec: CandidateSpec,
    x: np.ndarray,
    y: np.ndarray,
    fit: dict[str, Any],
    x0: np.ndarray,
    residual_scale: np.ndarray,
    forecast_scale: float,
    samples: int = 500,
    seed: int = 2026,
) -> dict[str, float]:
    """Refit the same selected model under irradiation-scaled residual resampling."""

    rng = np.random.default_rng(seed)
    normalized_residuals = fit["residuals"] / residual_scale
    normalized_residuals = normalized_residuals - np.mean(normalized_residuals)
    mean_predictions: list[float] = []
    realized_predictions: list[float] = []
    for _ in range(samples):
        resampled = rng.choice(normalized_residuals, size=len(y), replace=True)
        synthetic_y = fit["fitted"] + residual_scale * resampled
        synthetic_fit = _fit(spec, x, synthetic_y)
        point = float(x0 @ synthetic_fit["coefficients"])
        mean_predictions.append(point)
        realized_predictions.append(point + forecast_scale * float(rng.choice(normalized_residuals)))
    return {
        "samples": samples,
        "seed": seed,
        "confidence_lower": float(np.quantile(mean_predictions, 0.025)),
        "confidence_upper": float(np.quantile(mean_predictions, 0.975)),
        "prediction_lower": float(np.quantile(realized_predictions, 0.025)),
        "prediction_upper": float(np.quantile(realized_predictions, 0.975)),
        "point_model_refit": "same selected candidate definition on original Y scale",
    }


def _intercept_ci_contains_zero(x: np.ndarray, y: np.ndarray, fit: dict[str, Any]) -> bool:
    n, p = x.shape
    dof = n - p
    mse = float(np.sum(np.square(fit["residuals"]))) / dof
    standard_error = float(np.sqrt(mse * np.linalg.pinv(x.T @ x)[0, 0]))
    quantile = float(student_t.ppf(0.975, dof))
    alpha = float(fit["coefficients"][0])
    return alpha - quantile * standard_error <= 0.0 <= alpha + quantile * standard_error


def _evaluate_candidate(
    spec: CandidateSpec,
    y: np.ndarray,
    irradiation: np.ndarray,
    temperature: np.ndarray,
    wind: np.ndarray,
    day16: tuple[float, float, float],
    temperature_ref: float,
    wind_ref: float,
) -> dict[str, Any]:
    full_x = _design_matrix(spec, irradiation, temperature, wind, temperature_ref, wind_ref)
    full_fit = _fit(spec, full_x, y)
    day16_x = _design_matrix(
        spec,
        np.asarray([day16[0]]),
        np.asarray([day16[1]]),
        np.asarray([day16[2]]),
        temperature_ref,
        wind_ref,
    )[0]

    loo_predictions: list[float] = []
    loo_coefficients: list[np.ndarray] = []
    loo_ranks: list[int] = []
    loo_conditions: list[float] = []
    loo_day16_predictions: list[float] = []
    historical_prediction_minima: list[float] = []
    for held_out in range(len(y)):
        train = np.arange(len(y)) != held_out
        train_x = full_x[train]
        train_y = y[train]
        fold_fit = _fit(spec, train_x, train_y)
        loo_predictions.append(float(full_x[held_out] @ fold_fit["coefficients"]))
        loo_coefficients.append(fold_fit["coefficients"])
        loo_ranks.append(fold_fit["rank"])
        loo_conditions.append(fold_fit["condition_number"])
        loo_day16_predictions.append(float(day16_x @ fold_fit["coefficients"]))
        historical_prediction_minima.append(float(np.min(full_x @ fold_fit["coefficients"])))

    predictions = np.asarray(loo_predictions)
    errors = y - predictions
    absolute_errors = np.abs(errors)
    coefficients = np.asarray(loo_coefficients)
    mae = float(np.mean(absolute_errors))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    sst = float(np.sum(np.square(y - np.mean(y))))
    cv_r2 = float(1.0 - np.sum(np.square(errors)) / sst) if sst > 0 else float("nan")
    full_residual_sse = float(np.sum(np.square(full_fit["residuals"])))
    full_r2 = float(1.0 - full_residual_sse / sst) if sst > 0 else float("nan")

    reasons: list[str] = []
    parameter_count = full_x.shape[1]
    if full_fit["rank"] != parameter_count or any(rank != parameter_count for rank in loo_ranks):
        reasons.append("design matrix is not full rank in every fit")
    beta_main_index = 1 if spec.family == "M1" else 0
    if full_fit["coefficients"][beta_main_index] <= 0 or np.any(coefficients[:, beta_main_index] <= 0):
        reasons.append("irradiation main effect is not positive in every fit")
    if min(historical_prediction_minima) < 0 or min(loo_day16_predictions) < 0:
        reasons.append("negative historical or day-16 prediction")
    if max(abs(np.asarray(loo_day16_predictions) - float(day16_x @ full_fit["coefficients"]))) > 2.0 * rmse:
        reasons.append("day-16 prediction is unstable under one-day deletion")
    if spec.family == "M1" and not _intercept_ci_contains_zero(full_x, y, full_fit):
        reasons.append("M1 intercept 95% confidence interval excludes zero")
    if spec.family == "M2" and max([full_fit["condition_number"], *loo_conditions]) > 30.0:
        reasons.append("standardized design condition number exceeds 30")

    full_coefficients = np.asarray(full_fit["coefficients"])
    coefficient_scale = max(float(np.max(np.abs(full_coefficients))), 1.0)
    relative_tolerance = 1e-10 * coefficient_scale
    unstable_parameters: list[str] = []
    for index, parameter_name in enumerate(spec.parameter_names):
        full_value = float(full_coefficients[index])
        if abs(full_value) <= relative_tolerance:
            if parameter_name not in ("alpha",):
                unstable_parameters.append(f"{parameter_name}: unsupported near-zero full estimate")
            continue
        fold_values = coefficients[:, index]
        if np.max(np.abs(fold_values - full_value)) / abs(full_value) > 1.0:
            unstable_parameters.append(f"{parameter_name}: changes by more than 100% under deletion")
        if parameter_name == "beta_T" and np.any(fold_values > relative_tolerance):
            unstable_parameters.append("beta_T: physical sign reversal")
        if parameter_name == "beta_W" and np.any(fold_values < -relative_tolerance):
            unstable_parameters.append("beta_W: physical sign reversal")
    reasons.extend(unstable_parameters)

    boundary_hits: dict[str, int] = {}
    if spec.family == "M2":
        for index, parameter_name in enumerate(spec.parameter_names):
            if parameter_name in ("beta_T", "beta_W"):
                boundary_hits[parameter_name] = int(np.sum(np.abs(coefficients[:, index]) <= relative_tolerance))
                if boundary_hits[parameter_name] > 5:
                    reasons.append(f"{parameter_name} is at the zero boundary in more than 5 folds")

    return {
        "spec": spec,
        "x": full_x,
        "fit": full_fit,
        "day16_x": day16_x,
        "loo_predictions": predictions,
        "loo_errors": errors,
        "loo_absolute_errors": absolute_errors,
        "loo_coefficients": coefficients,
        "loo_conditions": np.asarray(loo_conditions),
        "loo_day16_predictions": np.asarray(loo_day16_predictions),
        "mae": mae,
        "rmse": rmse,
        "max_absolute_error": float(np.max(absolute_errors)),
        "normalized_mae": mae / float(np.mean(y)),
        "cv_r2": cv_r2,
        "full_r2": full_r2,
        "boundary_hits": boundary_hits,
        "eligibility_reasons": reasons,
        "eligible": len(reasons) == 0,
    }


def _candidate_summary(evaluation: dict[str, Any]) -> dict[str, Any]:
    spec: CandidateSpec = evaluation["spec"]
    fit = evaluation["fit"]
    return {
        "candidate": spec.name,
        "family": spec.family,
        "terms": list(spec.terms),
        "parameter_count": len(spec.parameter_names),
        "eligible": evaluation["eligible"],
        "eligibility_reasons": list(evaluation["eligibility_reasons"]),
        "mae_kwh": evaluation["mae"],
        "rmse_kwh": evaluation["rmse"],
        "max_absolute_error_kwh": evaluation["max_absolute_error"],
        "normalized_mae": evaluation["normalized_mae"],
        "cv_r2": evaluation["cv_r2"],
        "full_r2": evaluation["full_r2"],
        "full_condition_number": fit["condition_number"],
        "max_loo_condition_number": float(np.max(evaluation["loo_conditions"])),
        "coefficients": {
            name: float(value) for name, value in zip(spec.parameter_names, fit["coefficients"])
        },
        "boundary_hits": dict(evaluation["boundary_hits"]),
    }


def compare_candidates(data: ProblemData) -> dict[str, Any]:
    y = np.asarray(data.station_generation, dtype=float)
    irradiation = np.asarray([row["irradiation_kwh_m2"] for row in data.historical_weather])
    temperature = np.asarray([row["temperature_c"] for row in data.historical_weather])
    wind = np.asarray([row["wind_m_s"] for row in data.historical_weather])
    day16 = (
        float(data.day16_weather["irradiation_kwh_m2"]),
        float(data.day16_weather["temperature_c"]),
        float(data.day16_weather["wind_m_s"]),
    )
    temperature_ref = float(np.mean(temperature))
    wind_ref = float(np.mean(wind))

    evaluations = [
        _evaluate_candidate(spec, y, irradiation, temperature, wind, day16, temperature_ref, wind_ref)
        for spec in (M0, M1, M2)
    ]

    full_m2 = evaluations[-1]
    supported_terms = []
    if full_m2["boundary_hits"].get("beta_T", 0) <= 5:
        supported_terms.append("temperature")
    if full_m2["boundary_hits"].get("beta_W", 0) <= 5:
        supported_terms.append("wind")
    if 0 < len(supported_terms) < 2:
        suffix = "T" if supported_terms == ["temperature"] else "W"
        reduced = CandidateSpec(f"M2_{suffix}", "M2", tuple(supported_terms), 2)
        evaluations.append(
            _evaluate_candidate(reduced, y, irradiation, temperature, wind, day16, temperature_ref, wind_ref)
        )

    # An extension whose lower MAE is driven by too few days or a single day is ineligible.
    baseline_errors = evaluations[0]["loo_absolute_errors"]
    for evaluation in evaluations[1:]:
        if evaluation["mae"] < evaluations[0]["mae"]:
            improvement = baseline_errors - evaluation["loo_absolute_errors"]
            positive = improvement[improvement > 0]
            if int(np.sum(improvement > 0)) < 8:
                evaluation["eligibility_reasons"].append("improves absolute error on fewer than 8 of 15 days")
            if positive.size and float(np.max(positive) / np.sum(positive)) > 0.5:
                evaluation["eligibility_reasons"].append("one day contributes over 50% of positive error improvement")
            evaluation["eligible"] = len(evaluation["eligibility_reasons"]) == 0

    eligible = [evaluation for evaluation in evaluations if evaluation["eligible"]]
    if not eligible:
        raise RuntimeError("no candidate passed the frozen eligibility contract")
    minimum = min(eligible, key=lambda item: item["mae"])
    mae_standard_error = float(np.std(minimum["loo_absolute_errors"], ddof=1) / np.sqrt(len(y)))
    one_se_threshold = minimum["mae"] + mae_standard_error
    one_se_set = [evaluation for evaluation in eligible if evaluation["mae"] <= one_se_threshold]
    selected = min(
        one_se_set,
        key=lambda item: (len(item["spec"].parameter_names), item["spec"].complexity_order, item["spec"].name),
    )

    raw_correlation = spearmanr(np.abs(selected["fit"]["residuals"]), irradiation)
    normalized_residuals = selected["fit"]["residuals"] / irradiation
    normalized_correlation = spearmanr(np.abs(normalized_residuals), irradiation)
    use_normalized_scale = abs(float(normalized_correlation.statistic)) < abs(
        float(raw_correlation.statistic)
    )
    if use_normalized_scale:
        day16_irradiation = day16[0]
        interval = _hc3_scaled_residual_interval(
            selected["x"],
            y,
            selected["fit"],
            selected["day16_x"],
            irradiation,
            day16_irradiation,
        )
        bootstrap = _scaled_residual_bootstrap_sensitivity(
            selected["spec"],
            selected["x"],
            y,
            selected["fit"],
            selected["day16_x"],
            irradiation,
            day16_irradiation,
        )
        interval_method = (
            "selected Y-scale point model with HC3 parameter covariance and "
            "irradiation-scaled conditional residual variance"
        )
    else:
        interval = _regression_interval(
            selected["spec"], selected["x"], y, selected["fit"], selected["day16_x"]
        )
        bootstrap = _bootstrap_interval_sensitivity(
            selected["spec"], selected["x"], y, selected["fit"], selected["day16_x"]
        )
        interval_method = "small-sample Student-t regression interval on Y"

    loo_rows: list[dict[str, Any]] = []
    for evaluation in evaluations:
        for day_index, (prediction, error) in enumerate(
            zip(evaluation["loo_predictions"], evaluation["loo_errors"]), start=1
        ):
            loo_rows.append(
                {
                    "candidate": evaluation["spec"].name,
                    "day": day_index,
                    "observed_kwh": float(y[day_index - 1]),
                    "predicted_kwh": float(prediction),
                    "error_kwh": float(error),
                    "absolute_error_kwh": float(abs(error)),
                }
            )

    comparison = [_candidate_summary(evaluation) for evaluation in evaluations]
    for row in comparison:
        row["in_one_standard_error_set"] = row["candidate"] in {
            item["spec"].name for item in one_se_set
        }
        row["selected_by_contract"] = row["candidate"] == selected["spec"].name

    interval["confidence_lower"] = max(0.0, interval["confidence_lower"])
    interval["prediction_lower"] = max(0.0, interval["prediction_lower"])
    return {
        "candidate_comparison": comparison,
        "loo_predictions": loo_rows,
        "selection": {
            "selected_candidate": selected["spec"].name,
            "selected_family": selected["spec"].family,
            "selection_status": "technical selection under frozen validation contract; not an Accepted Decision",
            "minimum_mae_candidate": minimum["spec"].name,
            "minimum_mae_kwh": minimum["mae"],
            "mae_standard_error_kwh": mae_standard_error,
            "one_standard_error_threshold_kwh": one_se_threshold,
            "one_standard_error_candidates": [item["spec"].name for item in one_se_set],
            "temperature_reference_c": temperature_ref,
            "wind_reference_m_s": wind_ref,
            "coefficients": {
                name: float(value)
                for name, value in zip(selected["spec"].parameter_names, selected["fit"]["coefficients"])
            },
            "day16_point_from_selected_fit_kwh": float(
                selected["day16_x"] @ selected["fit"]["coefficients"]
            ),
        },
        "day16_forecast": {
            "candidate": selected["spec"].name,
            "weather": dict(data.day16_weather),
            "point_kwh": interval["point"],
            "confidence_95_kwh": [interval["confidence_lower"], interval["confidence_upper"]],
            "prediction_95_kwh": [interval["prediction_lower"], interval["prediction_upper"]],
            "degrees_of_freedom": interval["degrees_of_freedom"],
            "interval_method": interval_method,
            "point_model_coefficients": {
                name: float(value)
                for name, value in zip(selected["spec"].parameter_names, selected["fit"]["coefficients"])
            },
            "point_model_definition": "selected candidate refit once on all 15 Y-scale observations",
            "interval_point_locked_to_selected_model": True,
            "bootstrap_sensitivity": bootstrap,
            "absolute_residual_irradiation_spearman": {
                "raw_scale": float(raw_correlation.statistic),
                "normalized_y_over_h_scale": float(normalized_correlation.statistic),
            },
            "uncertainty_scope": {
                "propagated": [
                    "selected-model parameter estimation uncertainty",
                    "conditional day-level residual variability at fixed day-16 irradiation",
                ],
                "not_propagated": [
                    "day-16 weather forecast input uncertainty",
                    "candidate-model selection uncertainty",
                    "future fault-state changes, curtailment, or inverter events",
                ],
            },
            "coverage_claim": "diagnostic only; 15 days cannot prove exact 95% calibration",
        },
    }
