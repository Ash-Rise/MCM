from __future__ import annotations

import csv
import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "problem_b_data.json"
SCHEDULE_PATH = PROJECT_ROOT / "results" / "route_schedule.csv"
SUMMARY_PATH = PROJECT_ROOT / "results" / "summary.json"
FIGURE_DIR = PROJECT_ROOT / "figures"


COLORS = {"A": "#0072B2", "B": "#D55E00", "C": "#009E73"}
LINESTYLES = {"A": "-", "B": "--", "C": "-."}
MARKERS = {"A": "o", "B": "s", "C": "^"}


def configure_style() -> str:
    available = {font.name for font in font_manager.fontManager.ttflist}
    preferred = ["SimSun", "Noto Serif SC", "Source Han Serif SC", "Microsoft YaHei"]
    chosen = next((font for font in preferred if font in available), None)
    if chosen is None:
        raise RuntimeError("No supported Chinese font found; install Noto Serif SC or SimSun")
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": [chosen, "Times New Roman", "DejaVu Serif"],
            "font.size": 9,
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 8,
            "axes.unicode_minus": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    return chosen


def load_inputs() -> tuple[dict, dict, list[dict[str, str]]]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    with SCHEDULE_PATH.open(encoding="utf-8-sig", newline="") as handle:
        schedule = list(csv.DictReader(handle))
    return data, summary, schedule


def node(data: dict, node_id: int) -> dict:
    return data["nodes"][str(node_id)]


