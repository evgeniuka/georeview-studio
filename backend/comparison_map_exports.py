from __future__ import annotations

import csv
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


COMPARISON_MAP_EXPORTS_VERSION = "comparison_map_exports_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


DEFAULT_PILOTS = [
    {
        "pilot_label": "Kfar Saba",
        "pilot_osm_id": "53796999",
        "route_workspace_id": "safe_access_kfar_saba_route_aware_v001",
    },
    {
        "pilot_label": "Raanana",
        "pilot_osm_id": "10550854",
        "route_workspace_id": "safe_access_pilot_10550854_route_aware_v001",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "comparison_map_export") -> str:
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


def write_csv_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_float(value: object, default: float = 0.0) -> float:
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


def parse_json_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(str(value or "[]"))
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return []


POINT_RE = re.compile(r"POINT\s*\(\s*([-0-9.]+)\s+([-0-9.]+)\s*\)", re.IGNORECASE)
LINE_RE = re.compile(r"LINESTRING\s*\(([^)]+)\)", re.IGNORECASE)


def parse_point_wkt(value: object) -> tuple[float, float] | None:
    match = POINT_RE.search(str(value or ""))
    if not match:
        return None
    return parse_float(match.group(1)), parse_float(match.group(2))


def parse_linestring_wkt(value: object) -> list[tuple[float, float]]:
    match = LINE_RE.search(str(value or ""))
    if not match:
        return []
    points: list[tuple[float, float]] = []
    for part in match.group(1).split(","):
        coords = part.strip().split()
        if len(coords) >= 2:
            points.append((parse_float(coords[0]), parse_float(coords[1])))
    return points


def safe_call(fn: Callable[[], object], default: object) -> object:
    try:
        result = fn()
        return result if result is not None else default
    except Exception as exc:
        return {"error": "comparison_map_export_probe_failed", "detail": repr(exc)}


class ComparisonMapExportBuilder:
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
        self.default_pilots = default_pilots or DEFAULT_PILOTS
        self.workspaces_dir = output_root / "georeview_studio_workspaces"
        self.exports_dir = output_root / "georeview_studio_comparison_map_exports"

    def status(self) -> dict:
        pilot_statuses = [self.pilot_status(spec) for spec in self.default_pilots]
        latest = self.list_exports(1)
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "comparison_map_exports_version": COMPARISON_MAP_EXPORTS_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "default_pilot_count": len(self.default_pilots),
            "ready_pilot_count": sum(1 for row in pilot_statuses if row.get("route_workspace_exists") and row.get("required_tables_present")),
            "pilot_statuses": pilot_statuses,
            "export_count": len(self.list_exports(500)),
            "latest_export_id": latest[0].get("export_id") if latest else "",
            "latest_readiness": latest[0].get("export_readiness") if latest else "",
            "default_action": "create_comparison_map_export",
            "output_dir": str(self.exports_dir),
            "approved_review_wording": self.review_wording,
            "claim_boundary": "Map exports show mapped infrastructure review indicators and data-quality context; they are not crash prediction artifacts.",
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_export(self, body: dict | None = None) -> dict:
        body = body or {}
        top_limit = max(5, min(parse_int(body.get("top_limit"), 20), 60))
        pilot_specs = self.normalize_pilot_specs(body.get("pilots"))
        stamp = utc_now()
        export_id = f"comparison_map_export_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        export_dir = self.exports_dir / export_id
        pilot_maps = [self.build_pilot_map(spec, export_dir, top_limit) for spec in pilot_specs]
        rows = []
        for pilot_map in pilot_maps:
            rows.extend(pilot_map.get("top_candidate_rows", []))
        csv_path = export_dir / "top_review_candidates.csv"
        csv_fields = [
            "pilot_label",
            "workspace_id",
            "generator_id",
            "generator_type",
            "name",
            "route_review_priority_score",
            "base_risk_score",
            "route_nearest_crossing_m",
            "straight_nearest_crossing_m",
            "network_flags",
            "data_quality_flags",
            "review_wording",
            "lon",
            "lat",
        ]
        write_csv_rows(csv_path, rows, csv_fields)
        readiness = self.export_readiness(pilot_maps, csv_path)
        export = {
            "ok": True,
            "export_id": export_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Comparison map export for local portfolio review."),
            "comparison_map_exports_version": COMPARISON_MAP_EXPORTS_VERSION,
            "app_version": self.app_version,
            "export_readiness": readiness,
            "pilot_count": len(pilot_maps),
            "ready_pilot_count": sum(1 for item in pilot_maps if item.get("map_ready")),
            "top_limit": top_limit,
            "pilot_maps": pilot_maps,
            "top_candidate_rows": len(rows),
            "approved_review_wording": self.review_wording,
            "claim_boundary": "Map exports support infrastructure review prioritization and data-quality review only. They do not label a location and do not predict crashes.",
            "source_gis_modified": False,
            "mutates_config": False,
        }
        json_path = export_dir / f"{export_id}.json"
        html_path = export_dir / "index.html"
        latest_path = self.exports_dir / "latest_comparison_map_export.json"
        export["files"] = {
            "json": str(json_path),
            "html": str(html_path),
            "top_candidates_csv": str(csv_path),
            "latest": str(latest_path),
            "directory": str(export_dir),
        }
        write_json(json_path, export)
        write_json(latest_path, export)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(self.html_report(export), encoding="utf-8", newline="\n")
        return {"ok": True, "export": export, "source_gis_modified": False, "mutates_config": False}

    def list_exports(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.exports_dir.exists():
            return rows
        for path in sorted(self.exports_dir.glob("comparison_map_export_*/comparison_map_export_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "export_id": payload.get("export_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "export_readiness": payload.get("export_readiness"),
                "pilot_count": payload.get("pilot_count"),
                "ready_pilot_count": payload.get("ready_pilot_count"),
                "html_file": payload.get("files", {}).get("html"),
                "csv_file": payload.get("files", {}).get("top_candidates_csv"),
                "json_file": str(path),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, export_id: str) -> dict:
        token = safe_token(export_id, "missing")
        path = self.exports_dir / token / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "comparison_map_export_not_found", "export_id": export_id, "source_gis_modified": False}
        return payload

    def output_file(self, export_id: str, output_id: str = "comparison_map_export") -> dict:
        detail = self.detail(export_id)
        if detail.get("error"):
            return detail
        if output_id not in {"comparison_map_export", "html"}:
            return {"ok": False, "error": "comparison_map_export_output_not_found", "export_id": export_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists():
            return {"ok": False, "error": "comparison_map_export_output_not_found", "export_id": export_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False}

    def pilot_status(self, spec: dict) -> dict:
        workspace_id = str(spec.get("route_workspace_id") or "")
        workspace_dir = self.workspaces_dir / workspace_id
        required = [
            workspace_dir / "manifest.json",
            workspace_dir / "tables" / "network_access_results.csv",
            workspace_dir / "tables" / "crossings.csv",
            workspace_dir / "tables" / "road_segments.csv",
        ]
        missing = [path.name for path in required if not path.exists()]
        return {
            "pilot_label": spec.get("pilot_label"),
            "pilot_osm_id": spec.get("pilot_osm_id"),
            "route_workspace_id": workspace_id,
            "route_workspace_exists": (workspace_dir / "manifest.json").exists(),
            "required_tables_present": not missing,
            "missing": missing,
            "source_gis_modified": False,
        }

    def normalize_pilot_specs(self, pilots: object) -> list[dict]:
        if not isinstance(pilots, list) or len(pilots) < 2:
            return self.default_pilots
        normalized = []
        for item in pilots[:6]:
            if not isinstance(item, dict):
                continue
            workspace_id = str(item.get("route_workspace_id") or "").strip()
            if not workspace_id:
                continue
            normalized.append({
                "pilot_label": str(item.get("pilot_label") or workspace_id),
                "pilot_osm_id": str(item.get("pilot_osm_id") or ""),
                "route_workspace_id": workspace_id,
            })
        return normalized if len(normalized) >= 2 else self.default_pilots

    def build_pilot_map(self, spec: dict, export_dir: Path, top_limit: int) -> dict:
        pilot_label = str(spec.get("pilot_label") or "")
        workspace_id = str(spec.get("route_workspace_id") or "")
        workspace_dir = self.workspaces_dir / workspace_id
        tables_dir = workspace_dir / "tables"
        summary = read_json(workspace_dir / "reports" / "workspace_summary.json")
        network_rows = read_csv_rows(tables_dir / "network_access_results.csv")
        crossing_rows = read_csv_rows(tables_dir / "crossings.csv")
        road_rows = read_csv_rows(tables_dir / "road_segments.csv")
        top_rows = self.top_candidates(network_rows, top_limit)
        all_candidates = self.top_candidates(network_rows, min(180, max(top_limit * 4, 80)))
        svg = self.svg_map(pilot_label, summary, top_rows, all_candidates, crossing_rows, road_rows)
        svg_file_name = f"{safe_token(pilot_label, 'pilot')}_map.svg"
        svg_path = export_dir / svg_file_name
        svg_path.parent.mkdir(parents=True, exist_ok=True)
        svg_path.write_text(svg, encoding="utf-8", newline="\n")
        rows = []
        for row in top_rows:
            rows.append({
                "pilot_label": pilot_label,
                "workspace_id": workspace_id,
                "generator_id": row.get("generator_id"),
                "generator_type": row.get("generator_type"),
                "name": row.get("name") or "",
                "route_review_priority_score": row.get("route_review_priority_score"),
                "base_risk_score": row.get("base_risk_score"),
                "route_nearest_crossing_m": row.get("route_nearest_crossing_m"),
                "straight_nearest_crossing_m": row.get("straight_nearest_crossing_m"),
                "network_flags": row.get("network_flags"),
                "data_quality_flags": row.get("data_quality_flags"),
                "review_wording": row.get("review_wording") or self.review_wording,
                "lon": row.get("lon"),
                "lat": row.get("lat"),
            })
        return {
            "pilot_label": pilot_label,
            "pilot_osm_id": spec.get("pilot_osm_id"),
            "workspace_id": workspace_id,
            "map_ready": svg_path.exists() and svg_path.stat().st_size > 1000 and len(top_rows) > 0,
            "svg_file": str(svg_path),
            "svg_file_name": svg_file_name,
            "candidate_rows": len(network_rows),
            "crossing_rows": len(crossing_rows),
            "road_rows": len(road_rows),
            "top_candidate_count": len(top_rows),
            "counts": summary.get("counts", {}) if isinstance(summary, dict) else {},
            "route_aware": summary.get("route_aware_analysis", {}) if isinstance(summary, dict) else {},
            "top_candidate_rows": rows,
            "source_gis_modified": False,
        }

    def top_candidates(self, rows: list[dict], limit: int) -> list[dict]:
        return sorted(
            rows,
            key=lambda row: (
                -parse_int(row.get("route_review_priority_score") or row.get("risk_score") or row.get("base_risk_score")),
                -parse_float(row.get("route_nearest_crossing_m") or row.get("straight_nearest_crossing_m")),
            ),
        )[:limit]

    def svg_map(
        self,
        pilot_label: str,
        summary: dict,
        top_rows: list[dict],
        all_candidates: list[dict],
        crossing_rows: list[dict],
        road_rows: list[dict],
    ) -> str:
        width = 820
        height = 560
        pad = 42
        road_geoms = []
        for row in road_rows:
            points = parse_linestring_wkt(row.get("geometry_wkt"))
            if len(points) >= 2:
                road_geoms.append((row, points))
        point_rows = []
        for row in crossing_rows[:900] + all_candidates:
            point = parse_point_wkt(row.get("geometry_wkt"))
            if point:
                point_rows.append(point)
        all_points = [pt for _row, points in road_geoms for pt in points] + point_rows
        if not all_points:
            all_points = [(0.0, 0.0), (1.0, 1.0)]
        min_x = min(x for x, _y in all_points)
        max_x = max(x for x, _y in all_points)
        min_y = min(y for _x, y in all_points)
        max_y = max(y for _x, y in all_points)
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)

        def project(point: tuple[float, float]) -> tuple[float, float]:
            x, y = point
            sx = pad + ((x - min_x) / span_x) * (width - pad * 2)
            sy = height - pad - ((y - min_y) / span_y) * (height - pad * 2)
            return sx, sy

        road_svg = []
        for row, points in road_geoms:
            cls = str(row.get("highway_class") or "")
            coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in (project(pt) for pt in points))
            if cls in {"primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link", "trunk", "trunk_link"}:
                color = "#955c2d"
                stroke = "2.2"
                opacity = "0.55"
            elif cls in {"footway", "path", "pedestrian", "cycleway", "living_street"}:
                color = "#2f8f83"
                stroke = "1.3"
                opacity = "0.42"
            else:
                color = "#aab6c3"
                stroke = "0.8"
                opacity = "0.32"
            road_svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{stroke}" opacity="{opacity}" />')

        crossing_svg = []
        for row in crossing_rows:
            point = parse_point_wkt(row.get("geometry_wkt"))
            if not point:
                continue
            x, y = project(point)
            crossing_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="#16805d" opacity="0.58" />')

        candidate_svg = []
        for row in all_candidates:
            point = parse_point_wkt(row.get("geometry_wkt"))
            if not point:
                continue
            x, y = project(point)
            candidate_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="#326fa8" opacity="0.42" />')

        top_svg = []
        for index, row in enumerate(top_rows[:12], start=1):
            point = parse_point_wkt(row.get("geometry_wkt"))
            if not point:
                continue
            x, y = project(point)
            score = parse_int(row.get("route_review_priority_score"))
            radius = max(6, min(12, 5 + score / 18))
            top_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="#c94733" stroke="#fff" stroke-width="1.8" opacity="0.92" />')
            top_svg.append(f'<text x="{x + radius + 3:.1f}" y="{y + 4:.1f}" font-family="Arial" font-size="10" fill="#17202a">{index}</text>')

        counts = summary.get("counts", {}) if isinstance(summary, dict) else {}
        route = summary.get("route_aware_analysis", {}) if isinstance(summary, dict) else {}
        title = html.escape(pilot_label)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{title} comparison map export">
  <rect width="100%" height="100%" fill="#fbfcfa" />
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#d7dee8" />
  <g>{''.join(road_svg)}</g>
  <g>{''.join(crossing_svg)}</g>
  <g>{''.join(candidate_svg)}</g>
  <g>{''.join(top_svg)}</g>
  <rect x="18" y="16" width="420" height="116" rx="8" fill="#ffffff" opacity="0.94" stroke="#d7dee8" />
  <text x="34" y="42" font-family="Arial" font-size="22" font-weight="700" fill="#17202a">{title}</text>
  <text x="34" y="66" font-family="Arial" font-size="12" fill="#52616f">Generators {html.escape(str(counts.get('pedestrian_generators', '')))} | Crossings {html.escape(str(counts.get('crossings', '')))} | Major roads {html.escape(str(counts.get('major_roads', '')))}</text>
  <text x="34" y="88" font-family="Arial" font-size="12" fill="#52616f">Median route to crossing {html.escape(str(route.get('median_route_nearest_crossing_m', '')))} m | Route over 250 m {html.escape(str(route.get('generators_route_over_250m', '')))}</text>
  <circle cx="36" cy="112" r="5" fill="#c94733" /><text x="48" y="116" font-family="Arial" font-size="11" fill="#52616f">Top review candidates</text>
  <circle cx="180" cy="112" r="4" fill="#326fa8" opacity="0.55" /><text x="192" y="116" font-family="Arial" font-size="11" fill="#52616f">Candidate sample</text>
  <circle cx="310" cy="112" r="4" fill="#16805d" opacity="0.7" /><text x="322" y="116" font-family="Arial" font-size="11" fill="#52616f">Mapped crossings</text>
</svg>
"""

    def export_readiness(self, pilot_maps: list[dict], csv_path: Path) -> str:
        if len(pilot_maps) >= 2 and all(item.get("map_ready") for item in pilot_maps) and csv_path.exists() and csv_path.stat().st_size > 300:
            return "ready_for_portfolio_map_review"
        return "ready_with_review_warnings"

    def html_report(self, export: dict) -> str:
        def esc(value: object) -> str:
            return html.escape(str(value if value is not None else ""))

        cards = []
        for pilot in export.get("pilot_maps", []):
            counts = pilot.get("counts", {})
            route = pilot.get("route_aware", {})
            cards.append(
                f"<article class=\"map-card\"><h2>{esc(pilot.get('pilot_label'))}</h2>"
                f"<img src=\"{esc(pilot.get('svg_file_name'))}\" alt=\"{esc(pilot.get('pilot_label'))} map export\" />"
                f"<div class=\"metrics\"><span>Generators <b>{esc(counts.get('pedestrian_generators'))}</b></span>"
                f"<span>Crossings <b>{esc(counts.get('crossings'))}</b></span>"
                f"<span>Route median m <b>{esc(route.get('median_route_nearest_crossing_m'))}</b></span>"
                f"<span>Route over 250 m <b>{esc(route.get('generators_route_over_250m'))}</b></span></div>"
                "</article>"
            )
        rows = []
        for pilot in export.get("pilot_maps", []):
            for row in pilot.get("top_candidate_rows", [])[:8]:
                rows.append(
                    f"<tr><td>{esc(row.get('pilot_label'))}</td><td>{esc(row.get('generator_id'))}</td>"
                    f"<td>{esc(row.get('generator_type'))}</td><td>{esc(row.get('name'))}</td>"
                    f"<td>{esc(row.get('route_review_priority_score'))}</td><td>{esc(row.get('route_nearest_crossing_m'))}</td></tr>"
                )
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GeoReview Studio Comparison Map Export</title>
    <style>
      :root {{ color-scheme:light; --ink:#18222b; --muted:#586978; --line:#d5dde6; --panel:#fff; --soft:#eef5f1; --accent:#176b5b; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; font-family:Arial, Helvetica, sans-serif; background:#f7f9fb; color:var(--ink); line-height:1.5; }}
      header {{ background:#15382f; color:#fff; padding:42px 28px 34px; }}
      .inner {{ width:min(1260px, calc(100% - 40px)); margin:0 auto; }}
      h1 {{ margin:0 0 12px; font-size:40px; line-height:1.1; letter-spacing:0; }}
      h2 {{ margin:0 0 12px; font-size:22px; letter-spacing:0; }}
      p {{ margin:0 0 12px; }}
      .subtitle {{ color:#dceae5; max-width:900px; font-size:18px; }}
      .status-row {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:20px; }}
      .pill {{ border:1px solid rgba(255,255,255,.34); border-radius:6px; padding:7px 10px; font-size:13px; }}
      .band {{ padding:28px 0; border-top:1px solid var(--line); }}
      .band:nth-of-type(even) {{ background:var(--soft); }}
      .map-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(420px, 1fr)); gap:18px; align-items:start; }}
      .map-card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; }}
      img {{ width:100%; height:auto; border:1px solid var(--line); background:#fbfcfa; display:block; }}
      .metrics {{ display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:8px; margin-top:12px; }}
      .metrics span {{ background:#f8faf9; border:1px solid var(--line); border-radius:6px; padding:8px; color:var(--muted); font-size:13px; }}
      .metrics b {{ color:var(--accent); font-size:18px; display:block; }}
      table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); }}
      th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; }}
      th {{ background:#f8faf9; }}
      .claim {{ background:#fff7e6; border-top:1px solid #ecd399; border-bottom:1px solid #ecd399; padding:24px 0; }}
      footer {{ padding:28px; color:var(--muted); font-size:13px; }}
      @media (max-width:720px) {{ h1 {{ font-size:30px; }} .inner {{ width:min(100% - 28px, 1260px); }} .map-grid {{ grid-template-columns:1fr; }} }}
    </style>
  </head>
  <body>
    <header>
      <div class="inner">
        <h1>GeoReview Studio Comparison Map Export</h1>
        <p class="subtitle">Side-by-side visual evidence for Kfar Saba and Raanana route-aware Safe Access review candidates.</p>
        <div class="status-row">
          <span class="pill">App {esc(export.get('app_version'))}</span>
          <span class="pill">{esc(export.get('export_readiness'))}</span>
          <span class="pill">Top limit {esc(export.get('top_limit'))}</span>
          <span class="pill">Source GIS read-only</span>
        </div>
      </div>
    </header>
    <main>
      <section class="band"><div class="inner map-grid">{''.join(cards)}</div></section>
      <section class="band"><div class="inner"><h2>Top Review Candidate Sample</h2><table><thead><tr><th>Pilot</th><th>ID</th><th>Type</th><th>Name</th><th>Route score</th><th>Route m</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
      <section class="claim"><div class="inner"><h2>Claim Boundary</h2><p><b>Approved wording:</b> {esc(self.review_wording)}</p><p>This export supports infrastructure review prioritization and data-quality review only. It does not label a location and does not predict crashes.</p></div></section>
    </main>
    <footer><div class="inner">Export: {esc(export.get('export_id'))}<br />Source GIS modified: false. Config mutated: false.</div></footer>
  </body>
</html>
"""
