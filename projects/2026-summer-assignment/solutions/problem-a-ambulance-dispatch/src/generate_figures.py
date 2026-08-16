# 根据冻结结果生成A题三项任务的正式论文图及灰度预览。
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors
from matplotlib.lines import Line2D
from PIL import Image
from scipy.interpolate import PchipInterpolator

from ambulance_model import (
    intraday_density,
    problem_statement_path,
    read_problem,
    solve_q1,
)


SKILL_ROOT = Path(r"C:\Users\AA\.codex\skills\math-modeling")
FIGURE_TOOLS = SKILL_ROOT / "tools" / "figure" / "scripts"
sys.path.insert(0, str(FIGURE_TOOLS))
from export_figure import export_figure  # noqa: E402
from setup_style import setup_style  # noqa: E402
from visual_qa import audit_layout  # noqa: E402


BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"
PURPLE = "#CC79A7"
GRAY = "#6B7280"
SITE_COLORS = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9"]


def vector_heatmap(
    ax: plt.Axes,
    values: np.ndarray,
    cmap: str,
    vmin: float,
    vmax: float,
) -> plt.cm.ScalarMappable:
    normalization = colors.Normalize(vmin=vmin, vmax=vmax)
    colormap = plt.get_cmap(cmap)
    rows, columns = values.shape
    for row in range(rows):
        for column in range(columns):
            ax.add_patch(
                plt.Rectangle(
                    (column - 0.5, row - 0.5),
                    1.0,
                    1.0,
                    facecolor=colormap(normalization(values[row, column])),
                    edgecolor="none",
                )
            )
    ax.set_xlim(-0.5, columns - 0.5)
    ax.set_ylim(rows - 0.5, -0.5)
    return plt.cm.ScalarMappable(norm=normalization, cmap=colormap)


def keep_colorbar_vector(colorbar) -> None:
    if colorbar.solids is not None:
        colorbar.solids.set_rasterized(False)


def policy_label(candidate: str) -> str:
    labels = {
        "A": "策略A（就近派车）",
        "B_beta4_delta2": "策略B（保护性派车）",
        "C_r001000_tau7": "策略C（S3固定备用）",
    }
    return labels.get(candidate, candidate)


def q3_evidence_sources() -> dict[str, str]:
    return {
        "raw_q3_incident_load": "scenarios.csv",
        "process_q3_duration_zone": "response_surfaces.csv",
        "result_q3_response_curve": "response_surfaces.csv",
        "result_q3_paired_effect": "scoped_paired_response_surfaces.csv",
        "result_q3_external_support": "external-support/external_support_citywide.csv",
    }