def format_clock(minute: float) -> str:
    hour = int(minute // 60)
    mins = int(round(minute - 60 * hour))
    if mins == 60:
        hour += 1
        mins = 0
    return f"{hour:02d}:{mins:02d}"


def add_node_labels(ax, data: dict) -> None:
    offsets = {
        0: (4, -13), 1: (4, 5), 2: (4, -13), 3: (-30, -13), 4: (4, 5),
        5: (4, 5), 6: (-32, 5), 7: (4, -13), 8: (-34, 5), 9: (4, -13),
    }
    for raw_id, item in data["nodes"].items():
        node_id = int(raw_id)
        dx, dy = offsets[node_id]
        ax.annotate(
            f"{node_id} {item['name']}",
            (item["x"], item["y"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=7,
        )


def scatter_nodes(ax, data: dict, colored_assignments: bool) -> None:
    store_to_vehicle = {
        store: vehicle
        for vehicle, spec in data["vehicles"].items()
        for store in spec["stores"]
    }
    for raw_id, item in data["nodes"].items():
        node_id = int(raw_id)
        if item["type"] == "kitchen":
            ax.scatter(item["x"], item["y"], marker="*", s=150, color="#222222", zorder=5)
        elif item["type"] == "station":
            vehicle = next(v for v, spec in data["vehicles"].items() if spec["station"] == node_id)
            color = COLORS[vehicle] if colored_assignments else "#666666"
            ax.scatter(item["x"], item["y"], marker="s", s=62, color=color,
                       edgecolor="white", linewidth=0.7, zorder=5)
        else:
            vehicle = store_to_vehicle[node_id]
            color = COLORS[vehicle] if colored_assignments else "#999999"
            ax.scatter(item["x"], item["y"], marker="o", s=55, color=color,
                       edgecolor="white", linewidth=0.7, zorder=5)
    add_node_labels(ax, data)


def finish_map(ax) -> None:
    ax.set_xlabel("横坐标（km）")
    ax.set_ylabel("纵坐标（km）")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, color="#D9D9D9", linewidth=0.5, alpha=0.7)
    ax.set_xlim(-8.2, 16.2)
    ax.set_ylim(-7.0, 14.2)


def draw_arc(ax, data: dict, start: int, end: int, *, color: str, linestyle: str,
             linewidth: float, rad: float = 0.0, alpha: float = 1.0,
             mutation_scale: float = 10.0, zorder: int = 2) -> None:
    p1 = node(data, start)
    p2 = node(data, end)
    arrow = FancyArrowPatch(
        (p1["x"], p1["y"]), (p2["x"], p2["y"]),
        arrowstyle="-|>", mutation_scale=mutation_scale,
        connectionstyle=f"arc3,rad={rad}", color=color,
        linestyle=linestyle, linewidth=linewidth, alpha=alpha, zorder=zorder,
        shrinkA=7, shrinkB=7,
    )
    ax.add_patch(arrow)


def figure_assignment_network(data: dict) -> plt.Figure:
    """Contract: show source coordinates, fixed station-store assignments, and closure input."""
    fig, ax = plt.subplots(figsize=(7.2, 5.0), layout="none")
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.12, top=0.91)
    for vehicle, spec in data["vehicles"].items():
        station = spec["station"]
        for store in spec["stores"]:
            p1, p2 = node(data, station), node(data, store)
            ax.plot([p1["x"], p2["x"]], [p1["y"], p2["y"]],
                    color=COLORS[vehicle], linestyle=LINESTYLES[vehicle],
                    linewidth=1.5, alpha=0.8, zorder=1)
    draw_arc(ax, data, 2, 8, color="#CC3311", linestyle=":", linewidth=2.0,
             rad=0.10, alpha=0.9)
    scatter_nodes(ax, data, colored_assignments=True)
    ax.text(-5.0, 5.9, "任务三封闭弧 2→8", color="#AA2211", fontsize=8,
            rotation=-11, ha="center")
    legend = [
        Line2D([0], [0], color=COLORS[v], linestyle=LINESTYLES[v], lw=1.8,
               label=f"车辆 {v} 固定分区") for v in ("A", "B", "C")
    ]
    legend += [
        Line2D([0], [0], marker="*", color="none", markerfacecolor="#222222",
               markeredgecolor="#222222", markersize=10, label="中央厨房"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor="#777777",
               markeredgecolor="white", markersize=7, label="配送站"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#999999",
               markeredgecolor="white", markersize=7, label="门店"),
    ]
    ax.legend(handles=legend, loc="lower left", ncol=2, frameon=False)
    ax.set_title("节点坐标、固定分区与封闭弧")
    finish_map(ax)
    return fig


def figure_optimal_routes(data: dict, summary: dict) -> plt.Figure:
    """Contract: show the exact optimum and why the 2→8 closure leaves it unchanged."""
    fig, ax = plt.subplots(figsize=(7.2, 5.0), layout="none")
    fig.subplots_adjust(left=0.11, right=0.98, bottom=0.12, top=0.91)
    routes = summary["normal"]["routes"]
    for vehicle, route in routes.items():
        for start, end in zip(route, route[1:]):
            draw_arc(ax, data, start, end, color=COLORS[vehicle],
                     linestyle=LINESTYLES[vehicle], linewidth=2.0,
                     rad=0.04 if start == 0 or end == 0 else 0.0)
    draw_arc(ax, data, 2, 8, color="#CC3311", linestyle=":", linewidth=2.2,
             rad=0.12, alpha=0.75, zorder=1)
    scatter_nodes(ax, data, colored_assignments=True)
    ax.text(-5.0, 5.8, "封闭但未被最优路线使用", color="#AA2211", fontsize=8,
            rotation=-11, ha="center")
    handles = [
        Line2D([0], [0], color=COLORS[v], linestyle=LINESTYLES[v], lw=2.0,
               marker=MARKERS[v], label=f"{v}: {summary['normal']['route_labels'][v]}")
        for v in ("A", "B", "C")
    ]
    handles.append(Line2D([0], [0], color="#CC3311", linestyle=":", lw=2.2,
                          label="封闭有向弧 2→8"))
    ax.legend(handles=handles, loc="lower left", frameon=False)
    ax.set_title(
        "正常与扰动情景的共同最优路线"
        f"（总里程 {summary['normal']['distance_km']:.2f} km）"
    )
    finish_map(ax)
    return fig


def figure_time_windows(data: dict, schedule: list[dict[str, str]]) -> plt.Figure:
    """Contract: directly compare every store arrival with its hard time window."""
    store_rows = [
        row
        for row in schedule
        if row["scenario"] == "normal" and row["node_type"] == "store"
    ]
    order = [("A", 4), ("A", 6), ("B", 5), ("B", 8), ("C", 9), ("C", 7)]
    lookup = {(row["vehicle"], int(row["node"])): row for row in store_rows}

    fig, ax = plt.subplots(figsize=(7.2, 4.3), layout="none")
    fig.subplots_adjust(left=0.19, right=0.98, bottom=0.16, top=0.90)
    for y, key in enumerate(order):
        vehicle, node_id = key
        item = node(data, node_id)
        row = lookup[key]
        start, end = item["window_start"], item["window_end"]
        arrival = float(row["arrival_minute"])
        ax.hlines(y, start, end, color="#B8B8B8", linewidth=7, zorder=1)
        ax.plot(arrival, y, marker=MARKERS[vehicle], color=COLORS[vehicle],
                markersize=7, markeredgecolor="white", markeredgewidth=0.7, zorder=3)
        ax.annotate(format_clock(arrival), (arrival, y), xytext=(5, 0),
                    textcoords="offset points", va="center", fontsize=7,
                    color=COLORS[vehicle])

    labels = [f"车辆 {v} · {node(data, n)['name']}" for v, n in order]
    ax.set_yticks(range(len(order)), labels)
    ax.invert_yaxis()
    ticks = list(range(270, 361, 15))
    ax.set_xticks(ticks, [format_clock(value) for value in ticks])
    ax.set_xlim(267, 363)
    ax.set_xlabel("时刻")
    ax.set_ylabel("配送事件")
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.5)
    ax.set_title("最优方案到达时刻与门店时间窗")
    ax.text(
        360.5, 0.25, "灰线段：允许到达时间窗\n彩色符号：实际到达时刻",
        ha="right", va="center", fontsize=7,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 2.5},
    )
    return fig


def save_figure(fig: plt.Figure, basename: str, size: tuple[float, float]) -> None:
    fig.set_size_inches(*size)
    png_path = FIGURE_DIR / f"{basename}.png"
    fig.savefig(png_path, dpi=300)
    print(f"wrote {png_path.name}")
    plt.close(fig)


def main() -> None:
    warnings.filterwarnings("error", message=r"Glyph .* missing from font")
    cjk_font = configure_style()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    data, summary, schedule = load_inputs()
    save_figure(figure_assignment_network(data), "fig1_assignment_network", (7.2, 5.0))
    save_figure(figure_optimal_routes(data, summary), "fig2_optimal_routes", (7.2, 5.0))
    save_figure(figure_time_windows(data, schedule), "fig3_time_windows", (7.2, 4.3))
    print(f"CJK font: {cjk_font}")


if __name__ == "__main__":
    main()
