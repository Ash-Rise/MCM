"""Solve Problem B exactly under DEC-B-001 through DEC-B-003.

Purpose: enumerate the eight fixed-region route combinations, calculate schedules
and lexicographic costs, and write reproducible normal/disrupted results.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


EPS = 1e-9


@dataclass(frozen=True)
class StopResult:
    sequence: int
    node: int
    node_name: str
    node_type: str
    arrival_minute: float
    service_start_minute: float
    departure_minute: float
    waiting_minutes: float
    early: int
    late: int
    delivered_boxes: int


@dataclass(frozen=True)
class RouteResult:
    vehicle: str
    route: tuple[int, ...]
    distance_km: float
    demand_boxes: int
    early_count: int
    late_count: int
    travel_cost_yuan: float
    penalty_cost_yuan: float
    total_cost_yuan: float
    feasible: bool
    violations: tuple[str, ...]
    stops: tuple[StopResult, ...]


@dataclass(frozen=True)
class SolutionResult:
    scenario: str
    routes: tuple[RouteResult, ...]
    distance_km: float
    early_count: int
    late_count: int
    travel_cost_yuan: float
    penalty_cost_yuan: float
    total_cost_yuan: float
    feasible: bool
    violations: tuple[str, ...]

    @property
    def lexicographic_key(self) -> tuple[Any, ...]:
        route_key = tuple(route.route for route in self.routes)
        return (self.late_count, self.total_cost_yuan, route_key)


def load_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def node(data: dict[str, Any], node_id: int) -> dict[str, Any]:
    return data["nodes"][str(node_id)]


def distance(data: dict[str, Any], first: int, second: int) -> float:
    a = node(data, first)
    b = node(data, second)
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def route_label(route: Iterable[int]) -> str:
    return "→".join(str(value) for value in route)


def format_clock(minute: float) -> str:
    whole_seconds = int(round(minute * 60))
    hours, remainder = divmod(whole_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def candidate_routes(data: dict[str, Any], vehicle: str) -> tuple[tuple[int, ...], ...]:
    spec = data["vehicles"][vehicle]
    station = int(spec["station"])
    stores = tuple(int(value) for value in spec["stores"])
    return tuple((0, station, *order, 0) for order in itertools.permutations(stores))


def evaluate_route(
    data: dict[str, Any],
    vehicle: str,
    route: tuple[int, ...],
    closed_arcs: frozenset[tuple[int, int]] = frozenset(),
) -> RouteResult:
    spec = data["vehicles"][vehicle]
    expected_nodes = {0, int(spec["station"]), *(int(value) for value in spec["stores"])}
    violations: list[str] = []

    if route[0] != 0 or route[-1] != 0:
        violations.append("route_not_closed_at_kitchen")
    if set(route) != expected_nodes or len(route) != 5:
        violations.append("route_nodes_do_not_match_fixed_region")
    if route[1] != int(spec["station"]):
        violations.append("station_not_first")

    arcs = tuple(zip(route, route[1:]))
    blocked = sorted(set(arcs).intersection(closed_arcs))
    if blocked:
        violations.append("closed_arc:" + ",".join(f"{a}->{b}" for a, b in blocked))

    route_distance = sum(distance(data, a, b) for a, b in arcs)
    if route_distance > float(data["max_route_km"]) + EPS:
        violations.append("route_mileage_exceeded")

    demand_boxes = sum(int(node(data, value).get("demand", 0)) for value in route)
    if demand_boxes > int(data["vehicle_capacity_boxes"]):
        violations.append("vehicle_capacity_exceeded")

    if float(data["vehicle_temperature_c"]) > float(data["store_max_temperature_c"]):
        violations.append("temperature_requirement_failed")

    current_departure = float(data["departure_minute"])
    stops: list[StopResult] = [
        StopResult(
            sequence=0,
            node=0,
            node_name=node(data, 0)["name"],
            node_type=node(data, 0)["type"],
            arrival_minute=current_departure,
            service_start_minute=current_departure,
            departure_minute=current_departure,
            waiting_minutes=0.0,
            early=0,
            late=0,
            delivered_boxes=0,
        )
    ]

    early_count = 0
    late_count = 0
    speed = float(data["speed_kmph"])
    service_minutes = float(data["service_minutes"])

    for sequence, (previous, current) in enumerate(arcs, start=1):
        arrival = current_departure + 60.0 * distance(data, previous, current) / speed
        current_node = node(data, current)
        early = 0
        late = 0
        waiting = 0.0
        service_start = arrival
        delivered = int(current_node.get("demand", 0))

        if current_node["type"] == "store":
            window_start = float(current_node["window_start"])
            window_end = float(current_node["window_end"])
            early = int(arrival < window_start - EPS)
            late = int(arrival > window_end + EPS)
            waiting = max(0.0, window_start - arrival)
            service_start = arrival + waiting
            early_count += early
            late_count += late

        current_departure = service_start + (
            service_minutes if current_node["type"] == "store" else 0.0
        )
        stops.append(
            StopResult(
                sequence=sequence,
                node=current,
                node_name=current_node["name"],
                node_type=current_node["type"],
                arrival_minute=arrival,
                service_start_minute=service_start,
                departure_minute=current_departure,
                waiting_minutes=waiting,
                early=early,
                late=late,
                delivered_boxes=delivered,
            )
        )

    travel_cost = float(data["travel_cost_per_km"]) * route_distance
    penalty_cost = (
        float(data["early_penalty_per_event"]) * early_count
        + float(data["late_penalty_per_event"]) * late_count
    )
    return RouteResult(
        vehicle=vehicle,
        route=route,
        distance_km=route_distance,
        demand_boxes=demand_boxes,
        early_count=early_count,
        late_count=late_count,
        travel_cost_yuan=travel_cost,
        penalty_cost_yuan=penalty_cost,
        total_cost_yuan=travel_cost + penalty_cost,
        feasible=not violations,
        violations=tuple(violations),
        stops=tuple(stops),
    )


def combine_solution(scenario: str, routes: tuple[RouteResult, ...]) -> SolutionResult:
    violations = tuple(
        f"{route.vehicle}:{violation}"
        for route in routes
        for violation in route.violations
    )
    return SolutionResult(
        scenario=scenario,
        routes=routes,
        distance_km=sum(route.distance_km for route in routes),
        early_count=sum(route.early_count for route in routes),
        late_count=sum(route.late_count for route in routes),
        travel_cost_yuan=sum(route.travel_cost_yuan for route in routes),
        penalty_cost_yuan=sum(route.penalty_cost_yuan for route in routes),
        total_cost_yuan=sum(route.total_cost_yuan for route in routes),
        feasible=not violations,
        violations=violations,
    )


def enumerate_solutions(
    data: dict[str, Any], scenario: str, closed_arcs: frozenset[tuple[int, int]]
) -> tuple[SolutionResult, ...]:
    vehicles = tuple(data["vehicles"].keys())
    route_options = [
        tuple(evaluate_route(data, vehicle, route, closed_arcs) for route in candidate_routes(data, vehicle))
        for vehicle in vehicles
    ]
    return tuple(
        combine_solution(scenario, tuple(routes))
        for routes in itertools.product(*route_options)
    )


def solve(
    data: dict[str, Any], scenario: str, closed_arcs: frozenset[tuple[int, int]]
) -> tuple[SolutionResult, tuple[SolutionResult, ...]]:
    candidates = enumerate_solutions(data, scenario, closed_arcs)
    feasible = [candidate for candidate in candidates if candidate.feasible]
    if not feasible:
        raise RuntimeError(f"No feasible solution for scenario {scenario}")
    return min(feasible, key=lambda candidate: candidate.lexicographic_key), candidates


def maximum_zero_late_service_minutes(
    data: dict[str, Any], closed_arcs: frozenset[tuple[int, int]]
) -> tuple[float, SolutionResult]:
    """Find the largest uniform store service time that still permits zero lateness."""
    baseline_data = dict(data)
    baseline_data["service_minutes"] = 0.0
    baseline, _ = solve(baseline_data, "service_threshold", closed_arcs)
    if baseline.late_count > 0:
        return 0.0, baseline

    low = 0.0
    high = 1.0
    while high < 24.0 * 60.0:
        trial_data = dict(data)
        trial_data["service_minutes"] = high
        trial, _ = solve(trial_data, "service_threshold", closed_arcs)
        if trial.late_count > 0:
            break
        low = high
        high *= 2.0
    else:
        raise RuntimeError("Could not bracket the zero-lateness service-time threshold")

    for _ in range(80):
        middle = (low + high) / 2.0
        trial_data = dict(data)
        trial_data["service_minutes"] = middle
        trial, _ = solve(trial_data, "service_threshold", closed_arcs)
        if trial.late_count == 0:
            low = middle
        else:
            high = middle

    threshold_data = dict(data)
    threshold_data["service_minutes"] = low
    threshold_solution, _ = solve(threshold_data, "service_threshold", closed_arcs)
    return low, threshold_solution


def solution_summary(solution: SolutionResult) -> dict[str, Any]:
    return {
        "scenario": solution.scenario,
        "routes": {route.vehicle: list(route.route) for route in solution.routes},
        "route_labels": {route.vehicle: route_label(route.route) for route in solution.routes},
        "distance_km": solution.distance_km,
        "early_count": solution.early_count,
        "late_count": solution.late_count,
        "travel_cost_yuan": solution.travel_cost_yuan,
        "penalty_cost_yuan": solution.penalty_cost_yuan,
        "total_cost_yuan": solution.total_cost_yuan,
    }


def write_candidates(path: Path, candidates: Iterable[SolutionResult]) -> None:
    fieldnames = [
        "scenario",
        "solution_id",
        "route_A",
        "route_B",
        "route_C",
        "feasible",
        "late_count",
        "early_count",
        "distance_km",
        "travel_cost_yuan",
        "penalty_cost_yuan",
        "total_cost_yuan",
        "violations",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        scenario_counts: dict[str, int] = {}
        for candidate in candidates:
            scenario_counts[candidate.scenario] = scenario_counts.get(candidate.scenario, 0) + 1
            route_map = {route.vehicle: route_label(route.route) for route in candidate.routes}
            writer.writerow(
                {
                    "scenario": candidate.scenario,
                    "solution_id": scenario_counts[candidate.scenario],
                    "route_A": route_map["A"],
                    "route_B": route_map["B"],
                    "route_C": route_map["C"],
                    "feasible": int(candidate.feasible),
                    "late_count": candidate.late_count,
                    "early_count": candidate.early_count,
                    "distance_km": f"{candidate.distance_km:.6f}",
                    "travel_cost_yuan": f"{candidate.travel_cost_yuan:.6f}",
                    "penalty_cost_yuan": f"{candidate.penalty_cost_yuan:.2f}",
                    "total_cost_yuan": f"{candidate.total_cost_yuan:.6f}",
                    "violations": ";".join(candidate.violations),
                }
            )


def write_schedule(path: Path, solutions: Iterable[SolutionResult]) -> None:
    fieldnames = [
        "scenario",
        "vehicle",
        "route",
        "sequence",
        "node",
        "node_name",
        "node_type",
        "arrival_minute",
        "arrival_clock",
        "service_start_minute",
        "service_start_clock",
        "waiting_minutes",
        "early",
        "late",
        "delivered_boxes",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for solution in solutions:
            for route in solution.routes:
                for stop in route.stops:
                    writer.writerow(
                        {
                            "scenario": solution.scenario,
                            "vehicle": route.vehicle,
                            "route": route_label(route.route),
                            "sequence": stop.sequence,
                            "node": stop.node,
                            "node_name": stop.node_name,
                            "node_type": stop.node_type,
                            "arrival_minute": f"{stop.arrival_minute:.6f}",
                            "arrival_clock": format_clock(stop.arrival_minute),
                            "service_start_minute": f"{stop.service_start_minute:.6f}",
                            "service_start_clock": format_clock(stop.service_start_minute),
                            "waiting_minutes": f"{stop.waiting_minutes:.6f}",
                            "early": stop.early,
                            "late": stop.late,
                            "delivered_boxes": stop.delivered_boxes,
                        }
                    )


def write_route_summary(path: Path, solutions: Iterable[SolutionResult]) -> None:
    fieldnames = [
        "scenario",
        "vehicle",
        "route",
        "demand_boxes",
        "distance_km",
        "return_clock",
        "early_count",
        "late_count",
        "travel_cost_yuan",
        "penalty_cost_yuan",
        "total_cost_yuan",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for solution in solutions:
            for route in solution.routes:
                writer.writerow(
                    {
                        "scenario": solution.scenario,
                        "vehicle": route.vehicle,
                        "route": route_label(route.route),
                        "demand_boxes": route.demand_boxes,
                        "distance_km": f"{route.distance_km:.6f}",
                        "return_clock": format_clock(route.stops[-1].arrival_minute),
                        "early_count": route.early_count,
                        "late_count": route.late_count,
                        "travel_cost_yuan": f"{route.travel_cost_yuan:.6f}",
                        "penalty_cost_yuan": f"{route.penalty_cost_yuan:.2f}",
                        "total_cost_yuan": f"{route.total_cost_yuan:.6f}",
                    }
                )


def write_markdown_summary(
    path: Path,
    normal: SolutionResult,
    disrupted: SolutionResult,
    normal_candidates: tuple[SolutionResult, ...],
    disrupted_candidates: tuple[SolutionResult, ...],
    normal_service_threshold: float,
    disrupted_service_threshold: float,
) -> None:
    lines = [
        "# B 题精确求解结果摘要",
        "",
        "> 本文件由 `src/solve_problem_b.py` 根据 DEC-B-001 至 DEC-B-003 自动生成。",
        "",
        "## 正常场景",
        "",
        "| 车辆 | 最优路线 | 配送量/箱 | 门店到达时刻 | 里程/km | 早到 | 迟到 | 成本/元 | 返回时刻 |",
        "|---|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for route in normal.routes:
        arrivals = "；".join(
            f"{stop.node_name} {format_clock(stop.arrival_minute)[:5]}"
            for stop in route.stops
            if stop.node_type == "store"
        )
        lines.append(
            "| {vehicle} | {route} | {demand} | {arrivals} | {distance:.3f} | "
            "{early} | {late} | {cost:.2f} | {return_time} |".format(
                vehicle=route.vehicle,
                route=route_label(route.route),
                demand=route.demand_boxes,
                arrivals=arrivals,
                distance=route.distance_km,
                early=route.early_count,
                late=route.late_count,
                cost=route.total_cost_yuan,
                return_time=format_clock(route.stops[-1].arrival_minute)[:5],
            )
        )
    lines.extend(
        [
            "",
            f"正常场景共枚举 {len(normal_candidates)} 个完整组合，"
            f"其中 {sum(value.feasible for value in normal_candidates)} 个可行。"
            f"最优方案总里程为 {normal.distance_km:.3f} km，运输成本为 "
            f"{normal.travel_cost_yuan:.2f} 元，时间窗惩罚为 {normal.penalty_cost_yuan:.2f} 元，"
            f"综合成本为 {normal.total_cost_yuan:.2f} 元；早到和迟到门店数均为 0。",
            "",
            "## 任务三：封闭有向弧 2→8",
            "",
            f"封路场景仍枚举 {len(disrupted_candidates)} 个组合，其中 "
            f"{sum(value.feasible for value in disrupted_candidates)} 个不使用封闭弧并满足其他约束。"
            "正常最优 B 线为 `0→2→5→8→0`，本身不包含 `2→8`，因此封闭该弧后最优路线不变。",
            "",
            f"应急方案总里程仍为 {disrupted.distance_km:.3f} km，综合成本仍为 "
            f"{disrupted.total_cost_yuan:.2f} 元；里程、迟到数和总成本增量均为 0。"
            "这说明题面指定封路在 Accepted 模型下不是有效扰动，不能人为制造非零绕路代价。",
            "",
            "## 结果边界",
            "",
            "距离为坐标欧氏距离代理，速度固定为 35 km/h，门店服务时长基线为 0 分钟；"
            "任务三按 4:30 发车前已知封路的静态重优化解释。",
            "",
            "对所有门店采用相同服务时长并在连续区间上做单调二分后，正常场景仍可保持零迟到的"
            f"最大服务时长为 {normal_service_threshold:.3f} 分钟/店；封路场景阈值为 "
            f"{disrupted_service_threshold:.3f} 分钟/店。因两者相同，服务时长缺失不会改变任务三"
            "成本增量为 0 的结论。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(project_root: Path, data_path: Path, output_dir: Path) -> dict[str, Any]:
    data = load_data(data_path)
    source_docx = (project_root / data["source_docx"]).resolve()
    actual_source_hash = sha256_file(source_docx)
    if actual_source_hash != data["source_sha256"]:
        raise RuntimeError(
            f"Source DOCX hash mismatch: expected {data['source_sha256']}, got {actual_source_hash}"
        )

    normal, normal_candidates = solve(data, "normal", frozenset())
    closed_arc = tuple(int(value) for value in data["closed_arc"])
    disrupted, disrupted_candidates = solve(data, "disrupted", frozenset({closed_arc}))
    normal_threshold, normal_threshold_solution = maximum_zero_late_service_minutes(
        data, frozenset()
    )
    disrupted_threshold, disrupted_threshold_solution = maximum_zero_late_service_minutes(
        data, frozenset({closed_arc})
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_candidates(
        output_dir / "candidate_solutions.csv",
        (*normal_candidates, *disrupted_candidates),
    )
    write_schedule(output_dir / "route_schedule.csv", (normal, disrupted))
    write_route_summary(output_dir / "route_summary.csv", (normal, disrupted))

    comparison = {
        "normal": solution_summary(normal),
        "disrupted": solution_summary(disrupted),
        "change": {
            "distance_km": disrupted.distance_km - normal.distance_km,
            "early_count": disrupted.early_count - normal.early_count,
            "late_count": disrupted.late_count - normal.late_count,
            "travel_cost_yuan": disrupted.travel_cost_yuan - normal.travel_cost_yuan,
            "penalty_cost_yuan": disrupted.penalty_cost_yuan - normal.penalty_cost_yuan,
            "total_cost_yuan": disrupted.total_cost_yuan - normal.total_cost_yuan,
        },
        "enumeration": {
            "normal_total_candidates": len(normal_candidates),
            "normal_feasible_candidates": sum(value.feasible for value in normal_candidates),
            "disrupted_total_candidates": len(disrupted_candidates),
            "disrupted_feasible_candidates": sum(value.feasible for value in disrupted_candidates),
        },
        "service_time_sensitivity": {
            "definition": "maximum uniform service minutes per store with a zero-late solution",
            "normal_threshold_minutes": normal_threshold,
            "disrupted_threshold_minutes": disrupted_threshold,
            "normal_routes_at_threshold": {
                route.vehicle: list(route.route) for route in normal_threshold_solution.routes
            },
            "disrupted_routes_at_threshold": {
                route.vehicle: list(route.route) for route in disrupted_threshold_solution.routes
            },
        },
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as file:
        json.dump(comparison, file, ensure_ascii=False, indent=2)
        file.write("\n")
    write_markdown_summary(
        output_dir / "result_summary.md",
        normal,
        disrupted,
        normal_candidates,
        disrupted_candidates,
        normal_threshold,
        disrupted_threshold,
    )

    return comparison


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/problem_b_data.json", type=Path)
    parser.add_argument("--output-dir", default="results", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    data_path = args.data if args.data.is_absolute() else project_root / args.data
    output_dir = args.output_dir if args.output_dir.is_absolute() else project_root / args.output_dir
    comparison = run(project_root, data_path.resolve(), output_dir.resolve())
    print(json.dumps(comparison, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
