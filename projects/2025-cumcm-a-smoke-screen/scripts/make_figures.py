from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Ellipse
from scipy.spatial import ConvexHull


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN = (PROJECT_ROOT / "results" / "frozen").resolve()
OUTPUT = PROJECT_ROOT / "figures"

COLORS = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "gray": "#6E6E6E",
    "light": "#D9D9D9",
}
DRONE_COLORS = {
    "FY1": COLORS["blue"],
    "FY2": COLORS["orange"],
    "FY3": COLORS["green"],
    "FY4": COLORS["vermillion"],
    "FY5": COLORS["purple"],
}


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Noto Sans SC", "Microsoft YaHei", "DejaVu Sans"],
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "axes.linewidth": 0.8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "lines.linewidth": 1.5,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def load_frozen(name: str) -> dict:
    path = (FROZEN / name).resolve()
    if path.parent != FROZEN:
        raise RuntimeError("Figure input escaped results/frozen")
    return json.loads(path.read_text(encoding="utf-8"))


def save(fig: plt.Figure, stem: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / f"{stem}.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(OUTPUT / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def cylinder_surface(n_theta: int = 180, n_z: int = 9) -> np.ndarray:
    theta = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    side = np.array(
        [[7.0 * np.cos(a), 200.0 + 7.0 * np.sin(a), z]
         for z in np.linspace(0.0, 10.0, n_z) for a in theta]
    )
    caps = np.array(
        [[r * np.cos(a), 200.0 + r * np.sin(a), z]
         for z in (0.0, 10.0) for r in np.linspace(0.0, 7.0, 5) for a in theta]
    )
    return np.vstack((side, caps))


def figure_geometry() -> None:
    q1 = load_frozen("q1.json")
    left, right = q1["shielding_intervals_s"][0]
    time = 0.5 * (left + right)
    missile_initial = np.array([20000.0, 0.0, 2000.0])
    missile = missile_initial * (1.0 - 300.0 * time / np.linalg.norm(missile_initial))
    cloud = np.asarray(q1["explosion_point_m"], dtype=float)
    cloud[2] -= 3.0 * (time - q1["explosion_time_s"])
    target_center = np.array([0.0, 200.0, 5.0])

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.05), constrained_layout=True)
    ax = axes[0]
    target_outline = np.array([[0.0, 193.0, 5.0], [0.0, 207.0, 5.0]])
    for target in target_outline:
        ax.plot([missile[0] / 1000.0, target[0]], [missile[1], target[1]],
                color=COLORS["gray"], linewidth=0.8, alpha=0.75)
    ax.plot([missile[0] / 1000.0, target_center[0]], [missile[1], target_center[1]],
            color=COLORS["blue"], linestyle="--", linewidth=1.1, label="中心视线")
    ax.scatter(missile[0] / 1000.0, missile[1], s=36, marker=">", color=COLORS["vermillion"], zorder=4)
    ax.add_patch(Ellipse((cloud[0] / 1000.0, cloud[1]), 0.020, 20.0,
                         facecolor=COLORS["sky"], edgecolor=COLORS["blue"], alpha=0.55))
    ax.scatter(target_center[0], target_center[1], s=42, marker="s", color=COLORS["green"], zorder=4)
    ax.annotate("M1", (missile[0] / 1000.0, missile[1]), xytext=(-6, 8), textcoords="offset points")
    ax.annotate("烟幕云团", (cloud[0] / 1000.0, cloud[1]), xytext=(-58, 14), textcoords="offset points")
    ax.annotate("真目标", (0.0, 200.0), xytext=(7, -4), textcoords="offset points")
    ax.set_xlabel("$x$ / km")
    ax.set_ylabel("$y$ / m")
    ax.set_title(f"(a) Q1 有效区间中点的平面位置（$t={time:.3f}$ s）", loc="left")
    ax.grid(True, color="#E8E8E8", linewidth=0.6)
    ax.margins(x=0.04, y=0.12)

    observer = missile
    axis = target_center - observer
    axis /= np.linalg.norm(axis)
    transverse_1 = np.cross(np.array([0.0, 0.0, 1.0]), axis)
    transverse_1 /= np.linalg.norm(transverse_1)
    transverse_2 = np.cross(axis, transverse_1)
    points = cylinder_surface()
    segment = points - observer
    cloud_vector = cloud - observer
    fractions = np.sum(segment * cloud_vector, axis=1) / np.sum(segment**2, axis=1)
    fractions = np.clip(fractions, 0.0, 1.0)
    nearest = observer + fractions[:, None] * segment
    offsets = nearest - cloud
    projection = np.column_stack((offsets @ transverse_1, offsets @ transverse_2))
    distances = np.linalg.norm(offsets, axis=1)

    ax = axes[1]
    hull = ConvexHull(projection)
    hull_points = projection[hull.vertices]
    ax.fill(hull_points[:, 0], hull_points[:, 1], color=COLORS["orange"], alpha=0.45,
            label="完整圆柱视线束的最近点投影")
    ax.scatter(projection[::40, 0], projection[::40, 1], s=6, color=COLORS["orange"], alpha=0.8)
    ax.add_patch(Circle((0.0, 0.0), 10.0, facecolor=COLORS["sky"], edgecolor=COLORS["blue"],
                        linewidth=1.4, alpha=0.25, label="有效烟幕截面（半径 10 m）"))
    ax.scatter(0.0, 0.0, s=20, color=COLORS["blue"], zorder=4)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-11.0, 11.0)
    ax.set_ylim(-11.0, 11.0)
    ax.set_xlabel("横向投影 / m")
    ax.set_ylabel("竖向投影 / m")
    ax.set_title("(b) 云团附近的完整目标视线束截面", loc="left")
    ax.text(0.03, 0.93, f"最大三维线段距离：{distances.max():.2f} m",
            transform=ax.transAxes, color=COLORS["gray"], va="top",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 1.5})
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False, ncol=1)
    ax.grid(True, color="#ECECEC", linewidth=0.6)
    save(fig, "fig1_shielding_geometry")


