from __future__ import annotations

import csv
import heapq
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path


REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."

BASE_WORKSPACE_ID = "safe_access_kfar_saba_pbf_enriched_v001"
ROUTE_WORKSPACE_ID = "safe_access_kfar_saba_route_aware_v001"

NETWORK_INCLUDED_CLASSES = {
    "cycleway",
    "footway",
    "living_street",
    "path",
    "pedestrian",
    "primary",
    "primary_link",
    "residential",
    "secondary",
    "secondary_link",
    "service",
    "steps",
    "tertiary",
    "tertiary_link",
    "unclassified",
}

NETWORK_EXCLUDED_CLASSES = {
    "motorway",
    "motorway_link",
    "track",
    "track_grade1",
    "trunk",
    "trunk_link",
    "unknown",
}

NETWORK_FIELDNAMES = [
    "generator_id",
    "osm_id",
    "generator_type",
    "name",
    "base_risk_score",
    "route_review_priority_score",
    "straight_nearest_crossing_id",
    "straight_nearest_crossing_m",
    "route_nearest_crossing_id",
    "route_nearest_crossing_m",
    "straight_distance_to_route_crossing_m",
    "route_vs_straight_ratio",
    "route_gap_m",
    "reachable_crossings",
    "generator_network_attach_m",
    "generator_network_road_id",
    "generator_network_road_class",
    "crossing_network_attach_m",
    "crossing_network_road_id",
    "crossing_network_road_class",
    "network_status",
    "network_flags",
    "data_quality_flags",
    "review_wording",
    "geometry_wkt",
    "lon",
    "lat",
]


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_number(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_json_array(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def dump_json_array(values: list[str]) -> str:
    return json.dumps(sorted(set(values)), ensure_ascii=False)


def parse_point_wkt(wkt: str) -> tuple[float, float] | None:
    text = (wkt or "").strip()
    if not text.startswith("POINT"):
        return None
    body = text[text.find("(") + 1:text.rfind(")")]
    parts = body.strip().split()
    if len(parts) < 2:
        return None
    return parse_number(parts[0]), parse_number(parts[1])


def parse_linestring_wkt(wkt: str) -> list[tuple[float, float]]:
    text = (wkt or "").strip()
    if not text.startswith("LINESTRING"):
        return []
    body = text[text.find("(") + 1:text.rfind(")")]
    points: list[tuple[float, float]] = []
    for part in body.split(","):
        bits = part.strip().split()
        if len(bits) >= 2:
            points.append((parse_number(bits[0]), parse_number(bits[1])))
    return points


def node_key(point: tuple[float, float]) -> str:
    return f"{point[0]:.3f},{point[1]:.3f}"


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_segment_metrics(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
) -> tuple[float, float, float, float]:
    ax, ay = a
    bx, by = b
    px, py = point
    dx = bx - ax
    dy = by - ay
    length_sq = dx * dx + dy * dy
    if length_sq <= 0:
        dist = distance(point, a)
        return dist, 0.0, 0.0, 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    proj = (ax + t * dx, ay + t * dy)
    seg_len = math.sqrt(length_sq)
    return distance(point, proj), t, t * seg_len, (1.0 - t) * seg_len


class RouteNetworkAnalyzer:
    def __init__(self, workspaces_dir: Path, review_wording: str = REVIEW_WORDING) -> None:
        self.workspaces_dir = workspaces_dir
        self.review_wording = review_wording

    def ensure_route_aware_workspace(
        self,
        base_workspace_id: str = BASE_WORKSPACE_ID,
        workspace_id: str = ROUTE_WORKSPACE_ID,
    ) -> dict:
        target_dir = self.workspaces_dir / workspace_id
        manifest_path = target_dir / "manifest.json"
        network_table = target_dir / "tables" / "network_access_results.csv"
        if manifest_path.exists() and network_table.exists():
            return {
                "ok": True,
                "created": False,
                "workspace": self.workspace_detail(workspace_id),
            }

        base_dir = self.workspaces_dir / base_workspace_id
        base_manifest_path = base_dir / "manifest.json"
        if not base_manifest_path.exists():
            return {
                "ok": False,
                "error": "base_workspace_not_found",
                "base_workspace_id": base_workspace_id,
                "workspace_id": workspace_id,
            }

        target_dir.mkdir(parents=True, exist_ok=True)
        tables_dir = target_dir / "tables"
        reports_dir = target_dir / "reports"
        tables_dir.mkdir(exist_ok=True)
        reports_dir.mkdir(exist_ok=True)

        for source_file in (base_dir / "tables").glob("*.csv"):
            target_file = tables_dir / source_file.name
            if not target_file.exists():
                shutil.copy2(source_file, target_file)
        for source_file in (base_dir / "reports").glob("*"):
            if source_file.is_file():
                target_file = reports_dir / source_file.name
                if not target_file.exists():
                    shutil.copy2(source_file, target_file)

        analysis = self.compute_network_analysis(base_dir)
        if not analysis.get("ok"):
            return analysis

        network_rows = analysis["rows"]
        network_rows.sort(
            key=lambda row: (
                -parse_int(row.get("route_review_priority_score")),
                -parse_number(row.get("route_nearest_crossing_m")),
                -parse_number(row.get("route_vs_straight_ratio")),
            )
        )
        write_csv_rows(tables_dir / "network_access_results.csv", NETWORK_FIELDNAMES, network_rows)
        write_csv_rows(tables_dir / "network_access_top20.csv", NETWORK_FIELDNAMES, network_rows[:20])

        base_summary = read_json(base_dir / "reports" / "workspace_summary.json")
        base_quality = read_json(base_dir / "reports" / "quality_report.json")
        base_manifest = read_json(base_manifest_path)
        network_summary = analysis["summary"]

        workspace_summary = dict(base_summary)
        workspace_summary.update({
            "workspace_id": workspace_id,
            "created_from_workspace_id": base_workspace_id,
            "route_aware_analysis": network_summary,
        })
        write_json(reports_dir / "workspace_summary.json", workspace_summary)

        quality_report = dict(base_quality)
        limitations = list(quality_report.get("known_limitations", []))
        limitations.extend([
            "Route-aware metrics are an OSM road-network proxy, not verified pedestrian routing.",
            "The graph is built from simplified road segment geometry and does not prove legal or accessible walking paths.",
            "Cycleway and surface-street classes are included as proxy network evidence where detailed sidewalk tags are incomplete.",
        ])
        quality_report.update({
            "workspace_id": workspace_id,
            "route_aware_quality_principles": [
                "Network distance is used as a review-priority indicator only.",
                "Straight-line and network distances should both be shown because the network graph is incomplete.",
                "Unreachable network results are data-quality flags unless confirmed on-site.",
            ],
            "known_limitations": sorted(set(limitations)),
        })
        write_json(reports_dir / "quality_report.json", quality_report)

        self._append_network_dictionary(reports_dir / "data_dictionary.csv")
        write_json(reports_dir / "network_analysis_summary.json", network_summary)
        (target_dir / "README.md").write_text(self._readme(workspace_id, base_workspace_id), encoding="utf-8")

        copied_tables = list(base_manifest.get("tables", []))
        copied_tables.extend([
            {
                "table": "network_access_results",
                "file": str(tables_dir / "network_access_results.csv"),
                "geometry": "Point",
                "role": "Route-aware proxy distance from each pedestrian generator to mapped crossings using the OSM road network.",
                "rows": len(network_rows),
            },
            {
                "table": "network_access_top20",
                "file": str(tables_dir / "network_access_top20.csv"),
                "geometry": "Point",
                "role": "Small route-aware priority extract for portfolio/reporting workflows.",
                "rows": min(20, len(network_rows)),
            },
        ])
        manifest = dict(base_manifest)
        manifest.update({
            "workspace_id": workspace_id,
            "created_by": "GeoReview Studio v024 route network analyzer",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "created_from_workspace_id": base_workspace_id,
            "source_gis_modified": False,
            "route_aware_analysis_used": True,
            "route_network_method": "road_segment_vertex_graph_with_edge_projection_attachments",
            "workspace_dir": str(target_dir),
            "tables_dir": str(tables_dir),
            "reports_dir": str(reports_dir),
            "tables": copied_tables,
            "reports": {
                **base_manifest.get("reports", {}),
                "workspace_summary": str(reports_dir / "workspace_summary.json"),
                "quality_report": str(reports_dir / "quality_report.json"),
                "data_dictionary": str(reports_dir / "data_dictionary.csv"),
                "network_analysis_summary": str(reports_dir / "network_analysis_summary.json"),
            },
        })
        write_json(manifest_path, manifest)
        return {
            "ok": True,
            "created": True,
            "workspace": self.workspace_detail(workspace_id),
        }

    def compute_network_analysis(self, base_workspace_dir: Path) -> dict:
        tables_dir = base_workspace_dir / "tables"
        generators = read_csv_rows(tables_dir / "pedestrian_generators.csv")
        crossings = read_csv_rows(tables_dir / "crossings.csv")
        roads = read_csv_rows(tables_dir / "road_segments.csv")
        risk_rows = read_csv_rows(tables_dir / "risk_assessment_results.csv")
        if not generators or not crossings or not roads or not risk_rows:
            return {
                "ok": False,
                "error": "missing_network_input_tables",
                "base_workspace_dir": str(base_workspace_dir),
            }

        network = self._build_network(roads)
        if not network["segments"]:
            return {
                "ok": False,
                "error": "empty_network_proxy",
                "base_workspace_dir": str(base_workspace_dir),
            }

        crossing_by_id = {row.get("crossing_id"): row for row in crossings}
        crossing_points = {
            row.get("crossing_id"): parse_point_wkt(row.get("geometry_wkt", ""))
            for row in crossings
        }
        crossing_attachments = {
            crossing_id: self._nearest_segment(point, network["segments"])
            for crossing_id, point in crossing_points.items()
            if crossing_id and point is not None
        }

        generator_points = {
            row.get("generator_id"): parse_point_wkt(row.get("geometry_wkt", ""))
            for row in generators
        }
        generator_by_id = {row.get("generator_id"): row for row in generators}
        rows: list[dict] = []
        reachable_counts: list[int] = []
        route_distances: list[float] = []
        detour_ratios: list[float] = []
        over_250 = 0
        high_detour = 0
        unreachable = 0
        far_attach = 0

        for risk in risk_rows:
            generator_id = risk.get("generator_id")
            generator = generator_by_id.get(generator_id, {})
            point = generator_points.get(generator_id)
            if point is None:
                rows.append(self._network_error_row(risk, generator, "missing_generator_geometry"))
                unreachable += 1
                continue

            source_attachment = self._nearest_segment(point, network["segments"])
            initial = [
                (source_attachment["a_key"], source_attachment["off_network_m"] + source_attachment["along_to_a_m"]),
                (source_attachment["b_key"], source_attachment["off_network_m"] + source_attachment["along_to_b_m"]),
            ]
            distances = self._dijkstra(network["adjacency"], initial)
            best: dict | None = None
            reachable = 0

            for crossing_id, attachment in crossing_attachments.items():
                candidates = []
                if attachment["a_key"] in distances:
                    candidates.append(distances[attachment["a_key"]] + attachment["along_to_a_m"])
                if attachment["b_key"] in distances:
                    candidates.append(distances[attachment["b_key"]] + attachment["along_to_b_m"])
                if not candidates:
                    continue
                reachable += 1
                route_m = attachment["off_network_m"] + min(candidates)
                if best is None or route_m < best["route_m"]:
                    crossing_point = crossing_points.get(crossing_id)
                    straight_to_route = distance(point, crossing_point) if crossing_point else 0.0
                    best = {
                        "crossing_id": crossing_id,
                        "route_m": route_m,
                        "straight_to_route_m": straight_to_route,
                        "attachment": attachment,
                    }

            reachable_counts.append(reachable)
            if best is None:
                rows.append(self._network_error_row(risk, generator, "no_reachable_crossing_on_network_proxy", source_attachment))
                unreachable += 1
                continue

            crossing = crossing_by_id.get(best["crossing_id"], {})
            route_m = best["route_m"]
            straight_to_route = best["straight_to_route_m"]
            ratio = route_m / straight_to_route if straight_to_route > 0 else 0.0
            route_gap = route_m - parse_number(risk.get("nearest_crossing_m"))
            route_distances.append(route_m)
            if ratio:
                detour_ratios.append(ratio)

            network_flags: list[str] = []
            data_quality_flags = parse_json_array(risk.get("data_quality_flags", "[]"))
            data_quality_flags.extend([
                "route_network_proxy_from_osm_roads_not_verified_walk_route",
                "motorway_trunk_track_classes_excluded_from_walk_proxy",
                "cycleway_class_included_as_proxy_may_overestimate_walk_access",
            ])
            if route_m > 250:
                network_flags.append("route_nearest_crossing_over_250m")
                over_250 += 1
            if ratio >= 1.8 and route_m > 150:
                network_flags.append("high_network_detour_ratio")
                high_detour += 1
            if source_attachment["off_network_m"] > 35:
                network_flags.append("generator_far_from_network_proxy")
                data_quality_flags.append("generator_far_from_mapped_network_proxy")
                far_attach += 1
            if best["attachment"]["off_network_m"] > 25:
                data_quality_flags.append("route_crossing_far_from_mapped_network_proxy")

            network_score = parse_int(risk.get("risk_score"))
            if route_m > 250:
                network_score += 20
            if ratio >= 1.8 and route_m > 150:
                network_score += 10
            if source_attachment["off_network_m"] > 35:
                network_score += 5

            rows.append({
                "generator_id": generator_id,
                "osm_id": risk.get("osm_id"),
                "generator_type": risk.get("generator_type"),
                "name": risk.get("name") or "",
                "base_risk_score": str(parse_int(risk.get("risk_score"))),
                "route_review_priority_score": str(network_score),
                "straight_nearest_crossing_id": risk.get("nearest_crossing_id"),
                "straight_nearest_crossing_m": f"{parse_number(risk.get('nearest_crossing_m')):.1f}",
                "route_nearest_crossing_id": best["crossing_id"],
                "route_nearest_crossing_m": f"{route_m:.1f}",
                "straight_distance_to_route_crossing_m": f"{straight_to_route:.1f}",
                "route_vs_straight_ratio": f"{ratio:.2f}" if ratio else "",
                "route_gap_m": f"{route_gap:.1f}",
                "reachable_crossings": str(reachable),
                "generator_network_attach_m": f"{source_attachment['off_network_m']:.1f}",
                "generator_network_road_id": source_attachment["road_id"],
                "generator_network_road_class": source_attachment["road_class"],
                "crossing_network_attach_m": f"{best['attachment']['off_network_m']:.1f}",
                "crossing_network_road_id": best["attachment"]["road_id"],
                "crossing_network_road_class": best["attachment"]["road_class"],
                "network_status": "ok",
                "network_flags": dump_json_array(network_flags),
                "data_quality_flags": dump_json_array(data_quality_flags),
                "review_wording": risk.get("review_wording") or self.review_wording,
                "geometry_wkt": risk.get("geometry_wkt") or generator.get("geometry_wkt") or "",
                "lon": risk.get("lon") or generator.get("lon") or "",
                "lat": risk.get("lat") or generator.get("lat") or "",
            })

        summary = {
            "method": "road_segment_vertex_graph_with_edge_projection_attachments",
            "method_plain_language": (
                "Each generator and crossing is attached to the nearest included OSM road segment, "
                "then shortest path distance is calculated across the road-segment graph."
            ),
            "analysis_crs": "EPSG:2039",
            "base_workspace_id": base_workspace_dir.name,
            "route_workspace_id": ROUTE_WORKSPACE_ID,
            "review_wording": self.review_wording,
            "rows": len(rows),
            "network_nodes": len(network["nodes"]),
            "network_edges": network["edge_count"],
            "network_segments": len(network["segments"]),
            "included_road_segments": network["included_road_segments"],
            "excluded_road_segments": network["excluded_road_segments"],
            "included_highway_classes": sorted(NETWORK_INCLUDED_CLASSES),
            "excluded_highway_classes": sorted(NETWORK_EXCLUDED_CLASSES),
            "route_reachable_generators": len(rows) - unreachable,
            "route_unreachable_generators": unreachable,
            "median_route_nearest_crossing_m": round(percentile(route_distances, 50), 1),
            "p90_route_nearest_crossing_m": round(percentile(route_distances, 90), 1),
            "generators_route_over_250m": over_250,
            "generators_high_detour_ratio": high_detour,
            "generators_far_from_network_proxy": far_attach,
            "median_reachable_crossings_per_generator": round(percentile([float(v) for v in reachable_counts], 50), 1),
            "median_route_vs_straight_ratio": round(percentile(detour_ratios, 50), 2),
            "p90_route_vs_straight_ratio": round(percentile(detour_ratios, 90), 2),
            "limitations": [
                "This is a mapped OSM road-network proxy, not verified pedestrian routing.",
                "Missing OSM sidewalks or access tags are not treated as proof that walking infrastructure is absent.",
                "Simplified road geometry can overestimate or underestimate actual walking distance.",
            ],
        }
        return {"ok": True, "rows": rows, "summary": summary}

    def workspace_detail(self, workspace_id: str) -> dict:
        workspace_dir = self.workspaces_dir / workspace_id
        manifest_path = workspace_dir / "manifest.json"
        if not manifest_path.exists():
            return {"error": "workspace_not_found", "workspace_id": workspace_id}
        reports_dir = workspace_dir / "reports"
        return {
            "manifest": read_json(manifest_path),
            "summary": read_json(reports_dir / "workspace_summary.json"),
            "quality_report": read_json(reports_dir / "quality_report.json"),
            "network_analysis": read_json(reports_dir / "network_analysis_summary.json"),
            "files": self._list_files(workspace_dir),
        }

    def _build_network(self, roads: list[dict]) -> dict:
        nodes: dict[str, tuple[float, float]] = {}
        adjacency: dict[str, list[tuple[str, float]]] = {}
        segments: list[dict] = []
        included_road_segments = 0
        excluded_road_segments = 0

        for row in roads:
            road_class = row.get("highway_class") or "unknown"
            if road_class not in NETWORK_INCLUDED_CLASSES:
                excluded_road_segments += 1
                continue
            points = parse_linestring_wkt(row.get("geometry_wkt", ""))
            if len(points) < 2:
                excluded_road_segments += 1
                continue
            included_road_segments += 1
            for a, b in zip(points, points[1:]):
                edge_len = distance(a, b)
                if edge_len <= 0:
                    continue
                a_key = node_key(a)
                b_key = node_key(b)
                nodes.setdefault(a_key, a)
                nodes.setdefault(b_key, b)
                adjacency.setdefault(a_key, []).append((b_key, edge_len))
                adjacency.setdefault(b_key, []).append((a_key, edge_len))
                segments.append({
                    "a": a,
                    "b": b,
                    "a_key": a_key,
                    "b_key": b_key,
                    "road_id": row.get("road_id") or "",
                    "road_class": road_class,
                    "length_m": edge_len,
                })

        return {
            "nodes": nodes,
            "adjacency": adjacency,
            "segments": segments,
            "edge_count": sum(len(edges) for edges in adjacency.values()) // 2,
            "included_road_segments": included_road_segments,
            "excluded_road_segments": excluded_road_segments,
        }

    def _nearest_segment(self, point: tuple[float, float], segments: list[dict]) -> dict:
        best: dict | None = None
        for segment in segments:
            off_network_m, _t, along_to_a_m, along_to_b_m = point_segment_metrics(point, segment["a"], segment["b"])
            if best is None or off_network_m < best["off_network_m"]:
                best = {
                    "off_network_m": off_network_m,
                    "along_to_a_m": along_to_a_m,
                    "along_to_b_m": along_to_b_m,
                    "a_key": segment["a_key"],
                    "b_key": segment["b_key"],
                    "road_id": segment["road_id"],
                    "road_class": segment["road_class"],
                }
        if best is None:
            raise ValueError("network segments are empty")
        return best

    @staticmethod
    def _dijkstra(adjacency: dict[str, list[tuple[str, float]]], initial: list[tuple[str, float]]) -> dict[str, float]:
        distances: dict[str, float] = {}
        heap: list[tuple[float, str]] = []
        for node, cost in initial:
            if node not in distances or cost < distances[node]:
                distances[node] = cost
                heapq.heappush(heap, (cost, node))
        while heap:
            current_cost, node = heapq.heappop(heap)
            if current_cost > distances.get(node, math.inf):
                continue
            for neighbor, edge_cost in adjacency.get(node, []):
                new_cost = current_cost + edge_cost
                if new_cost < distances.get(neighbor, math.inf):
                    distances[neighbor] = new_cost
                    heapq.heappush(heap, (new_cost, neighbor))
        return distances

    def _network_error_row(
        self,
        risk: dict,
        generator: dict,
        status: str,
        source_attachment: dict | None = None,
    ) -> dict:
        data_quality_flags = parse_json_array(risk.get("data_quality_flags", "[]"))
        data_quality_flags.append("route_network_proxy_unavailable_for_generator")
        network_flags = [status]
        return {
            "generator_id": risk.get("generator_id") or generator.get("generator_id"),
            "osm_id": risk.get("osm_id") or generator.get("osm_id"),
            "generator_type": risk.get("generator_type") or generator.get("generator_type"),
            "name": risk.get("name") or generator.get("name") or "",
            "base_risk_score": str(parse_int(risk.get("risk_score"))),
            # Network-proxy unreachability is a data-quality flag (the proxy graph may be
            # incomplete), not a risk indicator, so it adds no points. It is surfaced via
            # the data_quality_flag route_network_proxy_unavailable_for_generator below.
            "route_review_priority_score": str(parse_int(risk.get("risk_score"))),
            "straight_nearest_crossing_id": risk.get("nearest_crossing_id"),
            "straight_nearest_crossing_m": f"{parse_number(risk.get('nearest_crossing_m')):.1f}",
            "route_nearest_crossing_id": "",
            "route_nearest_crossing_m": "",
            "straight_distance_to_route_crossing_m": "",
            "route_vs_straight_ratio": "",
            "route_gap_m": "",
            "reachable_crossings": "0",
            "generator_network_attach_m": f"{source_attachment['off_network_m']:.1f}" if source_attachment else "",
            "generator_network_road_id": source_attachment["road_id"] if source_attachment else "",
            "generator_network_road_class": source_attachment["road_class"] if source_attachment else "",
            "crossing_network_attach_m": "",
            "crossing_network_road_id": "",
            "crossing_network_road_class": "",
            "network_status": status,
            "network_flags": dump_json_array(network_flags),
            "data_quality_flags": dump_json_array(data_quality_flags),
            "review_wording": risk.get("review_wording") or self.review_wording,
            "geometry_wkt": risk.get("geometry_wkt") or generator.get("geometry_wkt") or "",
            "lon": risk.get("lon") or generator.get("lon") or "",
            "lat": risk.get("lat") or generator.get("lat") or "",
        }

    @staticmethod
    def _append_network_dictionary(path: Path) -> None:
        existing = path.read_text(encoding="utf-8") if path.exists() else "table,field,required,reliability,notes\n"
        additions = [
            "network_access_results,route_nearest_crossing_m,yes,derived_network_proxy,Shortest path distance over the OSM road-network proxy in EPSG:2039 meters.",
            "network_access_results,route_vs_straight_ratio,no,derived_network_proxy,Ratio between proxy route distance and straight distance to the same crossing.",
            "network_access_results,network_status,yes,derived_network_proxy,ok or data-quality status explaining why a route proxy could not be calculated.",
            "network_access_results,network_flags,yes,derived,Infrastructure review-priority indicators from network proxy metrics.",
            "network_access_results,data_quality_flags,yes,derived,Network limitations and inherited OSM data-quality flags.",
        ]
        path.write_text(existing.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")

    @staticmethod
    def _list_files(root: Path) -> list[dict]:
        return [
            {
                "name": path.name,
                "relative_path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(root.rglob("*"))
            if path.is_file()
        ]

    @staticmethod
    def _readme(workspace_id: str, base_workspace_id: str) -> str:
        return (
            f"# Safe Access Kfar Saba Route-Aware Workspace\n\n"
            f"Workspace: `{workspace_id}`\n\n"
            f"Derived from `{base_workspace_id}` by GeoReview Studio v024.\n\n"
            "This workspace adds `network_access_results.csv`, a road-network proxy analysis for mapped crossing access.\n\n"
            f"Approved review wording: `{REVIEW_WORDING}`\n\n"
            "Source GIS files were not modified.\n"
        )


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * (q / 100.0)
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return ordered[int(pos)]
    weight = pos - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight
