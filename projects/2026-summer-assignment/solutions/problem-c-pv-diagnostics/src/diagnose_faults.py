"""Task 1: official deviation-threshold diagnosis and non-overriding shading screen."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from data_io import ProblemData


NORMAL = "正常"
MICROCRACK = "隐裂"
HOTSPOT = "热斑"
OUTSIDE_RULE = "超出题面定义"


def classify_deviation(deviation_pct: float) -> str:
    """Apply the statement's exact percent-scale boundaries without using labels."""

    value = float(deviation_pct)
    if abs(value) <= 5.0:
        return NORMAL
    if -15.0 <= value < -5.0:
        return MICROCRACK
    if value < -15.0:
        return HOTSPOT
    return OUTSIDE_RULE


def _mad(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    median = float(np.median(values))
    return float(np.median(np.abs(values - median)))


def _screen_against_reference(
    q: np.ndarray,
    component_index: int,
    reference_indices: np.ndarray,
) -> tuple[float, float, bool, int]:
    if reference_indices.size < 5:
        raise ValueError("shading reference requires at least five normal modules")
    peer_daily_median = np.median(q[reference_indices, :], axis=0)
    if np.any(peer_daily_median <= 0) or np.any(q[component_index, :] <= 0):
        return float("nan"), float("nan"), False, 0

    log_relative = np.log(q[component_index, :] / peer_daily_median)
    centered = log_relative - np.median(log_relative)
    dispersion = 1.4826 * _mad(log_relative)

    normal_dispersions: list[float] = []
    pooled_centered: list[float] = []
    for peer_index in reference_indices:
        peer_log_relative = np.log(q[peer_index, :] / peer_daily_median)
        peer_centered = peer_log_relative - np.median(peer_log_relative)
        normal_dispersions.append(1.4826 * _mad(peer_log_relative))
        pooled_centered.extend(peer_centered.tolist())

    normal_d = np.asarray(normal_dispersions)
    cutoff = float(np.median(normal_d) + 3.0 * 1.4826 * _mad(normal_d))
    residual_scale = 1.4826 * _mad(np.asarray(pooled_centered))
    if residual_scale <= np.finfo(float).eps:
        anomaly_mask = np.abs(centered) > np.finfo(float).eps
    else:
        anomaly_mask = np.abs(centered) > 3.0 * residual_scale
    anomaly_indices = np.flatnonzero(anomaly_mask)
    same_direction = False
    time_local = False
    if anomaly_indices.size >= 2:
        signs = np.sign(centered[anomaly_indices])
        same_direction = bool(np.sum(signs > 0) >= 2 or np.sum(signs < 0) >= 2)
        time_local = bool(np.any(np.diff(anomaly_indices) == 1))
    flagged = bool(dispersion > cutoff and anomaly_indices.size >= 2 and (same_direction or time_local))
    return dispersion, cutoff, flagged, int(anomaly_indices.size)


def diagnose_components(data: ProblemData) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    classes = [classify_deviation(value) for value in data.deviation_pct]
    normal_indices = np.flatnonzero(np.asarray(classes) == NORMAL)
    if normal_indices.size < 5:
        raise ValueError("at least five provisionally normal modules are required for shading screening")

    irradiation = np.asarray(
        [row["irradiation_kwh_m2"] for row in data.historical_weather], dtype=float
    )
    if np.any(irradiation <= 0):
        raise ValueError("shading screen requires positive historical irradiation")
    q = data.generation / irradiation[np.newaxis, :]

    geometry_groups: dict[tuple[float, float], list[int]] = defaultdict(list)
    for index in normal_indices:
        parameter = data.parameters[index]
        geometry_groups[(parameter["azimuth_deg"], parameter["tilt_deg"])].append(int(index))

    rows: list[dict[str, Any]] = []
    for index, component_id in enumerate(data.component_ids):
        parameter = data.parameters[index]
        geometry_key = (parameter["azimuth_deg"], parameter["tilt_deg"])
        geometry_reference = np.asarray(geometry_groups.get(geometry_key, []), dtype=int)
        if geometry_reference.size < 5:
            geometry_reference = normal_indices

        config_d, config_cutoff, config_flag, config_anomalies = _screen_against_reference(
            q, index, geometry_reference
        )
        global_d, global_cutoff, global_flag, global_anomalies = _screen_against_reference(
            q, index, normal_indices
        )
        if config_flag and global_flag:
            shading_status = "疑似遮挡"
        elif config_flag != global_flag:
            shading_status = "筛查不稳定"
        else:
            shading_status = "未发现疑似遮挡"

        rows.append(
            {
                "component_id": component_id,
                "deviation_pct": float(data.deviation_pct[index]),
                "fault_class": classes[index],
                "shading_suspect": bool(config_flag and global_flag),
                "shading_screen_status": shading_status,
                "config_dispersion": config_d,
                "config_cutoff": config_cutoff,
                "config_anomaly_days": config_anomalies,
                "global_dispersion": global_d,
                "global_cutoff": global_cutoff,
                "global_anomaly_days": global_anomalies,
                "string": parameter["string"],
                "azimuth_deg": parameter["azimuth_deg"],
                "tilt_deg": parameter["tilt_deg"],
                "service_years": parameter["service_years"],
                "reference_label": data.reference_labels[index],
                "reference_match": classes[index] == data.reference_labels[index],
            }
        )

    class_counts = {label: classes.count(label) for label in (NORMAL, MICROCRACK, HOTSPOT, OUTSIDE_RULE)}
    agreement_count = sum(row["reference_match"] for row in rows)
    summary = {
        "component_count": len(rows),
        "class_counts": class_counts,
        "classification_complete_rate": 1.0 - class_counts[OUTSIDE_RULE] / len(rows),
        "reference_agreement_count": agreement_count,
        "reference_agreement_rate": agreement_count / len(rows),
        "shading_suspect_count": sum(row["shading_suspect"] for row in rows),
        "shading_unstable_count": sum(row["shading_screen_status"] == "筛查不稳定" for row in rows),
        "causal_interpretation_allowed": False,
    }
    return rows, summary


def summarize_distribution(rows: list[dict[str, Any]], group_field: str) -> list[dict[str, Any]]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row[group_field]].append(row)
    output: list[dict[str, Any]] = []
    for group, members in sorted(grouped.items(), key=lambda item: str(item[0])):
        denominator = len(members)
        for fault_class in (NORMAL, MICROCRACK, HOTSPOT, OUTSIDE_RULE):
            count = sum(member["fault_class"] == fault_class for member in members)
            output.append(
                {
                    "group_field": group_field,
                    "group": group,
                    "fault_class": fault_class,
                    "group_total": denominator,
                    "count": count,
                    "rate": count / denominator,
                    "causal_interpretation_allowed": False,
                }
            )
    return output