def save(fig: plt.Figure, figures: Path, name: str, size: tuple[float, float]) -> None:
    paths = export_figure(
        fig,
        str(figures / name),
        formats=["svg", "png"],
        size_inches=size,
        dpi=300,
        grayscale_preview=False,
        tight=False,
    )
    png_path = figures / f"{name}.png"
    grayscale_path = figures / f"{name}_grayscale.png"
    with Image.open(png_path) as image:
        image.convert("L").save(grayscale_path, dpi=(300, 300))
    paths.append(str(grayscale_path))
    qa_dir = figures / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        preview = Path(path)
        if preview.suffix.lower() == ".svg":
            content = preview.read_text(encoding="utf-8")
            preview.write_text(
                "\n".join(line.rstrip() for line in content.splitlines()) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        if preview.name.endswith("_grayscale.png"):
            preview.replace(qa_dir / preview.name)
    plt.close(fig)


def q1_tables(project_root: Path) -> tuple[object, dict[str, object]]:
    data = read_problem(problem_statement_path(project_root))
    result = solve_q1(data)
    out = project_root / "results" / "task-1"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "zone_id": data.zone_ids,
            "zone_name": data.zone_names,
            "x_km": data.zone_xy[:, 0],
            "y_km": data.zone_xy[:, 1],
            "area_km2": data.area,
            "population_10k": data.population,
            "daily_calls": data.demand,
            "daily_calls_per_km2": data.demand_density,
            "nearest_hospital_km": data.hospital_distance,
            "nearest_site_distance_km": data.distance.min(axis=1),
        }
    ).to_csv(out / "zone_input.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        {
            "site": data.site_ids,
            "x_km": data.site_xy[:, 0],
            "y_km": data.site_xy[:, 1],
            "max_vehicles": data.site_caps,
            "vehicles": result["vehicles"],
            "daily_capacity": 12 * result["vehicles"],
            "assigned_load": result["loads"],
        }
    ).to_csv(out / "site_solution.csv", index=False, encoding="utf-8-sig")
    assignment = pd.DataFrame(result["assignment"], index=data.zone_ids, columns=data.site_ids)
    assignment.index.name = "zone_id"
    assignment.to_csv(out / "assignment.csv", encoding="utf-8-sig")
    summary = {
        key: value.tolist() if isinstance(value, np.ndarray) else value
        for key, value in result.items()
        if key != "assignment"
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data, result


def raw_q1_spatial(data, figures: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.3, 4.5))
    size = 35 + 8 * data.demand
    ax.scatter(data.zone_xy[:, 0], data.zone_xy[:, 1], s=size, c=BLUE, alpha=0.50, edgecolor="white")
    ax.scatter(data.site_xy[:, 0], data.site_xy[:, 1], s=95, c=ORANGE, marker="s", edgecolor="black")
    for i, (x, y) in enumerate(data.zone_xy):
        ax.annotate(f"R{data.zone_ids[i]}", (x, y), xytext=(5, 5), textcoords="offset points", fontsize=7)
    for i, (x, y) in enumerate(data.site_xy):
        ax.annotate(data.site_ids[i], (x, y), xytext=(-10, -13), textcoords="offset points", fontsize=7)
    ax.set_xlabel("X 坐标（km）")
    ax.set_ylabel("Y 坐标（km）")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(
        handles=[
            Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, alpha=0.5, label="需求区（大小表示呼叫量）"),
            Line2D([0], [0], marker="s", color="none", markerfacecolor=ORANGE, markeredgecolor="black", label="候选站点"),
        ],
        frameon=False,
        loc="upper right",
    )
    save(fig, figures, "raw_q1_spatial", (6.3, 4.5))


def raw_q2_intensity(data, figures: Path) -> None:
    hours = np.linspace(0, 24, 24 * 12 + 1)
    total = 140 * np.asarray(intraday_density(hours))
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    ax.plot(hours, total, color=BLUE, linewidth=1.5)
    ax.fill_between(hours, total, color=BLUE, alpha=0.18)
    ax.axhline(140 / 24, color=GRAY, linestyle="--", linewidth=0.8, label="均匀到达基线")
    ax.set_xlim(0, 24)
    ax.set_xticks(np.arange(0, 25, 3))
    ax.set_xlabel("时刻（h）")
    ax.set_ylabel("全市呼叫强度（次/h）")
    ax.legend(frameon=False)
    save(fig, figures, "raw_q2_nhpp_intensity", (6.3, 3.6))


def process_q1_heatmap(data, result: dict[str, object], figures: Path) -> None:
    assignment = np.asarray(result["assignment"])
    fig, ax = plt.subplots(figsize=(6.3, 4.2))
    y = np.arange(len(data.zone_ids))
    left = np.zeros(len(data.zone_ids))
    for j, site_id in enumerate(data.site_ids):
        values = assignment[:, j]
        ax.barh(y, values, left=left, color=SITE_COLORS[j], label=site_id, height=0.66)
        for i, amount in enumerate(values):
            if amount <= 1e-8:
                continue
            ax.text(left[i] + amount / 2, i, f"{amount:.0f}", ha="center", va="center",
                    fontsize=7, color="white" if amount >= 5 else "black")
        left += values
    ax.set_yticks(y, [f"R{i}" for i in data.zone_ids])
    ax.set_xlabel("日分配呼叫量（次/日）")
    ax.set_ylabel("需求区")
    ax.invert_yaxis()
    ax.set_xlim(0, max(data.demand) * 1.08)
    ax.legend(title="服务站点", frameon=False, ncols=6, loc="lower center",
              bbox_to_anchor=(0.5, 1.01), columnspacing=0.8, handlelength=1.2)
    save(fig, figures, "process_q1_assignment_heatmap", (6.3, 4.2))