def draw_intervals(ax: plt.Axes, rows: list[tuple[str, list[list[float]], str]], union: list[list[float]]) -> None:
    labels = [label for label, _, _ in rows] + ["并集"]
    for y, (_, intervals, color) in enumerate(rows):
        for left, right in intervals:
            ax.broken_barh([(left, right - left)], (y - 0.32, 0.64), facecolors=color, alpha=0.82)
    union_y = len(rows)
    for left, right in union:
        ax.broken_barh([(left, right - left)], (union_y - 0.32, 0.64),
                       facecolors=COLORS["gray"], alpha=0.88)
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.grid(axis="x", color="#E8E8E8", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_xlabel("时间 / s")


def figure_intervals() -> None:
    q1, q3, q4 = (load_frozen(name) for name in ("q1.json", "q3.json", "q4.json"))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.0), constrained_layout=True)
    left, right = q1["shielding_intervals_s"][0]
    axes[0].broken_barh([(left, right - left)], (-0.32, 0.64), facecolors=COLORS["blue"], alpha=0.82)
    axes[0].set_yticks([0], ["有效遮蔽"])
    axes[0].grid(axis="x", color="#E8E8E8", linewidth=0.6)
    axes[0].set_axisbelow(True)
    axes[0].set_xlabel("时间 / s")
    axes[0].set_title(f"(a) Q1：单弹 {q1['effective_shielding_duration_s']:.3f} s", loc="left")

    rows3 = [
        (f"烟幕弹 {bomb['bomb']}", bomb["shielding_intervals_s"], color)
        for bomb, color in zip(q3["bombs"], (COLORS["blue"], COLORS["orange"], COLORS["green"]), strict=True)
    ]
    draw_intervals(axes[1], rows3, q3["union_intervals_s"])
    axes[1].set_title(f"(b) Q3：三弹并集 {q3['effective_shielding_duration_s']:.3f} s", loc="left")

    rows4 = [
        (record["drone"], record["shielding_intervals_s"], DRONE_COLORS[record["drone"]])
        for record in q4["records"]
    ]
    draw_intervals(axes[2], rows4, q4["union_intervals_s"])
    axes[2].set_title(f"(c) Q4：三机并集 {q4['effective_shielding_duration_s']:.3f} s", loc="left")
    save(fig, "fig2_q1_q3_q4_intervals")


