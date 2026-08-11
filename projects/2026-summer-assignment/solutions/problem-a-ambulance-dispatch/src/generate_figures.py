from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from ambulance_model import (
    PREP_MINUTES,
    SPEED_KMH,
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


BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"
PURPLE = "#CC79A7"
GRAY = "#6B7280"
SITE_COLORS = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9"]


def policy_label(candidate: str) -> str:
    labels = {
        "A": "策略A（就近派车）",
        "B_beta4_delta2": "策略B（保护性派车）",
        "C_r001000_tau4": "策略C（S3固定备用）",
    }
    return labels.get(candidate, candidate)


def save(fig: plt.Figure, figures: Path, name: str, size: tuple[float, float]) -> None:
    paths = export_figure(
        fig,
        str(figures / name),
        formats=["svg", "png"],
        size_inches=size,
        dpi=300,
        grayscale_preview=True,
        tight=False,
    )
    qa_dir = figures / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        preview = Path(path)
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
            "daily_calls": data.demand,
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


def raw_q1_demand(data, figures: Path) -> None:
    order = np.argsort(data.demand)
    fig, ax = plt.subplots(figsize=(6.3, 3.7))
    ax.barh(np.array(data.zone_names)[order], data.demand[order], color=BLUE, alpha=0.85)
    for y, value in enumerate(data.demand[order]):
        ax.text(value + 0.4, y, f"{value:.0f}", va="center", fontsize=7)
    ax.set_xlabel("日均急救呼叫量（次）")
    ax.set_ylabel("")
    ax.set_xlim(0, max(data.demand) * 1.15)
    save(fig, figures, "raw_q1_demand", (6.3, 3.7))


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


def process_q1_distance(data, result: dict[str, object], figures: Path) -> None:
    assignment = np.asarray(result["assignment"])
    fig, ax = plt.subplots(figsize=(6.3, 4.4))
    for i in range(len(data.zone_ids)):
        for j in range(len(data.site_ids)):
            amount = assignment[i, j]
            if amount <= 1e-8:
                continue
            ax.plot(
                [data.zone_xy[i, 0], data.site_xy[j, 0]],
                [data.zone_xy[i, 1], data.site_xy[j, 1]],
                color=SITE_COLORS[j],
                linewidth=0.7 + 0.09 * amount,
                alpha=0.62,
                zorder=1,
            )
    ax.scatter(data.zone_xy[:, 0], data.zone_xy[:, 1], s=28 + 5 * data.demand, c="white", edgecolor=BLUE, zorder=3)
    ax.scatter(data.site_xy[:, 0], data.site_xy[:, 1], s=100, c=SITE_COLORS, marker="s", edgecolor="black", zorder=4)
    for i, (x, y) in enumerate(data.zone_xy):
        ax.annotate(f"R{data.zone_ids[i]}", (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7)
    for i, (x, y) in enumerate(data.site_xy):
        ax.annotate(data.site_ids[i], (x, y), xytext=(-8, -14), textcoords="offset points", fontsize=7)
    ax.set_xlabel("X 坐标（km）")
    ax.set_ylabel("Y 坐标（km）")
    ax.set_aspect("equal", adjustable="box")
    save(fig, figures, "process_q1_transport_network", (6.3, 4.4))


def process_q1_heatmap(data, result: dict[str, object], figures: Path) -> None:
    assignment = np.asarray(result["assignment"])
    fig, ax = plt.subplots(figsize=(6.3, 4.2))
    image = ax.imshow(assignment, cmap="Blues", aspect="auto", vmin=0)
    for i in range(assignment.shape[0]):
        for j in range(assignment.shape[1]):
            if assignment[i, j] > 0:
                ax.text(j, i, f"{assignment[i, j]:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if assignment[i, j] > assignment.max() * 0.45 else "black")
    ax.set_xticks(range(len(data.site_ids)), data.site_ids)
    ax.set_yticks(range(len(data.zone_ids)), [f"R{i}" for i in data.zone_ids])
    ax.set_xlabel("站点")
    ax.set_ylabel("需求区")
    colorbar = fig.colorbar(image, ax=ax, shrink=0.86)
    colorbar.set_label("日分配呼叫量（次）")
    save(fig, figures, "process_q1_assignment_heatmap", (6.3, 4.2))


def result_q1_capacity(data, result: dict[str, object], figures: Path) -> None:
    loads = np.asarray(result["loads"])
    capacity = 12 * np.asarray(result["vehicles"])
    x = np.arange(len(data.site_ids))
    fig, ax = plt.subplots(figsize=(6.3, 3.7))
    ax.bar(x, capacity, color="#DCE6F1", edgecolor=BLUE, label="日服务上限")
    ax.bar(x, loads, color=BLUE, alpha=0.85, label="优化分配负荷")
    for xi, load, cap in zip(x, loads, capacity, strict=True):
        ax.text(xi, load + 0.6, f"{load:.0f}/{cap:.0f}", ha="center", fontsize=7)
    ax.set_xticks(x, data.site_ids)
    ax.set_xlabel("站点")
    ax.set_ylabel("呼叫量（次/日）")
    ax.set_ylim(0, max(capacity) * 1.15)
    ax.legend(frameon=False, ncols=2)
    save(fig, figures, "result_q1_site_capacity", (6.3, 3.7))


def result_q1_coverages(result: dict[str, object], figures: Path) -> None:
    labels = ["严格4分钟覆盖", "优化分配3 km覆盖", "潜在3 km覆盖"]
    values = 100 * np.array([
        result["strict_coverage"],
        result["assigned_3km_coverage"],
        result["potential_3km_coverage"],
    ])
    fig, ax = plt.subplots(figsize=(6.3, 3.4))
    y = np.arange(len(labels))
    ax.barh(y, values, color=[ORANGE, BLUE, GREEN])
    for yi, value in enumerate(values):
        ax.text(value + 1.0, yi, f"{value:.3f}%", va="center", fontsize=8)
    ax.set_yticks(y, labels)
    ax.set_xlim(0, 105)
    ax.set_xlabel("覆盖率（%）")
    ax.invert_yaxis()
    save(fig, figures, "result_q1_coverage", (6.3, 3.4))


def result_q1_response(data, result: dict[str, object], figures: Path) -> None:
    assignment = np.asarray(result["assignment"])
    rows = []
    for i, zone in enumerate(data.zone_ids):
        positive = assignment[i] > 1e-8
        weighted = float(np.sum(assignment[i, positive] * data.distance[i, positive]) / data.demand[i])
        rows.append((zone, PREP_MINUTES + 60 * weighted / SPEED_KMH))
    rows.sort(key=lambda item: item[1])
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    x = np.arange(len(rows))
    values = np.array([value for _, value in rows])
    colors = np.where(values <= 4.0, GREEN, ORANGE)
    ax.scatter(x, values, c=colors, s=36, edgecolor="black", linewidth=0.4)
    ax.axhline(4.0, color=GRAY, linestyle="--", linewidth=0.9, label="4分钟时限")
    ax.set_xticks(x, [f"R{zone}" for zone, _ in rows])
    ax.set_xlabel("需求区")
    ax.set_ylabel("静态加权响应下界（min）")
    ax.legend(frameon=False)
    save(fig, figures, "result_q1_zone_response", (6.3, 3.6))


def raw_q2_region_rates(data, figures: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    order = np.argsort(data.demand)[::-1]
    ax.bar(np.arange(len(order)), data.demand[order] / 140, color=BLUE)
    ax.set_xticks(np.arange(len(order)), [f"R{i}" for i in np.array(data.zone_ids)[order]])
    ax.set_xlabel("需求区")
    ax.set_ylabel("呼叫区域概率")
    ax.set_ylim(0, max(data.demand / 140) * 1.18)
    save(fig, figures, "raw_q2_region_probability", (6.3, 3.6))


def raw_q1_hospital_distance(data, figures: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    ax.scatter(data.demand, data.hospital_distance, s=34 + 3 * data.demand, color=ORANGE, edgecolor="black", linewidth=0.4)
    for zone, x, y in zip(data.zone_ids, data.demand, data.hospital_distance, strict=True):
        ax.annotate(f"R{zone}", (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.set_xlabel("日均急救呼叫量（次）")
    ax.set_ylabel("距最近医院距离（km）")
    save(fig, figures, "raw_q1_hospital_distance", (6.3, 3.6))


def process_q2_warmup(full: Path, figures: Path) -> None:
    files = sorted(full.glob("warmup_final_from_W*_daily_h*.csv")) or sorted(full.glob("warmup_coarse_daily_h*.csv"))
    if not files:
        return
    frame = pd.read_csv(files[-1])
    selected = frame[frame["candidate"].isin(frame["candidate"].drop_duplicates().head(4))]
    daily = selected.groupby(["candidate", "day"])["mean_response_min"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(6.3, 3.7))
    for idx, (candidate, group) in enumerate(daily.groupby("candidate")):
        group = group.sort_values("day").copy()
        group["batch"] = group["day"] // 5
        batched = group.groupby("batch", as_index=False).agg(
            day=("day", lambda values: float(values.mean() + 1)),
            mean_response_min=("mean_response_min", "mean"),
        )
        ax.plot(
            batched["day"],
            batched["mean_response_min"],
            label=policy_label(candidate),
            linewidth=1.0,
            color=SITE_COLORS[idx % len(SITE_COLORS)],
        )
    ax.axvline(40, color=GRAY, linestyle="--", linewidth=0.9, label="统一预热期 W=40日")
    ax.set_xlabel("试运行日")
    ax.set_ylabel("5日分批平均响应时间（min）")
    ax.legend(frameon=False, fontsize=6, ncols=2)
    save(fig, figures, "process_q2_warmup", (6.3, 3.7))


def process_q2_b_grid(full: Path, figures: Path) -> None:
    selected_file = full / "selected_policy.json"
    files = sorted(full.glob("tuning_all_W*.csv"))
    if not files or not selected_file.exists():
        return
    frame = pd.read_csv(files[-1])
    b = frame[frame["strategy"] == "B"].groupby("candidate")["mean_response_min"].mean().reset_index()
    parsed = b["candidate"].str.extract(r"B_beta(?P<beta>[0-9.]+)_delta(?P<delta>[0-9.]+)").astype(float)
    b = pd.concat([b, parsed], axis=1)
    pivot = b.pivot(index="beta", columns="delta", values="mean_response_min").sort_index().sort_index(axis=1)
    fig, ax = plt.subplots(figsize=(6.3, 4.0))
    image = ax.imshow(pivot, cmap="viridis_r", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)), [f"{x:g}" for x in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), [f"{x:g}" for x in pivot.index])
    ax.set_xlabel("允许绕行阈值 δ（min）")
    ax.set_ylabel("负荷权重 β（min）")
    colorbar = fig.colorbar(image, ax=ax, shrink=0.85)
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
    ax.set_ylabel("严格4分钟率（%）")
    save(fig, figures, "process_q2_c_screen", (6.3, 3.7))


def result_q2_summary(full: Path, figures: Path) -> None:
    path = full / "final_summary.csv"
    if not path.exists():
        return
    frame = pd.read_csv(path)
    sub = frame[frame["metric"] == "mean_response_min"].copy()
    sub = sub.sort_values("mean")
    fig, ax = plt.subplots(figsize=(6.3, 2.7))
    y = np.arange(len(sub))
    ax.errorbar(
        sub["mean"], y,
        xerr=np.vstack([sub["mean"] - sub["ci95_low"], sub["ci95_high"] - sub["mean"]]),
        fmt="o", color=BLUE, capsize=3,
    )
    ax.set_yticks(y, [policy_label(value) for value in sub["candidate"]])
    ax.set_xlabel("平均响应时间及复制均值95%置信区间（min）")
    ax.invert_yaxis()
    save(fig, figures, "result_q2_mean_response", (6.3, 2.7))

    metrics = ["strict_4min_rate", "p95_response_min", "mean_wait_min", "regional_mean_gap_min"]
    labels = ["严格4分钟率", "P95响应时间", "平均等待时间", "区域均值极差"]
    means = frame[frame["metric"].isin(metrics)].pivot(index="candidate", columns="metric", values="mean")
    if "A" in means.index and "B_beta4_delta2" in means.index:
        baseline = means.loc["A", metrics].to_numpy(dtype=float)
        optimized = means.loc["B_beta4_delta2", metrics].to_numpy(dtype=float)
        improvement = 100 * (baseline - optimized) / baseline
        improvement[0] = 100 * (optimized[0] - baseline[0]) / baseline[0]
        fig, ax = plt.subplots(figsize=(6.3, 3.2))
        y = np.arange(len(labels))
        bars = ax.barh(y, improvement, color=[GREEN, BLUE, BLUE, BLUE], alpha=0.86)
        ax.axvline(0, color=GRAY, linewidth=0.8)
        for bar, value in zip(bars, improvement, strict=True):
            ax.text(value + 0.08, bar.get_y() + bar.get_height() / 2, f"{value:.2f}%", va="center", fontsize=7)
        ax.set_yticks(y, labels)
        ax.set_xlabel("策略B相对策略A的改善率（%）")
        ax.invert_yaxis()
        save(fig, figures, "result_q2_multi_metric", (6.3, 3.2))

    paired = full / "final_paired_response.csv"
    if paired.exists() and paired.stat().st_size > 5:
        p = pd.read_csv(paired)
        fig, ax = plt.subplots(figsize=(6.3, 2.4))
        y = np.arange(len(p))
        ax.errorbar(
            p["mean_difference_min"], y,
            xerr=np.vstack([p["mean_difference_min"] - p["ci95_low"], p["ci95_high"] - p["mean_difference_min"]]),
            fmt="o", color=PURPLE, capsize=3,
        )
        ax.axvline(0, color=GRAY, linestyle="--", linewidth=0.9)
        ax.set_yticks(y, ["策略B - 策略A"] * len(p))
        ax.set_xlabel("相对策略A的成对平均响应差及95%置信区间（min）")
        save(fig, figures, "result_q2_paired_difference", (6.3, 2.4))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    figures = project_root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    setup_style(journal="general", lang="zh", serif_for_zh=True, constrained_layout=True)
    data, result = q1_tables(project_root)
    raw_q1_demand(data, figures)
    raw_q1_spatial(data, figures)
    raw_q1_hospital_distance(data, figures)
    raw_q2_intensity(data, figures)
    raw_q2_region_rates(data, figures)
    process_q1_distance(data, result, figures)
    process_q1_heatmap(data, result, figures)
    result_q1_capacity(data, result, figures)
    result_q1_coverages(result, figures)
    result_q1_response(data, result, figures)
    full = project_root / "results" / "task-2"
    process_q2_warmup(full, figures)
    process_q2_b_grid(full, figures)
    process_q2_c_screen(full, figures)
    result_q2_summary(full, figures)


if __name__ == "__main__":
    main()