def process_q2_b_grid(full: Path, figures: Path) -> None:
    selected_file = full / "selected_policy.json"
    files = sorted(full.glob("tuning_coarse_W*.csv"))
    if not files or not selected_file.exists():
        return
    frame = pd.read_csv(files[-1])
    b = frame[frame["strategy"] == "B"].groupby("candidate")["mean_response_min"].mean().reset_index()
    parsed = b["candidate"].str.extract(r"B_beta(?P<beta>[0-9.]+)_delta(?P<delta>[0-9.]+)").astype(float)
    b = pd.concat([b, parsed], axis=1)
    pivot = b.pivot(index="beta", columns="delta", values="mean_response_min").sort_index().sort_index(axis=1)
    fig, ax = plt.subplots(figsize=(6.3, 4.0))
    values = pivot.to_numpy(dtype=float)
    image = vector_heatmap(
        ax,
        values,
        "viridis_r",
        float(np.nanmin(values)),
        float(np.nanmax(values)),
    )
    ax.set_xticks(range(len(pivot.columns)), [f"{x:g}" for x in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), [f"{x:g}" for x in pivot.index])
    ax.set_xlabel("允许绕行阈值 δ（min）")
    ax.set_ylabel("负荷权重 β（min）")
    selected = json.loads(selected_file.read_text(encoding="utf-8"))["best_b"]
    selected_beta = float(selected["beta"])
    selected_delta = float(selected["delta"])
    if selected_beta in pivot.index and selected_delta in pivot.columns:
        row = pivot.index.get_loc(selected_beta)
        column = pivot.columns.get_loc(selected_delta)
        ax.add_patch(plt.Rectangle((column - 0.5, row - 0.5), 1, 1, fill=False, edgecolor=ORANGE, linewidth=1.8))
    colorbar = fig.colorbar(image, ax=ax, shrink=0.85)
    keep_colorbar_vector(colorbar)
    colorbar.set_label("调参集平均响应时间（min）")
    save(fig, figures, "process_q2_b_grid", (6.3, 4.0))


def process_q2_c_screen(full: Path, figures: Path) -> None:
    files = sorted(full.glob("tuning_coarse_W*.csv"))
    if not files:
        return
    frame = pd.read_csv(files[-1])
    a = frame[frame["candidate"] == "A"].set_index("seed")["mean_response_min"]
    rows = []
    for candidate, group in frame[frame["strategy"] == "C"].groupby("candidate"):
        c = group.set_index("seed")["mean_response_min"]
        common = a.index.intersection(c.index)
        rows.append((candidate, float((c.loc[common] - a.loc[common]).mean()), float(group["strict_4min_rate"].mean())))
    rows.sort(key=lambda item: item[1])
    frame = pd.DataFrame(rows, columns=["candidate", "difference", "coverage"])
    fig, ax = plt.subplots(figsize=(6.3, 3.7))
    ax.scatter(frame["difference"], 100 * frame["coverage"], s=14, c=np.where(frame["difference"] <= 0, GREEN, GRAY), alpha=0.68)
    ax.axvline(0, color=ORANGE, linestyle="--", linewidth=0.9)
    ax.set_xlabel("相对策略A的平均响应时间差（min）")
    ax.set_ylabel("4分钟内到达率（%）")
    save(fig, figures, "process_q2_c_screen", (6.3, 3.7))


