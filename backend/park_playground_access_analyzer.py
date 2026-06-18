from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PARK_PLAYGROUND_ACCESS_ANALYZER_VERSION = "park_playground_access_analyzer_v001"
DEFAULT_PARK_PLAYGROUND_WORKSPACE_ID = "park_playground_access_kfar_saba_v001"
PUBLIC_SPACE_TYPES = {"park", "playground", "community_centre", "recreation_ground"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json_list(value: object) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


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


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def median(values: list[float]) -> float | None:
    clean = sorted(value for value in values if value > 0)
    if not clean:
        return None
    mid = len(clean) // 2
    if len(clean) % 2:
        return round(clean[mid], 1)
    return round((clean[mid - 1] + clean[mid]) / 2, 1)


class ParkPlaygroundAccessAnalyzer:
    def __init__(self, workspaces_dir: Path, review_wording: str) -> None:
        self.workspaces_dir = workspaces_dir
        self.review_wording = review_wording

    def ensure_workspace(
        self,
        base_workspace_id: str = "safe_access_kfar_saba_route_aware_v001",
        workspace_id: str = DEFAULT_PARK_PLAYGROUND_WORKSPACE_ID,
    ) -> dict:
        base_dir = self.workspaces_dir / base_workspace_id
        if not (base_dir / "manifest.json").exists():
            return {"ok": False, "error": "base_workspace_not_found", "base_workspace_id": base_workspace_id}

        tables_dir = base_dir / "tables"
        risk_rows = read_csv_rows(tables_dir / "risk_assessment_results.csv")
        network_rows = read_csv_rows(tables_dir / "network_access_results.csv")
        if not risk_rows:
            return {"ok": False, "error": "missing_profile_input_tables", "detail": "risk_assessment_results.csv is missing or empty"}
        network_by_generator = {row.get("generator_id"): row for row in network_rows if row.get("generator_id")}

        output_dir = self.workspaces_dir / workspace_id
        output_tables = output_dir / "tables"
        output_reports = output_dir / "reports"
        rows = []
        for risk in risk_rows:
            if risk.get("generator_type") not in PUBLIC_SPACE_TYPES:
                continue
            network = network_by_generator.get(risk.get("generator_id"), {})
            rows.append(self.public_space_row(risk, network))
        rows.sort(
            key=lambda row: (
                -parse_int(row.get("public_space_review_priority_score")),
                -parse_number(row.get("route_nearest_crossing_m")),
                -parse_number(row.get("nearest_crossing_m")),
            )
        )
        fieldnames = [
            "public_space_id",
            "osm_id",
            "place_type",
            "name",
            "source_layer",
            "nearest_crossing_id",
            "nearest_crossing_m",
            "crossing_within_100m",
            "crossing_within_150m",
            "route_nearest_crossing_id",
            "route_nearest_crossing_m",
            "route_vs_straight_ratio",
            "nearest_major_road_class",
            "nearest_major_road_m",
            "major_road_within_150m",
            "signals_within_50m",
            "traffic_calming_within_100m",
            "base_risk_score",
            "public_space_review_priority_score",
            "public_space_access_flags",
            "data_quality_flags",
            "review_wording",
            "geometry_wkt",
            "lon",
            "lat",
        ]
        results_path = output_tables / "park_playground_access_results.csv"
        top20_path = output_tables / "park_playground_access_top20.csv"
        summary_path = output_reports / "park_playground_access_summary.json"
        markdown_path = output_reports / "park_playground_access_summary.md"
        manifest_path = output_dir / "manifest.json"
        readme_path = output_dir / "README.md"

        write_csv(results_path, rows, fieldnames)
        write_csv(top20_path, rows[:20], fieldnames)
        summary = self.summary(rows, base_workspace_id, workspace_id)
        write_json(summary_path, summary)
        markdown_path.write_text(self.summary_markdown(summary, rows[:10]), encoding="utf-8")
        manifest = {
            "workspace_id": workspace_id,
            "profile_id": "park_playground_access",
            "profile_workspace": True,
            "base_workspace_id": base_workspace_id,
            "created_at_utc": utc_now(),
            "analyzer": PARK_PLAYGROUND_ACCESS_ANALYZER_VERSION,
            "source_gis_modified": False,
            "tables": [
                {"table": "park_playground_access_results", "file": str(results_path), "rows": len(rows)},
                {"table": "park_playground_access_top20", "file": str(top20_path), "rows": min(20, len(rows))},
            ],
            "reports": {
                "park_playground_access_summary": str(summary_path),
                "park_playground_access_markdown": str(markdown_path),
            },
        }
        write_json(manifest_path, manifest)
        readme_path.write_text(
            "# Park And Playground Access Workspace\n\n"
            f"Derived from `{base_workspace_id}` by GeoReview Studio.\n\n"
            "This workspace summarizes infrastructure review indicators around mapped parks, playgrounds, "
            "community centres, and recreation grounds. It does not predict crashes and does not prove "
            "real-world access conditions.\n",
            encoding="utf-8",
        )
        return {
            "ok": True,
            "created": True,
            "workspace": {
                "manifest": manifest,
                "summary": summary,
            },
            "source_gis_modified": False,
        }

    def public_space_row(self, risk: dict, network: dict) -> dict:
        route_m = parse_number(network.get("route_nearest_crossing_m"))
        straight_m = parse_number(risk.get("nearest_crossing_m"))
        base_score = parse_int(risk.get("risk_score"))
        route_score = parse_int(network.get("route_review_priority_score"), base_score)
        flags = self.public_space_flags(risk, network)
        quality_flags = sorted(set(read_json_list(risk.get("data_quality_flags")) + read_json_list(network.get("data_quality_flags"))))
        return {
            "public_space_id": risk.get("generator_id"),
            "osm_id": risk.get("osm_id"),
            "place_type": risk.get("generator_type"),
            "name": risk.get("name") or "",
            "source_layer": risk.get("source_layer") or "",
            "nearest_crossing_id": risk.get("nearest_crossing_id") or network.get("straight_nearest_crossing_id") or "",
            "nearest_crossing_m": round(straight_m, 1),
            "crossing_within_100m": risk.get("crossing_within_100m"),
            "crossing_within_150m": risk.get("crossing_within_150m"),
            "route_nearest_crossing_id": network.get("route_nearest_crossing_id") or "",
            "route_nearest_crossing_m": round(route_m, 1) if route_m else "",
            "route_vs_straight_ratio": network.get("route_vs_straight_ratio") or "",
            "nearest_major_road_class": risk.get("nearest_major_road_class") or "",
            "nearest_major_road_m": risk.get("nearest_major_road_m") or "",
            "major_road_within_150m": risk.get("major_road_within_150m"),
            "signals_within_50m": risk.get("signals_within_50m") or "",
            "traffic_calming_within_100m": risk.get("traffic_calming_within_100m") or "",
            "base_risk_score": base_score,
            "public_space_review_priority_score": max(base_score, route_score),
            "public_space_access_flags": json.dumps(flags, ensure_ascii=False),
            "data_quality_flags": json.dumps(quality_flags, ensure_ascii=False),
            "review_wording": risk.get("review_wording") or self.review_wording,
            "geometry_wkt": risk.get("geometry_wkt") or network.get("geometry_wkt") or "",
            "lon": risk.get("lon") or network.get("lon") or "",
            "lat": risk.get("lat") or network.get("lat") or "",
        }

    @staticmethod
    def public_space_flags(risk: dict, network: dict) -> list[str]:
        flags: list[str] = []
        if not boolish(risk.get("crossing_within_100m")):
            flags.append("no_mapped_crossing_within_100m")
        if not boolish(risk.get("crossing_within_150m")):
            flags.append("no_mapped_crossing_within_150m")
        if boolish(risk.get("major_road_within_150m")):
            flags.append("major_road_within_150m")
        if parse_int(risk.get("signals_within_50m")) == 0:
            flags.append("no_mapped_signal_within_50m")
        if parse_int(risk.get("traffic_calming_within_100m")) == 0:
            flags.append("no_mapped_traffic_calming_within_100m_weak_indicator")
        if parse_number(network.get("route_nearest_crossing_m")) > 250:
            flags.append("route_nearest_crossing_over_250m")
        if parse_number(network.get("route_vs_straight_ratio")) >= 1.5:
            flags.append("high_network_detour_ratio")
        return sorted(set(flags + read_json_list(risk.get("risk_flags")) + read_json_list(network.get("network_flags"))))

    def summary(self, rows: list[dict], base_workspace_id: str, workspace_id: str) -> dict:
        route_values = [parse_number(row.get("route_nearest_crossing_m")) for row in rows]
        flag_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        for row in rows:
            place_type = str(row.get("place_type") or "unknown")
            type_counts[place_type] = type_counts.get(place_type, 0) + 1
            for flag in read_json_list(row.get("public_space_access_flags")):
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        return {
            "workspace_id": workspace_id,
            "profile_id": "park_playground_access",
            "base_workspace_id": base_workspace_id,
            "analyzer": PARK_PLAYGROUND_ACCESS_ANALYZER_VERSION,
            "review_wording": self.review_wording,
            "counts": {
                "public_spaces": len(rows),
                "parks": type_counts.get("park", 0),
                "playgrounds": type_counts.get("playground", 0),
                "community_centres": type_counts.get("community_centre", 0),
                "recreation_grounds": type_counts.get("recreation_ground", 0),
                "public_spaces_without_mapped_crossing_within_150m": sum(1 for row in rows if str(row.get("crossing_within_150m")).lower() != "true"),
                "public_spaces_near_major_road_150m": sum(1 for row in rows if boolish(row.get("major_road_within_150m"))),
                "public_spaces_route_crossing_over_250m": sum(1 for row in rows if parse_number(row.get("route_nearest_crossing_m")) > 250),
            },
            "median_route_nearest_crossing_m": median(route_values),
            "top_flags": dict(sorted(flag_counts.items(), key=lambda item: (-item[1], item[0]))[:12]),
            "limitations": [
                "Derived from Safe Access route-aware workspace outputs.",
                "Route-aware distance is an OSM road-network proxy, not verified walking navigation.",
                "Mapped park/playground points and polygons may represent centroids, not all entrances.",
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
            ],
            "source_gis_modified": False,
        }

    def summary_markdown(self, summary: dict, rows: list[dict]) -> str:
        counts = summary.get("counts", {})
        lines = [
            "# Park And Playground Access Summary",
            "",
            f"Workspace: `{summary.get('workspace_id')}`",
            f"Base workspace: `{summary.get('base_workspace_id')}`",
            "",
            f"Approved review wording: `{self.review_wording}`",
            "",
            "This profile summarizes infrastructure review indicators around mapped public spaces. It is not a crash prediction.",
            "",
            "## Counts",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
        for key, value in counts.items():
            lines.append(f"| {key} | {value} |")
        lines.extend([
            f"| median_route_nearest_crossing_m | {summary.get('median_route_nearest_crossing_m')} |",
            "",
            "## Top Public Spaces",
            "",
            "| ID | Type | Name | Route crossing m | Score | Flags |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ])
        for row in rows:
            flags = ", ".join(read_json_list(row.get("public_space_access_flags"))[:3])
            lines.append(
                f"| {row.get('public_space_id')} | {row.get('place_type')} | {str(row.get('name') or '').replace('|', ' ')} | "
                f"{row.get('route_nearest_crossing_m')} | {row.get('public_space_review_priority_score')} | {flags} |"
            )
        lines.extend([
            "",
            "## Limitations",
            "",
            "- Route-aware distance is an OSM road-network proxy.",
            "- Park and playground geometry can be mapped as points, polygons, or centroids.",
            "- Missing OSM tags are data-quality flags.",
            "- On-site review is required before operational decisions.",
        ])
        return "\n".join(lines) + "\n"

    def list_workspaces(self) -> list[dict]:
        rows = []
        for manifest_path in sorted(self.workspaces_dir.glob("*/manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("profile_id") != "park_playground_access":
                continue
            summary = self.summary_for_workspace(manifest.get("workspace_id") or manifest_path.parent.name)
            rows.append({
                "workspace_id": manifest.get("workspace_id") or manifest_path.parent.name,
                "profile_id": manifest.get("profile_id"),
                "base_workspace_id": manifest.get("base_workspace_id"),
                "created_at_utc": manifest.get("created_at_utc"),
                "table_count": len(manifest.get("tables", [])),
                "public_spaces": summary.get("counts", {}).get("public_spaces"),
                "source_gis_modified": manifest.get("source_gis_modified") is True,
            })
        return rows

    def summary_for_workspace(self, workspace_id: str) -> dict:
        workspace_dir = self.workspaces_dir / workspace_id
        summary_path = workspace_dir / "reports" / "park_playground_access_summary.json"
        if not summary_path.exists():
            return {"error": "profile_workspace_not_found", "workspace_id": workspace_id}
        return json.loads(summary_path.read_text(encoding="utf-8"))

    def results(self, workspace_id: str, limit: int = 50) -> list[dict] | dict:
        workspace_dir = self.workspaces_dir / workspace_id
        results_path = workspace_dir / "tables" / "park_playground_access_results.csv"
        if not results_path.exists():
            return {"error": "profile_workspace_not_found", "workspace_id": workspace_id}
        rows = read_csv_rows(results_path)
        return rows[: max(1, min(limit, 500))]

    def output_file(self, workspace_id: str, output_id: str) -> dict:
        workspace_dir = self.workspaces_dir / workspace_id
        candidates = {
            "park_playground_access_results": workspace_dir / "tables" / "park_playground_access_results.csv",
            "park_playground_access_top20": workspace_dir / "tables" / "park_playground_access_top20.csv",
            "park_playground_access_summary": workspace_dir / "reports" / "park_playground_access_summary.json",
            "park_playground_access_markdown": workspace_dir / "reports" / "park_playground_access_summary.md",
        }
        path = candidates.get(output_id)
        if not path or not path.exists() or not self.safe_output_path(path):
            return {"error": "profile_output_not_found", "workspace_id": workspace_id, "output_id": output_id}
        return {"ok": True, "path": path, "file_name": path.name}

    def safe_output_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            root = self.workspaces_dir.resolve()
        except OSError:
            return False
        return str(resolved).startswith(str(root))
