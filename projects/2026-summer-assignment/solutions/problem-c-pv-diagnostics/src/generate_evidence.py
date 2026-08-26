"""Generate the minimum paper evidence tables and figures from frozen results.

This module does not refit a model or change any accepted semantic decision.
It only creates paper-facing views from the existing structured results.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager, ticker
from matplotlib.lines import Line2D


SOLUTION_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_ROOT = SOLUTION_ROOT / "results"
DEFAULT_FIGURES_ROOT = SOLUTION_ROOT / "figures"

CLASS_ORDER = ("正常", "隐裂", "热斑")
CLASS_COLORS = {
    "正常": "#56B4E9",      # Okabe-Ito blue
    "隐裂": "#E69F00",      # Okabe-Ito orange
    "热斑": "#CC79A7",      # Okabe-Ito reddish purple
}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if value is None else value for key, value in row.items()})


def _as_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _format_reasons(value: str) -> str:
    if value.strip() in {"", "[]"}:
        return "无"
    try:
        reasons = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value
    return "；".join(str(reason) for reason in reasons)


def _configure_matplotlib() -> str:
    candidates = [
        Path("C:/Windows/Fonts/Noto Sans SC (TrueType).otf"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/Deng.ttf"),
    ]
    for font_path in candidates:
        if font_path.is_file():
            font_manager.fontManager.addfont(str(font_path))
            font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
            plt.rcParams.update(
                {
                    "font.family": font_name,
                    "axes.unicode_minus": False,
                    "font.size": 9,
                    "axes.titlesize": 12,
                    "axes.labelsize": 10,
                    "xtick.labelsize": 8.5,
                    "ytick.labelsize": 8.5,
                    "legend.fontsize": 8.5,
                    "figure.dpi": 100,
                    "savefig.dpi": 300,
                    "pdf.fonttype": 42,
                    "ps.fonttype": 42,
                }
            )
            return font_name
    plt.rcParams.update({"axes.unicode_minus": False, "savefig.dpi": 300})
    return "DejaVu Sans"


def _paper_tables(results_root: Path, evidence_root: Path) -> list[str]:
    task1_summary = _read_json(results_root / "task-1" / "fault_summary.json")
    task1_distribution = _read_csv(results_root / "task-1" / "fault_distributions.csv")
    shading = _read_csv(results_root / "task-1" / "shading_screen.csv")
    candidate_metrics = _read_csv(results_root / "task-2" / "candidate_metrics.csv")
    selected_model = _read_json(results_root / "task-2" / "selected_model.json")
    day16_forecast = _read_json(results_root / "task-2" / "day16_forecast.json")
    ranking = _read_csv(results_root / "task-3" / "repair_ranking.csv")
    improvement = _read_json(results_root / "task-3" / "improvement_summary.json")

    class_counts = task1_summary["class_counts"]
    diagnosis_rows = [
        {
            "metric": f"正式分类数量_{label}",
            "value": class_counts[label],
            "unit": "组件",
            "scope": "Task 1正式阈值分类",
        }
        for label in ("正常", "隐裂", "热斑", "超出题面定义")
    ]
    diagnosis_rows.extend(
        [
            {
                "metric": "分类完整率",
                "value": f"{100 * task1_summary['classification_complete_rate']:.1f}",
                "unit": "%",
                "scope": "正式三分类定义域",
            },
            {
                "metric": "参考示例一致率",
                "value": f"{100 * task1_summary['reference_agreement_rate']:.1f}",
                "unit": "%",
                "scope": "分类完成后的独立核验",
            },
            {
                "metric": "疑似遮挡数量",
                "value": task1_summary["shading_suspect_count"],
                "unit": "组件",
                "scope": "辅助筛查，不覆盖正式类别",
            },
            {
                "metric": "筛查不稳定数量",
                "value": task1_summary["shading_unstable_count"],
                "unit": "组件",
                "scope": "辅助筛查，不覆盖正式类别",
            },
        ]
    )
    _write_csv(
        evidence_root / "task1_diagnosis_summary.csv",
        diagnosis_rows,
        ["metric", "value", "unit", "scope"],
    )

    statuses = ("未发现疑似遮挡", "筛查不稳定", "疑似遮挡")
    cross_tab: list[dict[str, Any]] = []
    for fault_class in ("正常", "隐裂", "热斑"):
        members = [row for row in shading if row["fault_class"] == fault_class]
        row = {"fault_class": fault_class}
        for status in statuses:
            row[status] = sum(item["shading_screen_status"] == status for item in members)
        row["total"] = len(members)
        cross_tab.append(row)
    total_row = {"fault_class": "合计"}
    for status in statuses:
        total_row[status] = sum(row[status] for row in cross_tab)
    total_row["total"] = sum(row["total"] for row in cross_tab)
    cross_tab.append(total_row)
    _write_csv(
        evidence_root / "task1_shading_screen_cross_tab.csv",
        cross_tab,
        ["fault_class", *statuses, "total"],
    )

    candidate_rows: list[dict[str, Any]] = []
    for row in candidate_metrics:
        candidate_rows.append(
            {
                "candidate": row["candidate"],
                "eligible": "是" if _as_bool(row["eligible"]) else "否",
                "eligibility_reasons": _format_reasons(row["eligibility_reasons"]),
                "loo_mae_kwh": f"{float(row['mae_kwh']):.6f}",
                "loo_rmse_kwh": f"{float(row['rmse_kwh']):.6f}",
                "max_absolute_error_kwh": f"{float(row['max_absolute_error_kwh']):.6f}",
                "cv_r2": f"{float(row['cv_r2']):.8f}",
                "full_r2": f"{float(row['full_r2']):.8f}",
                "in_one_standard_error_set": "是" if _as_bool(row["in_one_standard_error_set"]) else "否",
                "selected_by_contract": "是" if _as_bool(row["selected_by_contract"]) else "否",
            }
        )
    _write_csv(
        evidence_root / "task2_candidate_comparison.csv",
        candidate_rows,
        [
            "candidate",
            "eligible",
            "eligibility_reasons",
            "loo_mae_kwh",
            "loo_rmse_kwh",
            "max_absolute_error_kwh",
            "cv_r2",
            "full_r2",
            "in_one_standard_error_set",
            "selected_by_contract",
        ],
    )

    ci_low, ci_high = day16_forecast["confidence_95_kwh"]
    pi_low, pi_high = day16_forecast["prediction_95_kwh"]
    bootstrap = day16_forecast["bootstrap_sensitivity"]
    forecast_rows = [
        {
            "metric": "day16点预测",
            "point_kwh": f"{day16_forecast['point_kwh']:.6f}",
            "lower_kwh": "",
            "upper_kwh": "",
            "scope": f"selected {selected_model['selected_candidate']}全15日原尺度最终拟合",
        },
        {
            "metric": "95%期望值置信区间",
            "point_kwh": "",
            "lower_kwh": f"{ci_low:.6f}",
            "upper_kwh": f"{ci_high:.6f}",
            "scope": "条件性参数不确定性；非精确覆盖证明",
        },
        {
            "metric": "95%单日预测区间",
            "point_kwh": "",
            "lower_kwh": f"{pi_low:.6f}",
            "upper_kwh": f"{pi_high:.6f}",
            "scope": "条件性参数与日级残差不确定性",
        },
        {
            "metric": "bootstrap敏感性_期望值区间",
            "point_kwh": "",
            "lower_kwh": f"{bootstrap['confidence_lower']:.6f}",
            "upper_kwh": f"{bootstrap['confidence_upper']:.6f}",
            "scope": "同一selected candidate的原尺度重拟合",
        },
        {
            "metric": "bootstrap敏感性_预测区间",
            "point_kwh": "",
            "lower_kwh": f"{bootstrap['prediction_lower']:.6f}",
            "upper_kwh": f"{bootstrap['prediction_upper']:.6f}",
            "scope": "同一selected candidate的原尺度重拟合",
        },
    ]
    _write_csv(
        evidence_root / "task2_day16_forecast.csv",
        forecast_rows,
        ["metric", "point_kwh", "lower_kwh", "upper_kwh", "scope"],
    )

    ranked = sorted(ranking, key=lambda row: int(row["rank"]))
    top10_rows: list[dict[str, Any]] = []
    cumulative = 0.0
    for row in ranked[:10]:
        cumulative += float(row["recoverable_loss_kwh_day"])
        top10_rows.append(
            {
                "rank": row["rank"],
                "component_id": row["component_id"],
                "fault_class": row["fault_class"],
                "deviation_pct": row["deviation_pct"],
                "normal_counterfactual_kwh_day": f"{float(row['normal_counterfactual_kwh_day']):.6f}",
                "recoverable_loss_kwh_day": f"{float(row['recoverable_loss_kwh_day']):.6f}",
                "loss_rounding_lower_kwh_day": f"{float(row['loss_rounding_lower_kwh_day']):.6f}",
                "loss_rounding_upper_kwh_day": f"{float(row['loss_rounding_upper_kwh_day']):.6f}",
                "cumulative_gain_kwh_day": f"{cumulative:.6f}",
            }
        )
    _write_csv(
        evidence_root / "task3_top10_repairs.csv",
        top10_rows,
        [
            "rank",
            "component_id",
            "fault_class",
            "deviation_pct",
            "normal_counterfactual_kwh_day",
            "recoverable_loss_kwh_day",
            "loss_rounding_lower_kwh_day",
            "loss_rounding_upper_kwh_day",
            "cumulative_gain_kwh_day",
        ],
    )

    supplementary = improvement["day16_supplementary"]
    gain_rows = [
        {
            "metric": "历史平均每日增发量",
            "value": f"{improvement['historical_mean_gain_kwh_day']:.6f}",
            "lower": "",
            "upper": "",
            "unit": "kWh/day",
            "scope": "DP-C-002主排序口径",
        },
        {
            "metric": "当前全站历史平均发电量",
            "value": f"{improvement['current_station_mean_kwh_day']:.6f}",
            "lower": "",
            "upper": "",
            "unit": "kWh/day",
            "scope": "Task 3比例缩放分母",
        },
        {
            "metric": "修复后全站历史平均发电量",
            "value": f"{improvement['post_repair_station_mean_kwh_day']:.6f}",
            "lower": "",
            "upper": "",
            "unit": "kWh/day",
            "scope": "加性修复假设下",
        },
        {
            "metric": "历史相对提升率",
            "value": f"{100 * improvement['historical_relative_improvement']:.6f}",
            "lower": "",
            "upper": "",
            "unit": "%",
            "scope": "加性修复假设下",
        },
        {
            "metric": "day16补充期望增发量",
            "value": f"{supplementary['expected_gain_kwh']:.6f}",
            "lower": "",
            "upper": "",
            "unit": "kWh",
            "scope": "历史增益×day16站级预测/历史站均值",
        },
        {
            "metric": "day16补充95%置信区间",
            "value": "",
            "lower": f"{supplementary['confidence_95_kwh'][0]:.6f}",
            "upper": f"{supplementary['confidence_95_kwh'][1]:.6f}",
            "unit": "kWh",
            "scope": "仅传播Task 2条件参数区间",
        },
        {
            "metric": "day16补充95%预测区间",
            "value": "",
            "lower": f"{supplementary['prediction_95_kwh'][0]:.6f}",
            "upper": f"{supplementary['prediction_95_kwh'][1]:.6f}",
            "unit": "kWh",
            "scope": "仅传播Task 2条件日级残差区间",
        },
        {
            "metric": "第10名中心损失",
            "value": f"{improvement['rank_10_loss_kwh_day']:.6f}",
            "lower": "",
            "upper": "",
            "unit": "kWh/day",
            "scope": "排序截止点",
        },
        {
            "metric": "第11名中心损失",
            "value": f"{improvement['rank_11_loss_kwh_day']:.6f}",
            "lower": "",
            "upper": "",
            "unit": "kWh/day",
            "scope": "排序截止点",
        },
    ]
    _write_csv(
        evidence_root / "task3_gain_summary.csv",
        gain_rows,
        ["metric", "value", "lower", "upper", "unit", "scope"],
    )

    return [
        "task1_diagnosis_summary.csv",
        "task1_shading_screen_cross_tab.csv",
        "task2_candidate_comparison.csv",
        "task2_day16_forecast.csv",
        "task3_top10_repairs.csv",
        "task3_gain_summary.csv",
    ]


def _save_figure(fig: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_task1(results_root: Path, figures_root: Path) -> str:
    rows = [
        row
        for row in _read_csv(results_root / "task-1" / "fault_distributions.csv")
        if row["group_field"] == "string" and row["fault_class"] in CLASS_ORDER
    ]
    strings = sorted({row["group"] for row in rows}, key=lambda value: int(value.removeprefix("STR")))
    values = {
        (row["group"], row["fault_class"]): float(row["rate"])
        for row in rows
    }
    totals = {row["group"]: int(row["group_total"]) for row in rows}

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    y = np.arange(len(strings))
    left = np.zeros(len(strings))
    for fault_class in CLASS_ORDER:
        widths = np.asarray([values[(string, fault_class)] for string in strings])
        ax.barh(
            y,
            widths,
            left=left,
            height=0.68,
            color=CLASS_COLORS[fault_class],
            label=fault_class,
            edgecolor="white",
            linewidth=0.5,
        )
        left += widths
    ax.set_yticks(y, strings)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.12)
    ax.xaxis.set_major_formatter(ticker.PercentFormatter(1.0))
    ax.set_xlabel("组内构成（%）")
    ax.set_ylabel("组串")
    ax.set_title("正式故障类别在各组串中的构成", pad=28)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for y_value, string in zip(y, strings):
        ax.text(1.015, y_value, f"n={totals[string]}", va="center", ha="left", fontsize=8)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.98),
        ncol=3,
        frameon=False,
        handlelength=1.2,
        columnspacing=1.5,
    )
    fig.text(
        0.01,
        0.01,
        "仅展示DP-C-001正式三分类；各组串样本数已标注，分布不作因果解释。",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#555555",
    )
    fig.subplots_adjust(left=0.12, right=0.88, top=0.77, bottom=0.13)
    path = figures_root / "evidence_task1_fault_distribution.png"
    _save_figure(fig, path)
    return path.name


def _plot_task2(results_root: Path, figures_root: Path) -> str:
    weather = _read_csv(results_root.parent / "data" / "derived" / "station_daily_weather.csv")
    weather = [row for row in weather if int(row["day"]) <= 15]
    loo = [
        row
        for row in _read_csv(results_root / "task-2" / "loo_predictions.csv")
        if row["candidate"] == "M0"
    ]
    loo.sort(key=lambda row: int(row["day"]))
    forecast = _read_json(results_root / "task-2" / "day16_forecast.json")
    point = float(forecast["point_kwh"])
    ci_low, ci_high = [float(value) for value in forecast["confidence_95_kwh"]]
    pi_low, pi_high = [float(value) for value in forecast["prediction_95_kwh"]]
    days = np.arange(1, 16)
    observed = np.asarray([float(row["station_generation_kwh"]) for row in weather])
    predicted = np.asarray([float(row["predicted_kwh"]) for row in loo])

    fig, (ax, ax_zoom) = plt.subplots(
        1,
        2,
        figsize=(7.2, 4.8),
        gridspec_kw={"width_ratios": [2.25, 1.0], "wspace": 0.34},
    )
    actual_line, = ax.plot(
        days,
        observed,
        color="#0072B2",
        marker="o",
        linewidth=1.8,
        markersize=4.5,
        label="实际全站发电量",
    )
    loo_line, = ax.plot(
        days,
        predicted,
        color="#D55E00",
        marker="s",
        markerfacecolor="white",
        linestyle="--",
        linewidth=1.5,
        markersize=4.2,
        label="M0逐日留一预测",
    )
    ax.set_xlim(0.5, 15.5)
    ax.set_ylim(0, max(float(np.max(observed)), pi_high) * 1.1)
    ax.set_xticks(range(1, 16))
    ax.set_xlabel("天数")
    ax.set_ylabel("全站日发电量（kWh）")
    ax.set_title("历史观测与M0逐日留一预测")
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    pi_line = ax_zoom.vlines(0, pi_low, pi_high, color="#777777", linewidth=9, alpha=0.55)
    ci_line = ax_zoom.vlines(0, ci_low, ci_high, color="#009E73", linewidth=4.0)
    point_handle = ax_zoom.scatter([0], [point], color="#000000", marker="*", s=110, zorder=5)
    ax_zoom.hlines([pi_low, pi_high], -0.10, 0.10, color="#777777", linewidth=1.0)
    ax_zoom.hlines([ci_low, ci_high], -0.10, 0.10, color="#009E73", linewidth=1.0)
    ax_zoom.text(0.13, pi_high, f"PI [{pi_low:.2f}, {pi_high:.2f}]", va="center", fontsize=7.5)
    ax_zoom.text(0.13, ci_high, f"CI [{ci_low:.2f}, {ci_high:.2f}]", va="center", fontsize=7.5)
    ax_zoom.text(0.13, point, f"点 {point:.2f}", va="center", fontsize=7.5)
    zoom_margin = 0.12
    ax_zoom.set_xlim(-0.35, 0.95)
    ax_zoom.set_ylim(pi_low - zoom_margin, pi_high + zoom_margin)
    ax_zoom.set_xticks([])
    ax_zoom.set_ylabel("day16发电量（kWh）")
    ax_zoom.set_title("day16区间放大")
    ax_zoom.grid(axis="y", color="#D9D9D9", linewidth=0.7, alpha=0.8)
    ax_zoom.set_axisbelow(True)
    ax_zoom.spines["top"].set_visible(False)
    ax_zoom.spines["right"].set_visible(False)
    legend_handles = [
        actual_line,
        loo_line,
        Line2D([0], [0], color="#000000", marker="*", linestyle="None", markersize=9, label="day16点预测"),
        Line2D([0], [0], color="#009E73", linewidth=4, label="95%置信区间"),
        Line2D([0], [0], color="#777777", linewidth=8, alpha=0.55, label="95%预测区间"),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.98),
        ncol=3,
        frameon=False,
        columnspacing=1.2,
    )
    fig.suptitle("M0逐日留一预测与第16天条件区间", y=0.90)
    fig.text(
        0.01,
        0.01,
        "历史点为逐日留一结果；第16天无实测值。区间为条件性小样本区间，不宣称精确95%覆盖。",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#555555",
    )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.78, bottom=0.15)
    path = figures_root / "evidence_task2_forecast_validation.png"
    _save_figure(fig, path)
    return path.name


def _plot_task3(results_root: Path, figures_root: Path) -> str:
    rows = sorted(
        _read_csv(results_root / "task-3" / "repair_ranking.csv"),
        key=lambda row: int(row["rank"]),
    )
    ranks = np.asarray([int(row["rank"]) for row in rows])
    losses = np.asarray([float(row["recoverable_loss_kwh_day"]) for row in rows])
    lower = np.asarray([float(row["loss_rounding_lower_kwh_day"]) for row in rows])
    upper = np.asarray([float(row["loss_rounding_upper_kwh_day"]) for row in rows])
    selected = ranks <= 10
    y = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(7.2, 8.0))
    for mask, color, label in (
        (selected, "#0072B2", "top-10"),
        (~selected, "#999999", "未入选故障组件"),
    ):
        ax.errorbar(
            losses[mask],
            y[mask],
            xerr=np.vstack((losses[mask] - lower[mask], upper[mask] - losses[mask])),
            fmt="o",
            color=color,
            ecolor="#555555",
            elinewidth=0.7,
            capsize=2.0,
            markersize=4.8,
            label=label,
        )
    rank10_loss = losses[9]
    ax.axvline(rank10_loss, color="#D55E00", linestyle="--", linewidth=1.2)
    ax.text(
        rank10_loss + 0.008,
        0.5,
        f"第10名中心损失={rank10_loss:.3f}",
        color="#D55E00",
        fontsize=8,
        ha="left",
        va="bottom",
    )
    ax.set_yticks(y, [f"{row['component_id']}（{row['rank']}）" for row in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, max(upper) * 1.1)
    ax.set_xlabel("历史平均可恢复损失（kWh/day）")
    ax.set_ylabel("故障组件（排名）")
    ax.set_title("故障组件维修收益排序与top-10截止点")
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower right", frameon=False)
    fig.text(
        0.01,
        0.005,
        "点为中心估计；误差线为偏差率显示精度±0.05个百分点的端点敏感性。排序依据为DP-C-002历史平均绝对损失。",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#555555",
    )
    fig.subplots_adjust(left=0.20, right=0.96, top=0.95, bottom=0.09)
    path = figures_root / "evidence_task3_repair_ranking.png"
    _save_figure(fig, path)
    return path.name


def generate_evidence(results_root: Path, figures_root: Path) -> dict[str, Any]:
    _configure_matplotlib()
    evidence_root = results_root / "evidence"
    table_names = _paper_tables(results_root, evidence_root)
    figure_names = [
        _plot_task1(results_root, figures_root),
        _plot_task2(results_root, figures_root),
        _plot_task3(results_root, figures_root),
    ]
    manifest = {
        "source": "frozen structured results; no model refit",
        "tables": table_names,
        "figures": figure_names,
        "paper_generated": False,
        "claims": {
            figure_names[0]: "Task 1 formal fault distribution by string; descriptive only",
            figure_names[1]: "Task 2 M0 held-out historical prediction and day16 conditional intervals",
            figure_names[2]: "Task 3 historical loss ranking, top-10 cutoff, and rounding sensitivity",
        },
    }
    evidence_root.mkdir(parents=True, exist_ok=True)
    with (evidence_root / "evidence_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--figures-root", type=Path, default=DEFAULT_FIGURES_ROOT)
    args = parser.parse_args()
    manifest = generate_evidence(args.results_root, args.figures_root)
    print(f"generated {len(manifest['tables'])} evidence tables and {len(manifest['figures'])} figures")


if __name__ == "__main__":
    main()
