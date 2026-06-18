from __future__ import annotations

import csv
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


MULTI_PILOT_COMPARISON_VERSION = "multi_pilot_comparison_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "multi_pilot_comparison") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:140] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def read_csv_rows(path: Path) -> list[dict]:
    try:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


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


def parse_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in text.split(";") if part.strip()]


def median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return round(ordered[midpoint], 1)
    return round((ordered[midpoint - 1] + ordered[midpoint]) / 2, 1)


def safe_call(fn: Callable[[], object], default: object) -> object:
    try:
        result = fn()
        return result if result is not None else default
    except Exception as exc:
        return {"error": "multi_pilot_probe_failed", "detail": repr(exc)}


class MultiPilotComparisonBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        dependencies: dict[str, object],
        expected_api_endpoints: int,
        default_pilots: list[dict] | None = None,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.dependencies = dependencies
        self.expected_api_endpoints = expected_api_endpoints
        self.comparisons_dir = output_root / "georeview_studio_multi_pilot_comparisons"
        self.workspaces_dir = output_root / "georeview_studio_workspaces"
        self.default_pilots = default_pilots or [
            {
                "pilot_label": "Kfar Saba",
                "pilot_osm_id": "53796999",
                "pbf_workspace_id": "safe_access_kfar_saba_pbf_enriched_v001",
                "route_workspace_id": "safe_access_kfar_saba_route_aware_v001",
            },
            {
                "pilot_label": "Raanana",
                "pilot_osm_id": "10550854",
                "pbf_workspace_id": "safe_access_pilot_10550854_pbf_enriched_v001",
                "route_workspace_id": "safe_access_pilot_10550854_route_aware_v001",
            },
        ]

    def status(self) -> dict:
        pilot_statuses = [self.pilot_status(spec) for spec in self.default_pilots]
        latest = self.list_comparisons(1)
        return {
            "ok": True,
            "multi_pilot_comparison_version": MULTI_PILOT_COMPARISON_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": self.safe_manifest().get("version"),
            "expected_api_endpoints": self.expected_api_endpoints,
            "default_pilot_count": len(self.default_pilots),
            "ready_pilot_count": sum(1 for row in pilot_statuses if row.get("route_workspace_exists")),
            "pilot_statuses": pilot_statuses,
            "comparison_count": len(self.list_comparisons(500)),
            "latest_comparison_id": latest[0].get("comparison_id") if latest else "",
            "latest_readiness": latest[0].get("comparison_readiness") if latest else "",
            "default_action": "create_multi_pilot_comparison",
            "output_dir": str(self.comparisons_dir),
            "approved_review_wording": self.review_wording,
            "claim_boundary": "Compares mapped infrastructure review indicators and data-quality evidence across pilot workspaces; it is not a crash prediction model.",
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_comparison(self, body: dict | None = None) -> dict:
        body = body or {}
        pilot_specs = self.normalize_pilot_specs(body.get("pilots"))
        metrics = [self.workspace_metrics(spec) for spec in pilot_specs]
        readiness = self.comparison_readiness(metrics)
        matrix = self.comparison_matrix(metrics)
        insights = self.insights(metrics)
        stamp = utc_now()
        comparison_id = f"multi_pilot_comparison_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        comparison_dir = self.comparisons_dir / comparison_id
        json_path = comparison_dir / f"{comparison_id}.json"
        markdown_path = comparison_dir / f"{comparison_id}.md"
        html_path = comparison_dir / "index.html"
        latest_path = self.comparisons_dir / "latest_multi_pilot_comparison.json"
        comparison = {
            "ok": True,
            "comparison_id": comparison_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Multi-pilot comparison for local portfolio review."),
            "multi_pilot_comparison_version": MULTI_PILOT_COMPARISON_VERSION,
            "app_version": self.app_version,
            "comparison_readiness": readiness,
            "pilot_count": len(metrics),
            "ready_pilot_count": sum(1 for item in metrics if item.get("workspace_exists")),
            "pilot_metrics": metrics,
            "comparison_matrix": matrix,
            "insights": insights,
            "approved_review_wording": self.review_wording,
            "claim_boundary": "The comparison ranks mapped infrastructure review indicators and data-quality evidence only. It does not label a location and does not predict crashes.",
            "source_gis_modified": False,
            "mutates_config": False,
        }
        comparison["files"] = {
            "json": str(json_path),
            "markdown": str(markdown_path),
            "html": str(html_path),
            "latest": str(latest_path),
            "directory": str(comparison_dir),
        }
        write_json(json_path, comparison)
        write_json(latest_path, comparison)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(self.markdown(comparison), encoding="utf-8", newline="\n")
        html_path.write_text(self.html_report(comparison), encoding="utf-8", newline="\n")
        return {"ok": True, "comparison": comparison, "source_gis_modified": False, "mutates_config": False}

    def list_comparisons(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.comparisons_dir.exists():
            return rows
        for path in sorted(self.comparisons_dir.glob("multi_pilot_comparison_*/multi_pilot_comparison_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "comparison_id": payload.get("comparison_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "comparison_readiness": payload.get("comparison_readiness"),
                "pilot_count": payload.get("pilot_count"),
                "ready_pilot_count": payload.get("ready_pilot_count"),
                "html_file": payload.get("files", {}).get("html"),
                "json_file": str(path),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, comparison_id: str) -> dict:
        token = safe_token(comparison_id, "missing")
        path = self.comparisons_dir / token / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "multi_pilot_comparison_not_found", "comparison_id": comparison_id, "source_gis_modified": False}
        return payload

    def output_file(self, comparison_id: str, output_id: str = "multi_pilot_comparison") -> dict:
        detail = self.detail(comparison_id)
        if detail.get("error"):
            return detail
        if output_id not in {"multi_pilot_comparison", "html"}:
            return {"ok": False, "error": "multi_pilot_comparison_output_not_found", "comparison_id": comparison_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists():
            return {"ok": False, "error": "multi_pilot_comparison_output_not_found", "comparison_id": comparison_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False}

    def pilot_status(self, spec: dict) -> dict:
        route_workspace_id = str(spec.get("route_workspace_id") or "")
        pbf_workspace_id = str(spec.get("pbf_workspace_id") or "")
        route_dir = self.workspaces_dir / route_workspace_id
        pbf_dir = self.workspaces_dir / pbf_workspace_id
        return {
            "pilot_label": spec.get("pilot_label"),
            "pilot_osm_id": spec.get("pilot_osm_id"),
            "pbf_workspace_id": pbf_workspace_id,
            "route_workspace_id": route_workspace_id,
            "pbf_workspace_exists": (pbf_dir / "manifest.json").exists(),
            "route_workspace_exists": (route_dir / "manifest.json").exists(),
            "source_gis_modified": False,
        }

    def normalize_pilot_specs(self, pilots: object) -> list[dict]:
        if not isinstance(pilots, list) or len(pilots) < 2:
            return self.default_pilots
        normalized = []
        for item in pilots[:6]:
            if not isinstance(item, dict):
                continue
            route_workspace_id = str(item.get("route_workspace_id") or "").strip()
            if not route_workspace_id:
                continue
            normalized.append({
                "pilot_label": str(item.get("pilot_label") or route_workspace_id),
                "pilot_osm_id": str(item.get("pilot_osm_id") or ""),
                "pbf_workspace_id": str(item.get("pbf_workspace_id") or ""),
                "route_workspace_id": route_workspace_id,
            })
        return normalized if len(normalized) >= 2 else self.default_pilots

    def workspace_metrics(self, spec: dict) -> dict:
        workspace_id = str(spec.get("route_workspace_id") or "")
        workspace_dir = self.workspaces_dir / workspace_id
        summary = read_json(workspace_dir / "reports" / "workspace_summary.json")
        manifest = read_json(workspace_dir / "manifest.json")
        tables_dir = workspace_dir / "tables"
        network_rows = read_csv_rows(tables_dir / "network_access_results.csv")
        risk_rows = read_csv_rows(tables_dir / "risk_assessment_results.csv")
        counts = summary.get("counts", {}) if isinstance(summary, dict) else {}
        route = summary.get("route_aware_analysis", {}) if isinstance(summary, dict) else {}
        workspace_exists = bool(summary and manifest)
        risk_scores = [parse_int(row.get("risk_score") or row.get("base_risk_score")) for row in risk_rows]
        route_scores = [parse_int(row.get("route_review_priority_score")) for row in network_rows]
        route_distances = [parse_number(row.get("route_nearest_crossing_m")) for row in network_rows if row.get("route_nearest_crossing_m") not in (None, "")]
        straight_distances = [parse_number(row.get("straight_nearest_crossing_m") or row.get("nearest_crossing_m")) for row in network_rows if row.get("straight_nearest_crossing_m") or row.get("nearest_crossing_m")]
        generator_counter = Counter(str(row.get("generator_type") or "unknown") for row in risk_rows)
        return {
            "ok": workspace_exists,
            "pilot_label": spec.get("pilot_label"),
            "pilot_osm_id": spec.get("pilot_osm_id"),
            "workspace_id": workspace_id,
            "workspace_exists": workspace_exists,
            "analysis_crs": summary.get("analysis_crs") if isinstance(summary, dict) else "",
            "validation_passed": summary.get("validation", {}).get("passed") is True if isinstance(summary, dict) else False,
            "counts": counts,
            "route_aware": {
                "rows": route.get("rows", len(network_rows)),
                "route_reachable_generators": route.get("route_reachable_generators"),
                "route_unreachable_generators": route.get("route_unreachable_generators"),
                "median_route_nearest_crossing_m": route.get("median_route_nearest_crossing_m") or median(route_distances),
                "p90_route_nearest_crossing_m": route.get("p90_route_nearest_crossing_m"),
                "generators_route_over_250m": route.get("generators_route_over_250m"),
                "generators_high_detour_ratio": route.get("generators_high_detour_ratio"),
                "generators_far_from_network_proxy": route.get("generators_far_from_network_proxy"),
                "median_route_vs_straight_ratio": route.get("median_route_vs_straight_ratio"),
                "network_nodes": route.get("network_nodes"),
                "network_edges": route.get("network_edges"),
            },
            "derived_metrics": {
                "risk_result_rows": len(risk_rows),
                "network_result_rows": len(network_rows),
                "max_base_risk_score": max(risk_scores) if risk_scores else 0,
                "max_route_review_priority_score": max(route_scores) if route_scores else 0,
                "median_route_nearest_crossing_m_from_rows": median(route_distances),
                "median_straight_nearest_crossing_m_from_rows": median(straight_distances),
                "crossings_per_100_generators": self.ratio_per_100(counts.get("crossings"), counts.get("pedestrian_generators")),
                "major_roads_per_100_generators": self.ratio_per_100(counts.get("major_roads"), counts.get("pedestrian_generators")),
                "traffic_calming_per_100_generators": self.ratio_per_100(counts.get("traffic_calming_features"), counts.get("pedestrian_generators")),
            },
            "top_generator_types": [{"generator_type": key, "rows": value} for key, value in generator_counter.most_common(8)],
            "flag_counts": {
                "risk_flags": self.flag_counts(risk_rows, "risk_flags"),
                "data_quality_flags": self.flag_counts(risk_rows + network_rows, "data_quality_flags"),
                "network_flags": self.flag_counts(network_rows, "network_flags"),
            },
            "top_review_rows": self.top_rows(network_rows or risk_rows, limit=5),
            "source_gis_modified": False,
        }

    def ratio_per_100(self, numerator: object, denominator: object) -> float:
        denom = parse_number(denominator)
        if denom <= 0:
            return 0.0
        return round((parse_number(numerator) / denom) * 100, 1)

    def flag_counts(self, rows: list[dict], field: str) -> list[dict]:
        counter: Counter[str] = Counter()
        for row in rows:
            for flag in parse_list(row.get(field)):
                counter[flag] += 1
        return [{"flag": key, "rows": value} for key, value in counter.most_common(8)]

    def top_rows(self, rows: list[dict], limit: int = 5) -> list[dict]:
        sorted_rows = sorted(
            rows,
            key=lambda row: (
                -parse_int(row.get("route_review_priority_score") or row.get("risk_score") or row.get("base_risk_score")),
                -parse_number(row.get("route_nearest_crossing_m") or row.get("nearest_crossing_m") or row.get("straight_nearest_crossing_m")),
            ),
        )
        selected = []
        for row in sorted_rows[:limit]:
            selected.append({
                "generator_id": row.get("generator_id"),
                "generator_type": row.get("generator_type"),
                "name": row.get("name") or "",
                "base_risk_score": parse_int(row.get("base_risk_score") or row.get("risk_score")),
                "route_review_priority_score": parse_int(row.get("route_review_priority_score")),
                "route_nearest_crossing_m": parse_number(row.get("route_nearest_crossing_m")),
                "straight_nearest_crossing_m": parse_number(row.get("straight_nearest_crossing_m") or row.get("nearest_crossing_m")),
                "network_flags": parse_list(row.get("network_flags")),
                "data_quality_flags": parse_list(row.get("data_quality_flags")),
                "review_wording": row.get("review_wording") or self.review_wording,
            })
        return selected

    def comparison_readiness(self, metrics: list[dict]) -> str:
        ready = [item for item in metrics if item.get("workspace_exists") and item.get("validation_passed") and parse_int(item.get("route_aware", {}).get("rows")) > 0]
        if len(ready) >= 2:
            return "ready_for_multi_pilot_review"
        return "ready_with_review_warnings"

    def comparison_matrix(self, metrics: list[dict]) -> list[dict]:
        metric_specs = [
            ("pedestrian_generators", "Pedestrian generators", ["counts", "pedestrian_generators"]),
            ("crossings", "Mapped crossings", ["counts", "crossings"]),
            ("traffic_signals", "Traffic signals", ["counts", "traffic_signals"]),
            ("major_roads", "Major road segments", ["counts", "major_roads"]),
            ("traffic_calming_features", "Traffic calming features", ["counts", "traffic_calming_features"]),
            ("median_route_nearest_crossing_m", "Median route distance to crossing (m)", ["route_aware", "median_route_nearest_crossing_m"]),
            ("generators_route_over_250m", "Generators with route distance over 250 m", ["route_aware", "generators_route_over_250m"]),
            ("high_detour_ratio", "High detour ratio rows", ["route_aware", "generators_high_detour_ratio"]),
            ("crossings_per_100_generators", "Crossings per 100 generators", ["derived_metrics", "crossings_per_100_generators"]),
            ("traffic_calming_per_100_generators", "Traffic calming per 100 generators", ["derived_metrics", "traffic_calming_per_100_generators"]),
        ]
        rows = []
        for metric_id, label, path in metric_specs:
            values = {item.get("pilot_label"): self.get_path(item, path) for item in metrics}
            rows.append({
                "metric_id": metric_id,
                "label": label,
                "values": values,
                "interpretation": self.metric_interpretation(metric_id),
            })
        return rows

    def get_path(self, payload: dict, path: list[str]) -> object:
        cursor: object = payload
        for key in path:
            if not isinstance(cursor, dict):
                return ""
            cursor = cursor.get(key)
        return cursor

    def metric_interpretation(self, metric_id: str) -> str:
        notes = {
            "pedestrian_generators": "Scale of review workload in the pilot workspace.",
            "crossings": "Mapped crossing evidence available for nearest-crossing analysis.",
            "traffic_signals": "Mapped signal evidence that can support crossing-context flags.",
            "major_roads": "Road exposure proxy from mapped OSM road classes.",
            "traffic_calming_features": "Mapped calming evidence; absence in OSM is a data-quality issue, not proof of absence.",
            "median_route_nearest_crossing_m": "Route-aware proxy distance across mapped road graph, measured in EPSG:2039.",
            "generators_route_over_250m": "Review-priority workload indicator for locations far from mapped crossings by route proxy.",
            "high_detour_ratio": "Locations where road-graph route is much longer than straight-line distance.",
            "crossings_per_100_generators": "Normalized mapped crossing coverage proxy.",
            "traffic_calming_per_100_generators": "Normalized mapped calming evidence proxy.",
        }
        return notes.get(metric_id, "Mapped infrastructure review indicator.")

    def insights(self, metrics: list[dict]) -> list[dict]:
        ready = [item for item in metrics if item.get("workspace_exists")]
        if len(ready) < 2:
            return [{
                "title": "Comparison requires two route-aware workspaces",
                "evidence": "At least one default pilot workspace is missing.",
                "recommendation": "Build missing selected-pilot workspaces before using the comparison in a portfolio demo.",
            }]
        first, second = ready[0], ready[1]
        first_generators = parse_int(first.get("counts", {}).get("pedestrian_generators"))
        second_generators = parse_int(second.get("counts", {}).get("pedestrian_generators"))
        first_median = parse_number(first.get("route_aware", {}).get("median_route_nearest_crossing_m"))
        second_median = parse_number(second.get("route_aware", {}).get("median_route_nearest_crossing_m"))
        first_over = parse_int(first.get("route_aware", {}).get("generators_route_over_250m"))
        second_over = parse_int(second.get("route_aware", {}).get("generators_route_over_250m"))
        insights = [
            {
                "title": "Second pilot proves the pipeline is reusable",
                "evidence": f"{second.get('pilot_label')} has {second_generators} pedestrian generators and {second.get('counts', {}).get('crossings')} mapped crossings in the route-aware workspace.",
                "recommendation": "Use this as portfolio evidence that the analyzer is not hard-coded only for Kfar Saba.",
            },
            {
                "title": "Review workload differs by pilot",
                "evidence": f"{first.get('pilot_label')} has {first_generators} generators; {second.get('pilot_label')} has {second_generators}.",
                "recommendation": "Show workload-normalized metrics such as crossings per 100 generators before comparing pilots.",
            },
            {
                "title": "Route-aware crossing distance is now comparable",
                "evidence": f"Median route distance is {first_median} m for {first.get('pilot_label')} and {second_median} m for {second.get('pilot_label')}.",
                "recommendation": "Treat this as a mapped network proxy for field-review prioritization, not verified walking distance.",
            },
            {
                "title": "Longer route-distance candidates can drive field review",
                "evidence": f"Rows over 250 m by route proxy: {first.get('pilot_label')}={first_over}, {second.get('pilot_label')}={second_over}.",
                "recommendation": "Use top candidates as inspection samples and keep missing tags as separate data-quality flags.",
            },
            {
                "title": "Lighting remains a data-quality limitation",
                "evidence": f"Street-lamp counts are {first.get('counts', {}).get('street_lamps')} and {second.get('counts', {}).get('street_lamps')} in the inspected workspaces.",
                "recommendation": "Do not infer real lighting conditions from missing OSM lighting evidence.",
            },
        ]
        return insights

    def markdown(self, comparison: dict) -> str:
        lines = [
            "# GeoReview Studio Multi-Pilot Comparison",
            "",
            f"Comparison: `{comparison.get('comparison_id')}`",
            f"Readiness: `{comparison.get('comparison_readiness')}`",
            "",
            "Approved review wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Pilot Metrics",
            "",
        ]
        for metric in comparison.get("pilot_metrics", []):
            counts = metric.get("counts", {})
            route = metric.get("route_aware", {})
            lines.extend([
                f"### {metric.get('pilot_label')}",
                "",
                f"- Workspace: `{metric.get('workspace_id')}`",
                f"- Generators: `{counts.get('pedestrian_generators')}`",
                f"- Crossings: `{counts.get('crossings')}`",
                f"- Major roads: `{counts.get('major_roads')}`",
                f"- Median route crossing distance: `{route.get('median_route_nearest_crossing_m')}` m",
                f"- Rows over 250 m: `{route.get('generators_route_over_250m')}`",
                "",
            ])
        lines.extend(["## Comparison Matrix", ""])
        for row in comparison.get("comparison_matrix", []):
            lines.append(f"- `{row.get('metric_id')}`: {row.get('values')} - {row.get('interpretation')}")
        lines.extend(["", "## Insights", ""])
        for insight in comparison.get("insights", []):
            lines.append(f"- **{insight.get('title')}**: {insight.get('evidence')} Recommendation: {insight.get('recommendation')}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            "This comparison supports infrastructure review prioritization and data-quality review only. It does not label a location and does not predict crashes.",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)

    def html_report(self, comparison: dict) -> str:
        def esc(value: object) -> str:
            return html.escape(str(value if value is not None else ""))

        metric_cards = []
        for metric in comparison.get("pilot_metrics", []):
            counts = metric.get("counts", {})
            route = metric.get("route_aware", {})
            metric_cards.append(
                f"<article class=\"card\"><h2>{esc(metric.get('pilot_label'))}</h2>"
                f"<p><b>Workspace:</b> {esc(metric.get('workspace_id'))}</p>"
                f"<div class=\"mini\"><span>Generators</span><strong>{esc(counts.get('pedestrian_generators'))}</strong></div>"
                f"<div class=\"mini\"><span>Crossings</span><strong>{esc(counts.get('crossings'))}</strong></div>"
                f"<div class=\"mini\"><span>Median route m</span><strong>{esc(route.get('median_route_nearest_crossing_m'))}</strong></div>"
                f"<div class=\"mini\"><span>Route >250 m</span><strong>{esc(route.get('generators_route_over_250m'))}</strong></div>"
                "</article>"
            )
        matrix_rows = []
        for row in comparison.get("comparison_matrix", []):
            value_cells = "".join(f"<td>{esc(label)}: {esc(value)}</td>" for label, value in row.get("values", {}).items())
            matrix_rows.append(f"<tr><th>{esc(row.get('label'))}</th>{value_cells}<td>{esc(row.get('interpretation'))}</td></tr>")
        insight_cards = []
        for insight in comparison.get("insights", []):
            insight_cards.append(
                f"<article class=\"insight\"><h3>{esc(insight.get('title'))}</h3>"
                f"<p>{esc(insight.get('evidence'))}</p>"
                f"<small>{esc(insight.get('recommendation'))}</small></article>"
            )
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GeoReview Studio Multi-Pilot Comparison</title>
    <style>
      :root {{ color-scheme: light; --ink:#18222b; --muted:#586978; --line:#d5dde6; --panel:#ffffff; --soft:#eef5f1; --accent:#176b5b; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:#f7f9fb; line-height:1.5; }}
      header {{ background:#15382f; color:#fff; padding:44px 28px 36px; }}
      .inner {{ width:min(1160px, calc(100% - 40px)); margin:0 auto; }}
      h1 {{ margin:0 0 12px; font-size:40px; line-height:1.1; letter-spacing:0; }}
      h2 {{ margin:0 0 10px; font-size:22px; letter-spacing:0; }}
      h3 {{ margin:0 0 8px; font-size:17px; letter-spacing:0; }}
      p {{ margin:0 0 12px; }}
      .subtitle {{ max-width:880px; color:#dceae5; font-size:18px; }}
      .status-row {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:20px; }}
      .pill {{ border:1px solid rgba(255,255,255,.36); border-radius:6px; padding:7px 10px; font-size:13px; }}
      .band {{ padding:28px 0; border-top:1px solid var(--line); }}
      .band:nth-of-type(even) {{ background:var(--soft); }}
      .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:14px; }}
      .card,.insight {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; }}
      .card p,.insight small {{ color:var(--muted); overflow-wrap:anywhere; }}
      .mini {{ display:flex; align-items:center; justify-content:space-between; gap:12px; border-top:1px solid var(--line); padding-top:10px; margin-top:10px; }}
      .mini span {{ color:var(--muted); font-size:13px; }}
      .mini strong {{ font-size:24px; color:var(--accent); }}
      table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
      th,td {{ border-bottom:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; }}
      th {{ width:26%; background:#f8faf9; }}
      .claim {{ background:#fff7e6; border-top:1px solid #ecd399; border-bottom:1px solid #ecd399; padding:24px 0; }}
      footer {{ padding:28px; color:var(--muted); font-size:13px; }}
      @media (max-width:720px) {{ h1 {{ font-size:30px; }} .inner {{ width:min(100% - 28px, 1160px); }} th,td {{ display:block; width:100%; }} }}
    </style>
  </head>
  <body>
    <header>
      <div class="inner">
        <h1>GeoReview Studio Multi-Pilot Comparison</h1>
        <p class="subtitle">Kfar Saba and Raanana are compared with the same Safe Access route-aware workspace contract.</p>
        <div class="status-row">
          <span class="pill">App {esc(comparison.get('app_version'))}</span>
          <span class="pill">{esc(comparison.get('comparison_readiness'))}</span>
          <span class="pill">Source GIS read-only</span>
          <span class="pill">EPSG:2039 distance evidence</span>
        </div>
      </div>
    </header>
    <main>
      <section class="band"><div class="inner"><div class="grid">{''.join(metric_cards)}</div></div></section>
      <section class="band"><div class="inner"><h2>Comparison Matrix</h2><table><tbody>{''.join(matrix_rows)}</tbody></table></div></section>
      <section class="band"><div class="inner"><h2>Review Insights</h2><div class="grid">{''.join(insight_cards)}</div></div></section>
      <section class="claim"><div class="inner"><h2>Claim Boundary</h2><p><b>Approved wording:</b> {esc(self.review_wording)}</p><p>This comparison supports infrastructure review prioritization and data-quality review only. It does not label a location and does not predict crashes.</p></div></section>
    </main>
    <footer><div class="inner">Comparison: {esc(comparison.get('comparison_id'))}<br />Source GIS modified: false. Config mutated: false.</div></footer>
  </body>
</html>
"""

    def safe_manifest(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        return manifest if isinstance(manifest, dict) else {}