def result_q2_summary(full: Path, figures: Path) -> None:
    path = full / "final_summary.csv"
    if not path.exists():
        return
    frame = pd.read_csv(path)
    replicate_path = full / "final_replicates_W030.csv"
    if replicate_path.exists():
        replicates = pd.read_csv(replicate_path)
        order = [
            "mean_response_min",
            "p95_response_min",
            "mean_wait_min",
            "strict_4min_rate",
            "regional_mean_gap_min",
            "mean_delay_penalty_yuan_per_call",
        ]
        labels = [
            "平均响应时间",
            "P95响应时间",
            "平均等待时间",
            "4分钟内到达率",
            "区域平均响应时间极差",
            "平均单次延迟成本",
        ]
        means = frame.pivot(index="candidate", columns="metric", values="mean")
        baseline = means.loc["A", order].to_numpy(dtype=float)
        baseline_replicates = replicates[replicates["candidate"] == "A"].set_index("seed")
        comparisons = [
            ("B_beta4_delta2", "策略B", BLUE, "#004B76", "", -0.18),
            ("C_r001000_tau7", "策略C", ORANGE, "#8F3F00", "///", 0.18),
        ]
        fig, ax = plt.subplots(figsize=(6.3, 3.8))
        y = np.arange(len(order), dtype=float)
        for candidate, label, color, interval_color, hatch, offset in comparisons:
            selected = means.loc[candidate, order].to_numpy(dtype=float)
            values = 100 * (baseline - selected) / baseline
            values[3] = 100 * (selected[3] - baseline[3]) / baseline[3]
            selected_replicates = replicates[replicates["candidate"] == candidate].set_index("seed")
            half_widths: list[float] = []
            for metric_index, metric in enumerate(order):
                common = baseline_replicates.index.intersection(selected_replicates.index)
                paired_improvement = (
                    selected_replicates.loc[common, metric]
                    - baseline_replicates.loc[common, metric]
                    if metric == "strict_4min_rate"
                    else baseline_replicates.loc[common, metric]
                    - selected_replicates.loc[common, metric]
                )
                relative_improvement = 100 * paired_improvement / baseline[metric_index]
                half_widths.append(float(relative_improvement.sem() * 2.045229642))
            bars = ax.barh(
                y + offset,
                values,
                height=0.32,
                color=color,
                label=label,
                alpha=0.88,
                hatch=hatch,
                edgecolor="white",
                linewidth=0.4,
                zorder=2,
            )
            ax.errorbar(
                values,
                y + offset,
                xerr=np.asarray(half_widths),
                fmt="none",
                ecolor=interval_color,
                elinewidth=0.6,
                capsize=2.0,
                capthick=0.6,
                zorder=4,
            )
            for bar, value, half_width in zip(bars, values, half_widths, strict=True):
                label_x = (
                    value + half_width + 0.45
                    if value >= 0
                    else value - half_width - 0.45
                )
                ax.text(
                    label_x,
                    bar.get_y() + bar.get_height() / 2,
                    f"{value:.2f}%",
                    color=color,
                    fontsize=6.7,
                    va="center",
                    ha="left" if value >= 0 else "right",
                    zorder=3,
                )
        ax.axvline(0, color=GRAY, linewidth=0.8)
        ax.set_yticks(y, labels)
        ax.set_xlabel("相对策略A的平均优化幅度（%）")
        ax.grid(axis="x", color="#D1D5DB", linewidth=0.55, alpha=0.75)
        ax.legend(loc="lower right", frameon=False, ncol=2, fontsize=7)
        ax.text(
            0.01,
            1.01,
            "深色误差线：30组相同随机呼叫下策略差异的95%置信区间；正值表示优于策略A",
            transform=ax.transAxes,
            fontsize=6.5,
            color=GRAY,
            va="bottom",
        )
        ax.invert_yaxis()
        save(fig, figures, "result_q2_multi_metric", (6.3, 3.8))