def figure_q5() -> None:
    q5 = load_frozen("q5.json")
    records = q5["records"]
    grouped = {
        missile: [record for record in records if record["assigned_missile"] == missile]
        for missile in ("M1", "M2", "M3")
    }
    heights = [len(grouped[name]) + 1 for name in ("M1", "M2", "M3")]
    fig = plt.figure(figsize=(7.2, 5.3), constrained_layout=True)
    grid = fig.add_gridspec(3, 2, width_ratios=(3.8, 1.25), height_ratios=heights)
    timeline_axes = [fig.add_subplot(grid[index, 0]) for index in range(3)]
    heat_ax = fig.add_subplot(grid[:, 1])

    for index, (missile_name, ax) in enumerate(zip(("M1", "M2", "M3"), timeline_axes, strict=True)):
        rows = grouped[missile_name]
        union = q5["formal_b1"]["per_missile_union_intervals_s"][missile_name]
        for left, right in union:
            ax.broken_barh([(left, right - left)], (-0.32, 0.64),
                           facecolors=COLORS["light"], edgecolors=COLORS["gray"], linewidth=0.7)
        for row_index, record in enumerate(rows, 1):
            for left, right in record["assigned_target_intervals_s"]:
                ax.broken_barh(
                    [(left, right - left)],
                    (row_index - 0.32, 0.64),
                    facecolors=DRONE_COLORS[record["drone"]],
                    alpha=0.86,
                )
        labels = ["并集"] + [f"{record['drone']}-{record['bomb']}" for record in rows]
        ax.set_yticks(range(len(labels)), labels)
        ax.invert_yaxis()
        ax.set_xlim(0.0, 41.0)
        ax.grid(axis="x", color="#E8E8E8", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_title(
            f"{missile_name}：$L={q5['formal_b1']['per_missile_durations_s'][missile_name]:.3f}$ s",
            loc="left",
        )
        if index < 2:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xlabel("时间 / s")

    counts = np.array(
        [[sum(record["drone"] == drone and record["assigned_missile"] == missile for record in records)
          for missile in ("M1", "M2", "M3")] for drone in DRONE_COLORS]
    )
    image = heat_ax.imshow(counts, cmap=mpl.colors.ListedColormap(["#F2F2F2", "#B8D8EB", "#56B4E9", "#0072B2"]),
                           vmin=0, vmax=3, aspect="auto")
    del image
    heat_ax.set_xticks(range(3), ["M1", "M2", "M3"])
    heat_ax.set_yticks(range(5), list(DRONE_COLORS))
    heat_ax.set_title(f"资源指派（枚）\nB1 总目标 {q5['formal_b1']['objective_sum_s']:.3f} s")
    for row in range(5):
        for column in range(3):
            heat_ax.text(column, row, str(counts[row, column]), ha="center", va="center",
                         color="white" if counts[row, column] >= 2 else "#333333", fontweight="bold")
    heat_ax.set_xticks(np.arange(-0.5, 3, 1), minor=True)
    heat_ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    heat_ax.grid(which="minor", color="white", linewidth=1.2)
    heat_ax.tick_params(which="minor", bottom=False, left=False)

    save(fig, "fig3_q5_timeline_allocation")


def main() -> None:
    setup_style()
    figure_geometry()
    figure_intervals()
    figure_q5()
    print("generated three frozen-result-only figures in PNG and PDF")


if __name__ == "__main__":
    main()
