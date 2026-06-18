from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PORTFOLIO_DEMO_VERSION = "portfolio_demo_walkthrough_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "portfolio_demo") -> str:
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


def safe_call(fn: Callable[[], object], default: object) -> object:
    try:
        result = fn()
        return result if result is not None else default
    except Exception as exc:
        return {"error": "portfolio_demo_probe_failed", "detail": repr(exc)}


class PortfolioDemoWalkthrough:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        dependencies: dict[str, object],
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.dependencies = dependencies
        self.snapshots_dir = output_root / "georeview_studio_portfolio_demo"

    def overview(self) -> dict:
        context = self.context()
        steps = self.demo_steps(context)
        return {
            "ok": True,
            "portfolio_demo_version": PORTFOLIO_DEMO_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": context.get("manifest", {}).get("version"),
            "title": "GeoReview Studio guided portfolio walkthrough",
            "audience": ["software engineering reviewer", "GIS/data engineering reviewer", "road-safety domain reviewer"],
            "estimated_duration_min": 8,
            "positioning": "A local-first GIS analytics workbench for infrastructure review indicators and data-quality evidence.",
            "step_count": len(steps),
            "steps": steps,
            "demo_metrics": self.demo_metrics(context),
            "recommended_demo_order": [step.get("step_id") for step in steps],
            "approved_review_wording": self.review_wording,
            "claim_boundary": "The demo presents mapped infrastructure indicators and data-quality evidence for field-review prioritization, not crash prediction.",
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def steps_response(self) -> dict:
        overview = self.overview()
        return {
            "ok": True,
            "portfolio_demo_version": PORTFOLIO_DEMO_VERSION,
            "app_version": self.app_version,
            "step_count": overview.get("step_count", 0),
            "steps": overview.get("steps", []),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_snapshot(self, body: dict | None = None) -> dict:
        body = body or {}
        overview = self.overview()
        stamp = utc_now()
        snapshot_id = f"portfolio_demo_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        snapshot = {
            "ok": True,
            "snapshot_id": snapshot_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Guided portfolio walkthrough snapshot."),
            "portfolio_demo_version": PORTFOLIO_DEMO_VERSION,
            "app_version": self.app_version,
            "step_count": overview.get("step_count", 0),
            "demo_metrics": overview.get("demo_metrics", {}),
            "overview": overview,
            "source_gis_modified": False,
            "mutates_config": False,
        }
        json_path = self.snapshots_dir / f"{snapshot_id}.json"
        md_path = self.snapshots_dir / f"{snapshot_id}.md"
        latest_path = self.snapshots_dir / "latest_portfolio_demo_snapshot.json"
        snapshot["files"] = {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)}
        write_json(json_path, snapshot)
        write_json(latest_path, snapshot)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(self.snapshot_markdown(snapshot), encoding="utf-8", newline="\n")
        return {"ok": True, "snapshot": snapshot, "source_gis_modified": False, "mutates_config": False}

    def list_snapshots(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.snapshots_dir.exists():
            return rows
        for path in sorted(self.snapshots_dir.glob("portfolio_demo_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "snapshot_id": payload.get("snapshot_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "step_count": payload.get("step_count"),
                "json_file": str(path),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def snapshot_detail(self, snapshot_id: str) -> dict:
        token = safe_token(snapshot_id, "missing")
        path = self.snapshots_dir / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "portfolio_demo_snapshot_not_found", "snapshot_id": snapshot_id, "source_gis_modified": False}
        return payload

    def context(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        product_architecture = self.dependencies.get("product_architecture")
        release_readiness = self.dependencies.get("release_readiness")
        onboarding = self.dependencies.get("onboarding")
        profile_dashboard = self.dependencies.get("profile_dashboard")
        scoring_rules = self.dependencies.get("scoring_rules")
        portfolio_reports = self.dependencies.get("portfolio_reports")
        profile_export_bundles = self.dependencies.get("profile_export_bundles")
        profile_promotion = self.dependencies.get("profile_promotion")

        architecture = safe_call(product_architecture.blueprint, {}) if product_architecture else {}
        roadmap = safe_call(product_architecture.roadmap, {}) if product_architecture else {}
        readiness = safe_call(release_readiness.overview, {}) if release_readiness else {}
        onboarding_status = safe_call(onboarding.status, {}) if onboarding else {}
        dashboard = safe_call(profile_dashboard.overview, {}) if profile_dashboard else {}
        scoring = safe_call(scoring_rules.overview, {}) if scoring_rules else {}
        reports = safe_call(lambda: portfolio_reports.list_reports(10), []) if portfolio_reports else []
        bundles = safe_call(lambda: profile_export_bundles.list_bundles(10), []) if profile_export_bundles else []
        promotion = safe_call(profile_promotion.status, {}) if profile_promotion else {}
        validation_summary = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        portfolio_manifest = read_json(self.project_dir / "portfolio" / "portfolio_manifest.json")

        profile_rows = 0
        profile_summaries = []
        for row in dashboard.get("profiles", []):
            try:
                profile_rows += int(row.get("result_count") or 0)
            except (TypeError, ValueError):
                pass
            profile_summaries.append({
                "profile_id": row.get("profile_id"),
                "name": row.get("name"),
                "result_count": row.get("result_count"),
                "status": row.get("status"),
            })

        return {
            "manifest": manifest if isinstance(manifest, dict) else {},
            "architecture": architecture if isinstance(architecture, dict) else {},
            "roadmap": roadmap if isinstance(roadmap, dict) else {},
            "release_readiness": readiness if isinstance(readiness, dict) else {},
            "onboarding": onboarding_status if isinstance(onboarding_status, dict) else {},
            "profile_dashboard": dashboard if isinstance(dashboard, dict) else {},
            "profile_summaries": profile_summaries,
            "profile_result_rows": profile_rows,
            "scoring": scoring if isinstance(scoring, dict) else {},
            "reports": reports if isinstance(reports, list) else [],
            "bundles": bundles if isinstance(bundles, list) else [],
            "promotion": promotion if isinstance(promotion, dict) else {},
            "validation_summary": validation_summary,
            "api_contract": api_contract,
            "portfolio_manifest": portfolio_manifest,
        }

    def demo_metrics(self, context: dict) -> dict:
        validation = context.get("validation_summary", {})
        readiness = context.get("release_readiness", {})
        readiness_summary = readiness.get("summary", {})
        portfolio_manifest = context.get("portfolio_manifest", {})
        counts = portfolio_manifest.get("counts", {}) if isinstance(portfolio_manifest, dict) else {}
        return {
            "source_count": context.get("onboarding", {}).get("source_count", 0),
            "profile_count": context.get("profile_dashboard", {}).get("profile_count", context.get("profile_dashboard", {}).get("implemented_profile_count", 0)),
            "profile_result_rows": context.get("profile_result_rows", 0),
            "pedestrian_generators": counts.get("pedestrian_generators", validation.get("generators")),
            "crossings": counts.get("crossings", validation.get("crossings")),
            "traffic_signals": counts.get("traffic_signals"),
            "api_checked_endpoints": context.get("api_contract", {}).get("checked_endpoints", 0),
            "readiness_level": readiness.get("readiness_level"),
            "readiness_gate_count": readiness_summary.get("gate_count", 0),
            "readiness_failed_gate_count": readiness_summary.get("failed_gate_count", 0),
            "portfolio_report_count": len(context.get("reports", [])),
            "export_bundle_count": len(context.get("bundles", [])),
            "promotion_regression_previews": context.get("promotion", {}).get("regression_preview_count", 0),
        }

    def demo_steps(self, context: dict) -> list[dict]:
        metrics = self.demo_metrics(context)
        architecture = context.get("architecture", {})
        profile_summaries = context.get("profile_summaries", [])
        reports = context.get("reports", [])
        roadmap = context.get("roadmap", {}).get("roadmap", [])
        next_release = next((row for row in roadmap if row.get("status") == "next"), {})
        return [
            {
                "step_id": "opening_positioning",
                "title": "Position the product",
                "duration_min": 1,
                "talk_track": "GeoReview Studio is a local-first GIS workbench for infrastructure review indicators and data-quality evidence.",
                "show_in_ui": ["Product Architecture", "Release Readiness"],
                "evidence": {
                    "recommended_variant": architecture.get("recommended_variant_id"),
                    "current_version": architecture.get("current_version"),
                    "approved_wording": self.review_wording,
                },
                "reviewer_takeaway": "The project has a clear claim boundary and a reusable product direction.",
            },
            {
                "step_id": "data_intake_evidence",
                "title": "Show the inspected local data",
                "duration_min": 1,
                "talk_track": "The app scans local OSM/GIS sources read-only and turns source readiness into explicit evidence.",
                "show_in_ui": ["Source Onboarding", "Local Intake"],
                "evidence": {
                    "source_count": metrics.get("source_count"),
                    "source_readiness": context.get("onboarding", {}).get("readiness_level") or context.get("onboarding", {}).get("default_readiness"),
                    "source_gis_modified": False,
                },
                "reviewer_takeaway": "The data pipeline starts from inspected files, not assumptions.",
            },
            {
                "step_id": "safe_access_profile",
                "title": "Walk through Safe Access Kfar Saba",
                "duration_min": 1,
                "talk_track": "Use schools, childcare, bus stops, parks and crossings to prioritize field-review candidates.",
                "show_in_ui": ["Map", "Profile Dashboard", "Candidate table"],
                "evidence": {
                    "pedestrian_generators": metrics.get("pedestrian_generators"),
                    "crossings": metrics.get("crossings"),
                    "traffic_signals": metrics.get("traffic_signals"),
                    "review_wording": self.review_wording,
                },
                "reviewer_takeaway": "The MVP produces review candidates without claiming real-world harm.",
            },
            {
                "step_id": "multi_profile_expansion",
                "title": "Show reusable profile expansion",
                "duration_min": 1,
                "talk_track": "The same source and pilot support Safe Access, transit stop walk access, park/playground access and authored audits.",
                "show_in_ui": ["Analysis Profiles", "Profile Dashboard", "Profile Runners"],
                "evidence": {
                    "profile_count": metrics.get("profile_count"),
                    "profile_result_rows": metrics.get("profile_result_rows"),
                    "profiles": profile_summaries[:6],
                },
                "reviewer_takeaway": "This is a reusable analytics workbench, not a one-off notebook.",
            },
            {
                "step_id": "quality_and_governance",
                "title": "Explain engineering quality gates",
                "duration_min": 1,
                "talk_track": "Scoring rules, release readiness, contract diffs and regression previews make the workflow reviewable.",
                "show_in_ui": ["Scoring Rules", "Profile Promotion", "Release Readiness"],
                "evidence": {
                    "readiness_level": metrics.get("readiness_level"),
                    "readiness_gate_count": metrics.get("readiness_gate_count"),
                    "readiness_failed_gate_count": metrics.get("readiness_failed_gate_count"),
                    "api_checked_endpoints": metrics.get("api_checked_endpoints"),
                    "promotion_regression_previews": metrics.get("promotion_regression_previews"),
                },
                "reviewer_takeaway": "The app includes guardrails, tests and reproducible evidence.",
            },
            {
                "step_id": "portfolio_outputs",
                "title": "Show exportable outputs",
                "duration_min": 1,
                "talk_track": "Reports, export bundles and snapshots make the analysis portable for review.",
                "show_in_ui": ["Portfolio Reports", "Dataset Packages", "Release Readiness"],
                "evidence": {
                    "portfolio_report_count": metrics.get("portfolio_report_count"),
                    "export_bundle_count": metrics.get("export_bundle_count"),
                    "recent_reports": [{"report_id": row.get("report_id"), "report_type": row.get("report_type")} for row in reports[:5]],
                },
                "reviewer_takeaway": "The project can produce artifacts outside the live app.",
            },
            {
                "step_id": "next_development_path",
                "title": "Close with the next roadmap step",
                "duration_min": 1,
                "talk_track": "The next release should package the demo story and evidence into a review bundle that is easier to share.",
                "show_in_ui": ["Product Architecture", "Portfolio Demo"],
                "evidence": {
                    "next_release": next_release,
                    "source_gis_modified": False,
                    "mutates_config": False,
                },
                "reviewer_takeaway": "The project has a credible path from local MVP to a stronger analytics product.",
            },
        ]

    def snapshot_markdown(self, snapshot: dict) -> str:
        overview = snapshot.get("overview", {})
        lines = [
            "# GeoReview Studio Guided Portfolio Walkthrough",
            "",
            f"Snapshot: `{snapshot.get('snapshot_id')}`",
            f"Created: `{snapshot.get('created_at')}`",
            f"App version: `{snapshot.get('app_version')}`",
            "",
            "Approved review wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Demo Steps",
            "",
        ]
        for step in overview.get("steps", []):
            lines.append(f"### {step.get('title')}")
            lines.append("")
            lines.append(str(step.get("talk_track") or ""))
            lines.append("")
            lines.append(f"Reviewer takeaway: {step.get('reviewer_takeaway')}")
            lines.append("")
        lines.extend([
            "## Metrics",
            "",
        ])
        for key, value in (overview.get("demo_metrics") or {}).items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            "This walkthrough presents infrastructure review indicators and data-quality evidence for field-review prioritization.",
            "It does not make crash-prediction or absolute safety claims.",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)