def raw_q3_incident_load(full: Path, figures: Path) -> None:
    path = full / "scenarios.csv"
    if not path.exists():
        return
    frame = pd.read_csv(path)
    nodes = sorted(frame["duration_hours"].unique())
    dense_duration = np.linspace(0.5, 12.0, 240)
    fig, ax = plt.subplots(figsize=(6.3, 4.1))
    colormap = plt.get_cmap("viridis")
    for zone in range(1, 11):
        group = frame[frame["incident_zone"] == zone].sort_values("duration_hours")
        interpolator = PchipInterpolator(
            group["duration_hours"].to_numpy(dtype=float),
            group["expected_extra_calls"].to_numpy(dtype=float),
        )
        color = colormap((zone - 1) / 9)
        ax.plot(
            dense_duration,
            interpolator(dense_duration),
            color=color,
            linewidth=1.0,
            alpha=0.72,
        )
        ax.scatter(
            group["duration_hours"],
            group["expected_extra_calls"],
            s=11,
            color=color,
            edgecolor="white",
            linewidth=0.25,
            zorder=3,
        )
        ax.text(12.08, float(interpolator(12.0)), f"R{zone}", color=color, fontsize=6.3, va="center")
    ax.set_xticks(nodes)
    ax.set_xlim(0.5, 12.65)
    ax.set_xlabel("事故持续时间（h）")
    ax.set_ylabel("最不利窗口内预期新增呼叫量（次）")
    ax.text(
        0.02,
        0.98,
        "实心点为自适应仿真节点；曲线仅表示连续负荷估计",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=6.5,
        color=GRAY,
    )
    save(fig, figures, "raw_q3_incident_load", (6.3, 4.1))


def process_q3_duration_zone(full: Path, figures: Path) -> None:
    path = full / "response_surfaces.csv"
    if not path.exists():
        return
    frame = pd.read_csv(path)
    sub = frame[(frame["metric"] == "mean_response_min") & (frame["mode"] == "B_N")]
    pivot = sub.pivot(index="incident_zone", columns="duration_hours", values="mean").sort_index()
    width_pivot = sub.assign(width=sub["ci95_high"] - sub["ci95_low"]).pivot(
        index="incident_zone", columns="duration_hours", values="width"
    ).sort_index()
    x = pivot.columns.to_numpy(dtype=float)
    y = pivot.index.to_numpy(dtype=float)
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(6.3, 5.1),
        sharex=True,
        gridspec_kw={"height_ratios": [3.2, 1.25]},
    )
    image = axes[0].pcolormesh(x, y, pivot.to_numpy(dtype=float), cmap="magma", shading="nearest")
    sampled_x = sorted(frame.loc[frame["sampled_node"], "duration_hours"].unique())
    axes[0].scatter(
        np.tile(sampled_x, 10),
        np.repeat(np.arange(1, 11), len(sampled_x)),
        s=5,
        facecolor="none",
        edgecolor="white",
        linewidth=0.3,
    )
    axes[0].set_yticks(range(1, 11), [f"R{i}" for i in range(1, 11)])
    axes[0].set_ylabel("事故区域")
    colorbar = fig.colorbar(image, ax=axes[0], shrink=0.90)
    keep_colorbar_vector(colorbar)
    colorbar.set_label(r"常态预测 $B_N$ 平均响应时间（min）")
    max_width = width_pivot.max(axis=0).to_numpy(dtype=float)
    median_width = width_pivot.median(axis=0).to_numpy(dtype=float)
    axes[1].plot(x, max_width, color=ORANGE, linewidth=1.2, label="10区最大带宽")
    axes[1].plot(x, median_width, color=BLUE, linewidth=1.0, linestyle="--", label="10区中位带宽")
    axes[1].scatter(sampled_x, np.interp(sampled_x, x, max_width), s=16, color=ORANGE, zorder=3)
    axes[1].set_xlabel("事故持续时间 H（h）")
    axes[1].set_ylabel("95%置信带宽（min）")
    axes[1].legend(frameon=False, ncol=2, loc="upper left")
    save(fig, figures, "process_q3_duration_zone", (6.3, 5.1))


