from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PORTFOLIO_REPORT_BUILDER_VERSION = "portfolio_report_builder_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "item") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:96] or fallback


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def read_csv_sample(path: Path, limit: int = 8) -> list[dict]:
    rows: list[dict] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
                if len(rows) >= limit:
                    break
    except OSError:
        return []
    return rows


def compact_outputs(outputs: list[dict]) -> list[dict]:
    return [
        {
            "output_id": item.get("output_id"),
            "kind": item.get("kind"),
            "label": item.get("label"),
            "file_name": item.get("file_name"),
            "rows": item.get("rows"),
            "size_bytes": item.get("size_bytes"),
            "download_url": item.get("download_url"),
        }
        for item in outputs
    ]


def pick_output(outputs: list[dict], *needles: str) -> dict:
    lowered = [needle.lower() for needle in needles]
    for item in outputs:
        haystack = " ".join(
            str(item.get(key, "")) for key in ("output_id", "label", "file_name", "path")
        ).lower()
        if all(needle in haystack for needle in lowered):
            return item
    return {}


def markdown_escape(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def summarize_counts(summary: dict) -> dict:
    counts = summary.get("counts", {}) if isinstance(summary, dict) else {}
    return {
        "pedestrian_generators": counts.get("pedestrian_generators"),
        "crossings": counts.get("crossings"),
        "road_segments": counts.get("road_segments"),
        "major_roads": counts.get("major_roads"),
        "traffic_signals": counts.get("traffic_signals"),
        "traffic_calming_features": counts.get("traffic_calming_features"),
        "childcare": counts.get("childcare"),
    }


def summarize_route(summary: dict) -> dict:
    route = summary.get("route_aware_analysis", {}) if isinstance(summary, dict) else {}
    return {
        "rows": route.get("rows"),
        "network_nodes": route.get("network_nodes"),
        "route_reachable_generators": route.get("route_reachable_generators"),
        "median_route_nearest_crossing_m": route.get("median_route_nearest_crossing_m"),
        "generators_route_over_250m": route.get("generators_route_over_250m"),
    }


def primary_profile_count(profile_id: str, counts: dict) -> int | None:
    if profile_id == "transit_stop_walk_access":
        return counts.get("transit_stops")
    if profile_id == "park_playground_access":
        return counts.get("public_spaces")
    return counts.get("result_rows") or counts.get("rows") or counts.get("features")


class PortfolioReportBuilder:
    def __init__(self, reports_dir: Path, analysis_runs, workspaces_dir: Path | None = None) -> None:
        self.reports_dir = reports_dir
        self.analysis_runs = analysis_runs
        self.workspaces_dir = workspaces_dir

    def generate_from_run(self, run_id: str) -> dict:
        detail = self.analysis_runs.detail(run_id)
        if "error" in detail:
            return detail
        run = detail.get("run", {})
        outputs = detail.get("outputs", [])
        summary = detail.get("workspace_summary", {})
        report_id = self.next_report_id("report", run_id)

        risk_output = pick_output(outputs, "risk", "top20") or pick_output(outputs, "risk_assessment_results")
        network_output = pick_output(outputs, "network", "top20") or pick_output(outputs, "network_access_results")
        top_candidates = self.output_sample(risk_output)
        network_candidates = self.output_sample(network_output, limit=5)

        report = {
            "ok": True,
            "portfolio_report_builder_version": PORTFOLIO_REPORT_BUILDER_VERSION,
            "report_id": report_id,
            "report_type": "single_run",
            "generated_at_utc": utc_now(),
            "run": run,
            "payload": detail.get("payload", {}),
            "workspace_id": run.get("active_workspace_id"),
            "counts": summarize_counts(summary),
            "route_aware_metrics": summarize_route(summary),
            "validation": summary.get("validation", {}) if isinstance(summary, dict) else {},
            "outputs": compact_outputs(outputs),
            "top_candidates": self.candidate_sample(top_candidates),
            "network_candidate_sample": self.network_sample(network_candidates),
            "claim_boundaries": [
                "Infrastructure review indicators only.",
                "Not a crash prediction.",
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
                REVIEW_WORDING,
            ],
            "source_gis_modified": detail.get("source_gis_modified") is True,
        }
        self.write_report(report, self.single_run_markdown(report))
        return self.response_payload(report)

    def compare_runs(self, run_ids: list[str]) -> dict:
        clean_ids = [safe_token(run_id) for run_id in run_ids if str(run_id or "").strip()]
        if len(clean_ids) < 2:
            return {"error": "portfolio_compare_needs_runs", "detail": "at least two run ids are required"}
        rows = []
        errors = []
        for run_id in clean_ids[:8]:
            detail = self.analysis_runs.detail(run_id)
            if "error" in detail:
                errors.append({"run_id": run_id, "error": detail.get("error")})
                continue
            run = detail.get("run", {})
            summary = detail.get("workspace_summary", {})
            route = summarize_route(summary)
            counts = summarize_counts(summary)
            rows.append({
                "run_id": run.get("run_id"),
                "status": run.get("status"),
                "run_type": run.get("run_type"),
                "workspace_id": run.get("active_workspace_id"),
                "output_count": run.get("output_count"),
                "pedestrian_generators": counts.get("pedestrian_generators"),
                "crossings": counts.get("crossings"),
                "road_segments": counts.get("road_segments"),
                "route_rows": route.get("rows"),
                "route_reachable_generators": route.get("route_reachable_generators"),
                "median_route_nearest_crossing_m": route.get("median_route_nearest_crossing_m"),
                "source_gis_modified": detail.get("source_gis_modified") is True,
            })
        if len(rows) < 2:
            return {"error": "portfolio_compare_needs_runs", "detail": "fewer than two valid runs", "errors": errors}
        report_id = self.next_report_id("compare", "-".join(row["run_id"] or "" for row in rows))
        report = {
            "ok": True,
            "portfolio_report_builder_version": PORTFOLIO_REPORT_BUILDER_VERSION,
            "report_id": report_id,
            "report_type": "run_compare",
            "generated_at_utc": utc_now(),
            "runs": rows,
            "errors": errors,
            "claim_boundaries": [
                "Run comparison checks reproducibility and output consistency.",
                "It does not rank real-world safety.",
                REVIEW_WORDING,
            ],
            "source_gis_modified": any(row.get("source_gis_modified") for row in rows),
        }
        self.write_report(report, self.compare_markdown(report))
        return self.response_payload(report)

    def generate_from_profile_workspace(self, workspace_id: str) -> dict:
        if self.workspaces_dir is None:
            return {"error": "profile_report_not_configured"}
        clean_workspace_id = safe_token(workspace_id, "workspace")
        workspace_dir = self.workspaces_dir / clean_workspace_id
        manifest = read_json(workspace_dir / "manifest.json")
        if not manifest or not manifest.get("profile_workspace"):
            return {"error": "profile_workspace_not_found", "workspace_id": workspace_id}
        profile_id = manifest.get("profile_id") or "profile"
        summary = self.profile_summary(workspace_dir, manifest)
        outputs = self.profile_outputs(manifest)
        top_rows = self.profile_sample(workspace_dir, manifest)
        report_id = self.next_report_id("profile", f"{profile_id}_{clean_workspace_id}")
        report = {
            "ok": True,
            "portfolio_report_builder_version": PORTFOLIO_REPORT_BUILDER_VERSION,
            "report_id": report_id,
            "report_type": "profile_workspace",
            "generated_at_utc": utc_now(),
            "profile_id": profile_id,
            "workspace_id": clean_workspace_id,
            "base_workspace_id": manifest.get("base_workspace_id"),
            "analyzer": manifest.get("analyzer"),
            "counts": summary.get("counts", {}),
            "median_route_nearest_crossing_m": summary.get("median_route_nearest_crossing_m"),
            "top_flags": summary.get("top_flags", {}),
            "outputs": outputs,
            "top_transit_stops": top_rows if profile_id == "transit_stop_walk_access" else [],
            "top_public_spaces": top_rows if profile_id == "park_playground_access" else [],
            "top_authored_results": top_rows if manifest.get("authored_profile_workspace") else [],
            "profile_candidate_sample": top_rows,
            "claim_boundaries": [
                "Profile workspace reports summarize infrastructure review indicators.",
                "They do not predict crashes.",
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
                REVIEW_WORDING,
            ],
            "source_gis_modified": manifest.get("source_gis_modified") is True or summary.get("source_gis_modified") is True,
        }
        self.write_report(report, self.profile_workspace_markdown(report))
        return self.response_payload(report)

    def generate_profile_comparison(self, base_workspace_id: str, profile_workspace_ids: list[str]) -> dict:
        if self.workspaces_dir is None:
            return {"error": "profile_report_not_configured"}
        clean_base_workspace_id = safe_token(base_workspace_id, "workspace")
        base_workspace_dir = self.workspaces_dir / clean_base_workspace_id
        base_manifest = read_json(base_workspace_dir / "manifest.json")
        base_summary = read_json(base_workspace_dir / "reports" / "workspace_summary.json")
        if not base_manifest or not base_summary:
            return {"error": "workspace_not_found", "workspace_id": base_workspace_id}

        clean_profile_ids = [safe_token(workspace_id, "workspace") for workspace_id in profile_workspace_ids if str(workspace_id or "").strip()]
        profiles = []
        errors = []
        for workspace_id in clean_profile_ids[:8]:
            workspace_dir = self.workspaces_dir / workspace_id
            manifest = read_json(workspace_dir / "manifest.json")
            if not manifest or not manifest.get("profile_workspace"):
                errors.append({"workspace_id": workspace_id, "error": "profile_workspace_not_found"})
                continue
            summary = self.profile_summary(workspace_dir, manifest)
            counts = summary.get("counts", {})
            profiles.append({
                "profile_id": manifest.get("profile_id"),
                "workspace_id": workspace_id,
                "base_workspace_id": manifest.get("base_workspace_id"),
                "analyzer": manifest.get("analyzer"),
                "primary_count": primary_profile_count(str(manifest.get("profile_id") or ""), counts),
                "counts": counts,
                "median_route_nearest_crossing_m": summary.get("median_route_nearest_crossing_m"),
                "top_flags": summary.get("top_flags", {}),
                "outputs": self.profile_outputs(manifest),
                "source_gis_modified": manifest.get("source_gis_modified") is True or summary.get("source_gis_modified") is True,
            })
        if len(profiles) < 2:
            return {"error": "profile_compare_needs_workspaces", "detail": "at least two valid profile workspaces are required", "errors": errors}

        base_counts = base_summary.get("counts", {})
        route = summarize_route(base_summary)
        comparison_rows = [
            {
                "profile_id": "safe_access_pedestrian_review",
                "workspace_id": clean_base_workspace_id,
                "primary_count": base_counts.get("pedestrian_generators"),
                "median_route_nearest_crossing_m": route.get("median_route_nearest_crossing_m"),
                "top_evidence": f"{base_counts.get('crossings')} crossings; {base_counts.get('road_segments')} road segments",
            }
        ]
        for profile in profiles:
            top_flag = next(iter(profile.get("top_flags", {}).items()), ("", ""))
            comparison_rows.append({
                "profile_id": profile.get("profile_id"),
                "workspace_id": profile.get("workspace_id"),
                "primary_count": profile.get("primary_count"),
                "median_route_nearest_crossing_m": profile.get("median_route_nearest_crossing_m"),
                "top_evidence": f"{top_flag[0]}: {top_flag[1]}" if top_flag[0] else "",
            })

        report_id = self.next_report_id("profile_compare", f"{clean_base_workspace_id}_{'_'.join(clean_profile_ids)}")
        report = {
            "ok": True,
            "portfolio_report_builder_version": PORTFOLIO_REPORT_BUILDER_VERSION,
            "report_id": report_id,
            "report_type": "profile_comparison",
            "generated_at_utc": utc_now(),
            "base_workspace_id": clean_base_workspace_id,
            "base_profile": {
                "profile_id": "safe_access_pedestrian_review",
                "workspace_id": clean_base_workspace_id,
                "counts": summarize_counts(base_summary),
                "generator_counts": {
                    "schools": base_counts.get("schools"),
                    "kindergartens": base_counts.get("kindergartens"),
                    "childcare": base_counts.get("childcare"),
                    "bus_stops": base_counts.get("bus_stops"),
                    "parks": base_counts.get("parks"),
                    "playgrounds": base_counts.get("playgrounds"),
                    "community_centres": base_counts.get("community_centres"),
                },
                "route_aware_metrics": route,
            },
            "profiles": profiles,
            "comparison_rows": comparison_rows,
            "errors": errors,
            "claim_boundaries": [
                "Profile comparison shows reusable analytics coverage across one validated source and pilot area.",
                "It compares infrastructure review indicators, not real-world safety.",
                "Profile counts depend on mapped OSM/Geofabrik evidence and generated workspace outputs.",
                "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
                REVIEW_WORDING,
            ],
            "source_gis_modified": base_manifest.get("source_gis_modified") is True or any(profile.get("source_gis_modified") for profile in profiles),
        }
        self.write_report(report, self.profile_comparison_markdown(report))
        return self.response_payload(report)

    def list_reports(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 200))
        reports = []
        if not self.reports_dir.exists():
            return reports
        for path in sorted(self.reports_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("portfolio_report_builder_version") != PORTFOLIO_REPORT_BUILDER_VERSION:
                continue
            reports.append(self.compact_report(data))
            if len(reports) >= limit:
                break
        return reports

    def detail(self, report_id: str) -> dict:
        json_path = self.report_path(report_id, ".json")
        if not json_path.exists():
            return {"error": "portfolio_report_not_found", "report_id": report_id}
        data = read_json(json_path)
        if not data:
            return {"error": "portfolio_report_not_found", "report_id": report_id}
        markdown_path = self.report_path(report_id, ".md")
        data["download_url"] = f"/api/portfolio-reports/{data.get('report_id')}/download"
        data["markdown_file"] = str(markdown_path) if markdown_path.exists() else ""
        return data

    def report_file(self, report_id: str, suffix: str = ".md") -> dict:
        if suffix not in {".md", ".json"}:
            return {"error": "portfolio_report_output_not_found", "report_id": report_id}
        path = self.report_path(report_id, suffix)
        if not path.exists() or not self.safe_report_path(path):
            return {"error": "portfolio_report_output_not_found", "report_id": report_id}
        return {"ok": True, "path": path, "file_name": path.name}

    def output_sample(self, output: dict, limit: int = 8) -> list[dict]:
        path = Path(output.get("path", "")) if output else Path()
        if not path.exists():
            return []
        return read_csv_sample(path, limit=limit)

    def profile_summary(self, workspace_dir: Path, manifest: dict) -> dict:
        reports = manifest.get("reports", {})
        for key in ("transit_access_summary", "park_playground_access_summary", "profile_summary", "summary"):
            file_name = reports.get(key)
            if not file_name:
                continue
            path = Path(file_name)
            if path.exists():
                return read_json(path)
        for path in sorted((workspace_dir / "reports").glob("*.json")):
            data = read_json(path)
            if isinstance(data.get("counts"), dict):
                return data
        return {}

    def profile_outputs(self, manifest: dict) -> list[dict]:
        outputs = []
        workspace_id = manifest.get("workspace_id")
        for table in manifest.get("tables", []):
            path = Path(table.get("file", ""))
            if path.exists():
                output_id_value = safe_token(table.get("table") or path.stem)
                outputs.append({
                    "output_id": output_id_value,
                    "kind": "table",
                    "label": table.get("table") or path.stem,
                    "file_name": path.name,
                    "rows": table.get("rows"),
                    "size_bytes": path.stat().st_size,
                    "download_url": f"/api/profile-workspaces/{workspace_id}/download/{output_id_value}" if workspace_id else "",
                })
        for label, file_name in manifest.get("reports", {}).items():
            path = Path(file_name)
            if path.exists():
                output_id_value = safe_token(label)
                outputs.append({
                    "output_id": output_id_value,
                    "kind": "report",
                    "label": label,
                    "file_name": path.name,
                    "rows": None,
                    "size_bytes": path.stat().st_size,
                    "download_url": f"/api/profile-workspaces/{workspace_id}/download/{output_id_value}" if workspace_id else "",
                })
        return outputs

    def profile_sample(self, workspace_dir: Path, manifest: dict) -> list[dict]:
        candidates = []
        for table in manifest.get("tables", []):
            label = str(table.get("table") or "")
            path = Path(table.get("file", ""))
            if "top20" in label and path.exists():
                candidates = read_csv_sample(path, limit=8)
                break
        if not candidates:
            for table in manifest.get("tables", []):
                path = Path(table.get("file", ""))
                if path.exists():
                    candidates = read_csv_sample(path, limit=8)
                    break
        if manifest.get("authored_profile_workspace"):
            fields = [
                "result_id",
                "requirement_type",
                "tag_or_field",
                "evidence_status",
                "total_count",
                "primary_score",
                "flags",
                "data_quality_flags",
                "review_wording",
            ]
        elif manifest.get("profile_id") == "park_playground_access":
            fields = [
                "public_space_id",
                "osm_id",
                "place_type",
                "name",
                "nearest_crossing_m",
                "route_nearest_crossing_m",
                "public_space_review_priority_score",
                "public_space_access_flags",
                "data_quality_flags",
                "review_wording",
            ]
        else:
            fields = [
                "transit_stop_id",
                "osm_id",
                "name",
                "nearest_crossing_m",
                "route_nearest_crossing_m",
                "transit_review_priority_score",
                "transit_access_flags",
                "data_quality_flags",
                "review_wording",
            ]
        return [{field: row.get(field, "") for field in fields} for row in candidates]

    @staticmethod
    def candidate_sample(rows: list[dict]) -> list[dict]:
        fields = [
            "generator_id",
            "generator_type",
            "name",
            "nearest_crossing_m",
            "nearest_major_road_m",
            "risk_score",
            "risk_flags",
            "data_quality_flags",
            "review_wording",
        ]
        return [{field: row.get(field, "") for field in fields} for row in rows]

    @staticmethod
    def network_sample(rows: list[dict]) -> list[dict]:
        fields = [
            "generator_id",
            "generator_type",
            "name",
            "base_risk_score",
            "route_review_priority_score",
            "route_nearest_crossing_m",
            "route_vs_straight_ratio",
            "network_flags",
        ]
        return [{field: row.get(field, "") for field in fields} for row in rows]

    def write_report(self, report: dict, markdown: str) -> None:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_id = report["report_id"]
        json_path = self.report_path(report_id, ".json")
        md_path = self.report_path(report_id, ".md")
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(markdown, encoding="utf-8")

    def response_payload(self, report: dict) -> dict:
        payload = self.compact_report(report)
        payload.update({
            "ok": True,
            "json_file": str(self.report_path(report["report_id"], ".json")),
            "markdown_file": str(self.report_path(report["report_id"], ".md")),
        })
        return payload

    @staticmethod
    def compact_report(report: dict) -> dict:
        report_id = report.get("report_id")
        return {
            "ok": True,
            "report_id": report_id,
            "report_type": report.get("report_type"),
            "generated_at_utc": report.get("generated_at_utc"),
            "run_id": report.get("run", {}).get("run_id"),
            "profile_id": report.get("profile_id"),
            "workspace_id": report.get("workspace_id"),
            "run_count": len(report.get("runs", [])),
            "profile_count": len(report.get("profiles", [])),
            "source_gis_modified": report.get("source_gis_modified") is True,
            "download_url": f"/api/portfolio-reports/{report_id}/download" if report_id else "",
        }

    def single_run_markdown(self, report: dict) -> str:
        run = report.get("run", {})
        counts = report.get("counts", {})
        route = report.get("route_aware_metrics", {})
        outputs = report.get("outputs", [])
        candidates = report.get("top_candidates", [])
        network = report.get("network_candidate_sample", [])
        lines = [
            "# GeoReview Studio Portfolio Report",
            "",
            "## Scope",
            "",
            "This report summarizes one reproducible GIS analysis run for infrastructure review prioritization.",
            "",
            f"Approved review wording: `{REVIEW_WORDING}`",
            "",
            "This is not a crash prediction. Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
            "",
            "## Run Evidence",
            "",
            f"- Report id: `{report.get('report_id')}`",
            f"- Run id: `{run.get('run_id')}`",
            f"- Status: `{run.get('status')}`",
            f"- Run type: `{run.get('run_type')}`",
            f"- Workspace: `{run.get('active_workspace_id')}`",
            f"- Dataset id: `{run.get('dataset_id')}`",
            f"- Pilot: `{run.get('pilot_name') or run.get('pilot_osm_id')}`",
            f"- Source GIS modified: `{report.get('source_gis_modified')}`",
            "",
            "## Key Counts",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
        for key, value in counts.items():
            lines.append(f"| {markdown_escape(key)} | {markdown_escape(value)} |")
        lines.extend([
            "",
            "## Route-Aware Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ])
        for key, value in route.items():
            lines.append(f"| {markdown_escape(key)} | {markdown_escape(value)} |")
        lines.extend([
            "",
            "## Top Candidate Sample",
            "",
            "| ID | Type | Name | Crossing m | Major road m | Score |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ])
        for row in candidates:
            lines.append(
                "| {generator_id} | {generator_type} | {name} | {nearest_crossing_m} | {nearest_major_road_m} | {risk_score} |".format(
                    generator_id=markdown_escape(row.get("generator_id")),
                    generator_type=markdown_escape(row.get("generator_type")),
                    name=markdown_escape(row.get("name")),
                    nearest_crossing_m=markdown_escape(row.get("nearest_crossing_m")),
                    nearest_major_road_m=markdown_escape(row.get("nearest_major_road_m")),
                    risk_score=markdown_escape(row.get("risk_score")),
                )
            )
        lines.extend([
            "",
            "## Route Candidate Sample",
            "",
            "| ID | Type | Route priority | Route crossing m | Ratio |",
            "| --- | --- | ---: | ---: | ---: |",
        ])
        for row in network:
            lines.append(
                "| {generator_id} | {generator_type} | {route_review_priority_score} | {route_nearest_crossing_m} | {route_vs_straight_ratio} |".format(
                    generator_id=markdown_escape(row.get("generator_id")),
                    generator_type=markdown_escape(row.get("generator_type")),
                    route_review_priority_score=markdown_escape(row.get("route_review_priority_score")),
                    route_nearest_crossing_m=markdown_escape(row.get("route_nearest_crossing_m")),
                    route_vs_straight_ratio=markdown_escape(row.get("route_vs_straight_ratio")),
                )
            )
        lines.extend([
            "",
            "## Output Files",
            "",
            "| Kind | Label | Rows | File |",
            "| --- | --- | ---: | --- |",
        ])
        for item in outputs:
            lines.append(
                f"| {markdown_escape(item.get('kind'))} | {markdown_escape(item.get('label'))} | {markdown_escape(item.get('rows'))} | `{markdown_escape(item.get('file_name'))}` |"
            )
        lines.extend([
            "",
            "## Interpretation Limits",
            "",
            "- The score is a transparent review-priority indicator.",
            "- OSM coverage varies by tag and place.",
            "- On-site review is required before operational decisions.",
        ])
        return "\n".join(lines) + "\n"

    def compare_markdown(self, report: dict) -> str:
        lines = [
            "# GeoReview Studio Run Compare",
            "",
            "This report compares reproducible run outputs and consistency signals.",
            "",
            f"Approved review wording: `{REVIEW_WORDING}`",
            "",
            "| Run | Status | Workspace | Outputs | Generators | Crossings | Route rows | Median route m |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in report.get("runs", []):
            lines.append(
                "| {run_id} | {status} | {workspace_id} | {output_count} | {pedestrian_generators} | {crossings} | {route_rows} | {median_route_nearest_crossing_m} |".format(
                    run_id=markdown_escape(row.get("run_id")),
                    status=markdown_escape(row.get("status")),
                    workspace_id=markdown_escape(row.get("workspace_id")),
                    output_count=markdown_escape(row.get("output_count")),
                    pedestrian_generators=markdown_escape(row.get("pedestrian_generators")),
                    crossings=markdown_escape(row.get("crossings")),
                    route_rows=markdown_escape(row.get("route_rows")),
                    median_route_nearest_crossing_m=markdown_escape(row.get("median_route_nearest_crossing_m")),
                )
            )
        lines.extend([
            "",
            "This comparison does not rank real-world safety. It checks whether repeated analysis runs expose stable outputs.",
        ])
        return "\n".join(lines) + "\n"

    def profile_workspace_markdown(self, report: dict) -> str:
        lines = [
            "# GeoReview Studio Profile Workspace Report",
            "",
            "## Scope",
            "",
            f"Profile: `{report.get('profile_id')}`",
            f"Workspace: `{report.get('workspace_id')}`",
            f"Base workspace: `{report.get('base_workspace_id')}`",
            "",
            f"Approved review wording: `{REVIEW_WORDING}`",
            "",
            "This report summarizes profile-specific infrastructure review indicators. It does not predict crashes.",
            "",
            "## Counts",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
        for key, value in report.get("counts", {}).items():
            lines.append(f"| {markdown_escape(key)} | {markdown_escape(value)} |")
        lines.append(f"| median_route_nearest_crossing_m | {markdown_escape(report.get('median_route_nearest_crossing_m'))} |")
        lines.extend([
            "",
            "## Top Flags",
            "",
            "| Flag | Count |",
            "| --- | ---: |",
        ])
        for key, value in report.get("top_flags", {}).items():
            lines.append(f"| {markdown_escape(key)} | {markdown_escape(value)} |")
        lines.extend([
            "",
        ])
        if report.get("top_authored_results"):
            lines.extend([
                "## Authored Profile Evidence Sample",
                "",
                "| Result | Requirement | Tag | Evidence status | Count | Score |",
                "| --- | --- | --- | --- | ---: | ---: |",
            ])
            for row in report.get("profile_candidate_sample", []):
                lines.append(
                    "| {result_id} | {requirement_type} | {tag_or_field} | {evidence_status} | {total_count} | {primary_score} |".format(
                        result_id=markdown_escape(row.get("result_id")),
                        requirement_type=markdown_escape(row.get("requirement_type")),
                        tag_or_field=markdown_escape(row.get("tag_or_field")),
                        evidence_status=markdown_escape(row.get("evidence_status")),
                        total_count=markdown_escape(row.get("total_count")),
                        primary_score=markdown_escape(row.get("primary_score")),
                    )
                )
        elif report.get("profile_id") == "park_playground_access":
            lines.extend([
                "## Top Public Space Sample",
                "",
                "| ID | Type | Name | Straight crossing m | Route crossing m | Score |",
                "| --- | --- | --- | ---: | ---: | ---: |",
            ])
            for row in report.get("profile_candidate_sample", []):
                lines.append(
                    "| {public_space_id} | {place_type} | {name} | {nearest_crossing_m} | {route_nearest_crossing_m} | {public_space_review_priority_score} |".format(
                        public_space_id=markdown_escape(row.get("public_space_id")),
                        place_type=markdown_escape(row.get("place_type")),
                        name=markdown_escape(row.get("name")),
                        nearest_crossing_m=markdown_escape(row.get("nearest_crossing_m")),
                        route_nearest_crossing_m=markdown_escape(row.get("route_nearest_crossing_m")),
                        public_space_review_priority_score=markdown_escape(row.get("public_space_review_priority_score")),
                    )
                )
        else:
            lines.extend([
                "## Top Transit Stop Sample",
                "",
                "| Stop | Name | Straight crossing m | Route crossing m | Score |",
                "| --- | --- | ---: | ---: | ---: |",
            ])
            for row in report.get("profile_candidate_sample", []):
                lines.append(
                    "| {transit_stop_id} | {name} | {nearest_crossing_m} | {route_nearest_crossing_m} | {transit_review_priority_score} |".format(
                        transit_stop_id=markdown_escape(row.get("transit_stop_id")),
                        name=markdown_escape(row.get("name")),
                        nearest_crossing_m=markdown_escape(row.get("nearest_crossing_m")),
                        route_nearest_crossing_m=markdown_escape(row.get("route_nearest_crossing_m")),
                        transit_review_priority_score=markdown_escape(row.get("transit_review_priority_score")),
                    )
                )
        lines.extend([
            "",
            "## Output Files",
            "",
            "| Kind | Label | Rows | File |",
            "| --- | --- | ---: | --- |",
        ])
        for item in report.get("outputs", []):
            lines.append(
                f"| {markdown_escape(item.get('kind'))} | {markdown_escape(item.get('label'))} | {markdown_escape(item.get('rows'))} | `{markdown_escape(item.get('file_name'))}` |"
            )
        lines.extend([
            "",
            "## Interpretation Limits",
            "",
            "- Profile outputs are derived from generated workspace evidence.",
            "- Route-aware distance is an OSM road-network proxy.",
            "- Missing OSM tags remain data-quality gaps.",
            "- On-site review is required before operational decisions.",
        ])
        return "\n".join(lines) + "\n"

    def profile_comparison_markdown(self, report: dict) -> str:
        base = report.get("base_profile", {})
        lines = [
            "# GeoReview Studio Profile Comparison",
            "",
            "## Scope",
            "",
            f"Base workspace: `{report.get('base_workspace_id')}`",
            "",
            f"Approved review wording: `{REVIEW_WORDING}`",
            "",
            "This report compares implemented analytics profiles on the same Kfar Saba OSM/Geofabrik evidence. It is not a crash prediction.",
            "",
            "## Implemented Profile Coverage",
            "",
            "| Profile | Workspace | Primary count | Median route crossing m | Top evidence |",
            "| --- | --- | ---: | ---: | --- |",
        ]
        for row in report.get("comparison_rows", []):
            lines.append(
                "| {profile_id} | {workspace_id} | {primary_count} | {median_route_nearest_crossing_m} | {top_evidence} |".format(
                    profile_id=markdown_escape(row.get("profile_id")),
                    workspace_id=markdown_escape(row.get("workspace_id")),
                    primary_count=markdown_escape(row.get("primary_count")),
                    median_route_nearest_crossing_m=markdown_escape(row.get("median_route_nearest_crossing_m")),
                    top_evidence=markdown_escape(row.get("top_evidence")),
                )
            )
        lines.extend([
            "",
            "## Safe Access Generator Counts",
            "",
            "| Generator type | Count |",
            "| --- | ---: |",
        ])
        for key, value in base.get("generator_counts", {}).items():
            lines.append(f"| {markdown_escape(key)} | {markdown_escape(value)} |")
        lines.extend([
            "",
            "## Profile Details",
            "",
            "| Profile | Count fields | Output files |",
            "| --- | --- | --- |",
        ])
        for profile in report.get("profiles", []):
            count_text = ", ".join(f"{key}={value}" for key, value in profile.get("counts", {}).items())
            output_text = ", ".join(str(item.get("file_name") or "") for item in profile.get("outputs", [])[:4])
            lines.append(
                f"| {markdown_escape(profile.get('profile_id'))} | {markdown_escape(count_text)} | {markdown_escape(output_text)} |"
            )
        lines.extend([
            "",
            "## Interpretation Limits",
            "",
            "- The comparison demonstrates reusable analytics coverage, not a ranking of places.",
            "- Profile outputs inherit OSM coverage and tagging limitations.",
            "- Route-aware distance remains an OSM road-network proxy.",
            "- On-site review is required before operational decisions.",
        ])
        return "\n".join(lines) + "\n"

    def next_report_id(self, prefix: str, seed: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{prefix}_{stamp}_{safe_token(seed, 'run')[-48:]}"

    def report_path(self, report_id: str, suffix: str) -> Path:
        return self.reports_dir / f"{safe_token(report_id, 'report')}{suffix}"

    def safe_report_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            root = self.reports_dir.resolve()
        except OSError:
            return False
        return str(resolved).startswith(str(root))