def result_q3_response_curve(full: Path, figures: Path) -> None:
    path = full / "response_surfaces.csv"
    if not path.exists():
        return
    summary = pd.read_csv(path)
    baseline = summary[(summary["metric"] == "mean_response_min") & (summary["mode"] == "B_N")]
    pressure = baseline.groupby("incident_zone")["mean"].mean().sort_values()
    representative_zones = [
        int(pressure.index[0]),
        int(pressure.index[len(pressure) // 2]),
        int(pressure.index[-1]),
    ]
    titles = ["低压力", "中位压力", "高压力"]
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 2.9), sharex=True)
    styles = {
        "B_N": (BLUE, "o", "常态预测 $B_N$"),
        "B_E": (ORANGE, "s", "事故感知 $B_E$"),
    }
    for ax, zone, title in zip(axes, representative_zones, titles, strict=True):
        for mode in ("B_N", "B_E"):
            group = summary[
                (summary["incident_zone"] == zone)
                & (summary["metric"] == "mean_response_min")
                & (summary["mode"] == mode)
            ].sort_values("duration_hours")
            color, marker, label = styles[mode]
            x = group["duration_hours"].to_numpy(dtype=float)
            mean = group["mean"].to_numpy(dtype=float)
            low = group["ci95_low"].to_numpy(dtype=float)
            high = group["ci95_high"].to_numpy(dtype=float)
            ax.plot(
                x,
                mean,
                color=color,
                linestyle="-" if mode == "B_N" else "--",
                linewidth=1.0,
                label=label,
            )
            ax.fill_between(x, np.maximum(low, 0.0), high, color=color, alpha=0.12)
            nodes = group[group["sampled_node"]]
            ax.scatter(nodes["duration_hours"], nodes["mean"], s=11, marker=marker, color=color, zorder=3)
        ax.set_title(f"{title}：R{zone}", fontsize=8)
        ax.set_xlabel("H（h）")
        ax.set_ylim(bottom=0.0)
    axes[0].set_ylabel("事故期平均响应时间（min）")
    axes[0].text(
        0.02,
        0.97,
        "三面板纵轴独立且均从0开始",
        transform=axes[0].transAxes,
        va="top",
        fontsize=6.2,
        color=GRAY,
    )
    axes[-1].legend(frameon=False, fontsize=6.5, loc="upper left")
    save(fig, figures, "result_q3_response_curve", (6.3, 2.9))


def result_q3_paired_effect(full: Path, figures: Path) -> None:
    path = full / "scoped_paired_response_surfaces.csv"
    if not path.exists():
        return
    frame = pd.read_csv(path)
    citywide = pd.read_csv(full / "citywide_duration_table.csv")
    citywide = citywide[citywide["metric"] == "mean_response_min"].sort_values("duration_hours")
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    styles = {
        "citywide": (BLUE, ":", "全市"),
        "incident_zone_mean_response_min": (PURPLE, "-", "事故区呼叫"),
        "nonincident_zone_mean_response_min": (GREEN, "--", "非事故区呼叫"),
    }
    for metric, (color, linestyle, label) in styles.items():
        group = (
            citywide.assign(sampled_node=True)
            if metric == "citywide"
            else frame[frame["metric"] == metric].sort_values("duration_hours")
        )
        x = group["duration_hours"].to_numpy(dtype=float)
        mean = group["mean_difference_B_E_minus_B_N"].to_numpy(dtype=float)
        ax.plot(x, mean, color=color, linestyle=linestyle, linewidth=1.1, label=label)
        ax.fill_between(
            x,
            group["ci95_low"].to_numpy(dtype=float),
            group["ci95_high"].to_numpy(dtype=float),
            color=color,
            alpha=0.14,
        )
        nodes = group[group["sampled_node"]]
        ax.scatter(
            nodes["duration_hours"],
            nodes["mean_difference_B_E_minus_B_N"],
            s=14,
            color=color,
            zorder=3,
        )
    ax.axhline(0.0, color=GRAY, linestyle=":", linewidth=0.9)
    ax.set_xlabel("事故持续时间 H（h）")
    ax.set_ylabel(r"成对平均响应时间差 $B_E-B_N$（min）")
    ax.legend(frameon=False, loc="lower left", ncol=3, fontsize=7)
    ax.text(
        0.02,
        0.97,
        "阴影为95%置信区间；负值表示事故感知预测改善响应",
        transform=ax.transAxes,
        va="top",
        fontsize=6.5,
        color=GRAY,
    )
    save(fig, figures, "result_q3_paired_effect", (6.3, 3.6))


def result_q3_external_support(full: Path, figures: Path) -> None:
    path = full / "external-support" / "external_support_citywide.csv"
    if not path.exists():
        return
    frame = pd.read_csv(path)
    fig = plt.figure(figsize=(6.3, 5.8))
    grid = fig.add_gridspec(
        2,
        2,
        width_ratios=[1.12, 0.88],
        height_ratios=[0.95, 1.15],
    )
    ax_response = fig.add_subplot(grid[0, 0])
    ax_share = fig.add_subplot(grid[0, 1])
    ax_penalty = fig.add_subplot(grid[1, :])

    durations = [0.5, 2.0, 4.0, 6.0, 8.0, 12.0]
    line_styles = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]
    markers = ["o", "s", "^", "D", "v", "P"]
    duration_colors = plt.get_cmap("viridis")(np.linspace(0.08, 0.92, len(durations)))
    for duration, color, linestyle, marker in zip(
        durations,
        duration_colors,
        line_styles,
        markers,
        strict=True,
    ):
        group = frame[np.isclose(frame["duration_hours"], duration)].sort_values(
            "external_count"
        )
        x = group["external_count"].to_numpy(dtype=float)
        mean = group["mean_response_min_mean"].to_numpy(dtype=float)
        low = group["mean_response_min_ci95_low"].to_numpy(dtype=float)
        high = group["mean_response_min_ci95_high"].to_numpy(dtype=float)
        ax_response.errorbar(
            x,
            mean,
            yerr=np.vstack((mean - low, high - mean)),
            color=color,
            linestyle=linestyle,
            marker=marker,
            markersize=3.2,
            linewidth=1.0,
            elinewidth=0.45,
            capsize=1.4,
            alpha=0.92,
            label=f"H={duration:g} h",
        )
    ax_response.axvline(3, color=GRAY, linestyle="--", linewidth=0.8)
    ax_response.set_xlabel("临时外援车辆数（辆）")
    ax_response.set_ylabel("全市平均响应时间（min）")
    ax_response.set_xticks(range(7))
    ax_response.set_ylim(bottom=0.0)
    ax_response.set_title("不同事故时长下的响应变化", fontsize=8)
    ax_response.legend(frameon=False, fontsize=6.1, ncol=2, loc="upper right")

    long_durations = [6.0, 8.0, 10.0, 11.0, 12.0]
    long_colors = plt.get_cmap("viridis")(np.linspace(0.08, 0.92, len(long_durations)))
    long_styles = ["-", "--", "-.", ":", (0, (3, 1, 1, 1))]
    long_markers = ["o", "s", "^", "v", "D"]
    for duration, color, linestyle, marker in zip(
        long_durations,
        long_colors,
        long_styles,
        long_markers,
        strict=True,
    ):
        group = frame[np.isclose(frame["duration_hours"], duration)].sort_values(
            "external_count"
        )
        group = group[group["external_count"] > 0]
        total_gain = float(
            group.loc[group["external_count"] == 6, "cumulative_response_gain_min_mean"].iloc[0]
        )
        share = 100.0 * group["cumulative_response_gain_min_mean"].to_numpy(dtype=float) / total_gain
        ax_share.plot(
            group["external_count"],
            share,
            color=color,
            linestyle=linestyle,
            marker=marker,
            markersize=3.2,
            linewidth=1.0,
            label=f"H={duration:g} h",
        )
    ax_share.axhline(90, color=GRAY, linestyle="--", linewidth=0.8)
    ax_share.axvline(3, color=GRAY, linestyle="--", linewidth=0.8)
    ax_share.set_xlabel("临时外援车辆数（辆）")
    ax_share.set_ylabel("响应改善达成率（%）")
    ax_share.set_xticks(range(1, 7))
    ax_share.set_ylim(0, 104)
    ax_share.set_title("长时事故的响应改善达成率", fontsize=8)
    ax_share.text(
        0.03,
        0.96,
        "6辆外援=100%",
        transform=ax_share.transAxes,
        ha="left",
        va="top",
        fontsize=6.2,
        color=GRAY,
    )
    ax_share.legend(frameon=False, fontsize=6.2, ncol=2, loc="lower right")

    penalty = (
        frame[frame["external_count"] > 0]
        .pivot(
            index="duration_hours",
            columns="external_count",
            values="marginal_break_even_cost_yuan_mean",
        )
        .sort_index()
        .sort_index(axis=1)
        / 10_000.0
    )
    penalty_values = penalty.to_numpy(dtype=float)
    penalty_norm = colors.LogNorm(
        vmin=float(np.nanmin(penalty_values)),
        vmax=float(np.nanmax(penalty_values)),
    )
    penalty_cmap = plt.get_cmap("YlGnBu")
    for row in range(penalty_values.shape[0]):
        for column in range(penalty_values.shape[1]):
            value = penalty_values[row, column]
            ax_penalty.add_patch(
                plt.Rectangle(
                    (column - 0.5, row - 0.5),
                    1.0,
                    1.0,
                    facecolor=penalty_cmap(penalty_norm(value)),
                    edgecolor="white",
                    linewidth=0.45,
                )
            )
            ax_penalty.text(
                column,
                row,
                f"{value:.2f}",
                ha="center",
                va="center",
                fontsize=6.1,
                color="white" if penalty_norm(value) > 0.58 else "#111827",
            )
    ax_penalty.set_xlim(-0.5, penalty_values.shape[1] - 0.5)
    ax_penalty.set_ylim(penalty_values.shape[0] - 0.5, -0.5)
    ax_penalty.set_xticks(
        range(len(penalty.columns)),
        [f"第{int(count)}辆" for count in penalty.columns],
    )
    ax_penalty.set_yticks(
        range(len(penalty.index)),
        [f"{duration:g}" for duration in penalty.index],
    )
    ax_penalty.set_xlabel("新增外援序号")
    ax_penalty.set_ylabel("事故持续时间 H（h）")
    ax_penalty.set_title("新增第m辆外援的边际避免罚金", fontsize=8)
    penalty_map = plt.cm.ScalarMappable(norm=penalty_norm, cmap=penalty_cmap)
    colorbar = fig.colorbar(penalty_map, ax=ax_penalty, pad=0.025, shrink=0.92)
    keep_colorbar_vector(colorbar)
    colorbar.set_label("边际避免罚金（万元/辆·事故情景，对数色阶）", fontsize=6.8)
    colorbar.ax.tick_params(labelsize=6.0)

    for label, ax in zip(
        ("(a)", "(b)", "(c)"),
        (ax_response, ax_share, ax_penalty),
        strict=True,
    ):
        ax.text(-0.15, 1.04, label, transform=ax.transAxes, fontsize=8, fontweight="bold")
    issues = audit_layout(fig)
    failures = [message for severity, message in issues if severity == "FAIL"]
    if failures:
        raise RuntimeError("; ".join(failures))
    save(fig, figures, "result_q3_external_support", (6.3, 5.8))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    figures = project_root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    setup_style(journal="general", lang="zh", serif_for_zh=False, constrained_layout=True)
    data, result = q1_tables(project_root)
    raw_q1_spatial(data, figures)
    raw_q2_intensity(data, figures)
    process_q1_heatmap(data, result, figures)
    full = project_root / "results" / "task-2"
    process_q2_b_grid(full, figures)
    process_q2_c_screen(full, figures)
    result_q2_summary(full, figures)
    emergency = project_root / "results" / "task-3"
    raw_q3_incident_load(emergency, figures)
    process_q3_duration_zone(emergency, figures)
    result_q3_response_curve(emergency, figures)
    result_q3_paired_effect(emergency, figures)
    result_q3_external_support(emergency, figures)


if __name__ == "__main__":
    main()
