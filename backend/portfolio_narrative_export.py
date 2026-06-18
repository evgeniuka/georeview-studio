from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PORTFOLIO_NARRATIVE_EXPORT_VERSION = "portfolio_narrative_export_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "portfolio_narrative") -> str:
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


def read_text(path: Path, limit: int = 9000) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def safe_call(fn: Callable[[], object], default: object) -> object:
    try:
        result = fn()
        return result if result is not None else default
    except Exception as exc:
        return {"error": "portfolio_narrative_probe_failed", "detail": repr(exc)}


class PortfolioNarrativeExporter:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        dependencies: dict[str, object],
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.dependencies = dependencies
        self.expected_api_endpoints = expected_api_endpoints
        self.narratives_dir = output_root / "georeview_studio_portfolio_narratives"
        self.checklists_dir = output_root / "georeview_studio_bundle_review_checklists"

    def status(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        latest_checklist = self.latest_checklist()
        latest_narrative = self.list_narratives(1)
        return {
            "ok": True,
            "portfolio_narrative_export_version": PORTFOLIO_NARRATIVE_EXPORT_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "narrative_count": len(self.list_narratives(500)),
            "latest_checklist_id": latest_checklist.get("checklist_id") if latest_checklist else "",
            "latest_checklist_readiness": latest_checklist.get("summary", {}).get("review_readiness") if latest_checklist else "",
            "latest_narrative_id": latest_narrative[0].get("narrative_id") if latest_narrative else "",
            "default_action": "create_portfolio_narrative_export",
            "narrative_sections": [section.get("section_id") for section in self.default_sections()],
            "output_dir": str(self.narratives_dir),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_narrative(self, body: dict | None = None) -> dict:
        body = body or {}
        checklist = self.resolve_checklist(body)
        if not checklist:
            return {"ok": False, "error": "bundle_review_checklist_not_found", "source_gis_modified": False, "mutates_config": False}
        bundle = self.resolve_bundle(checklist)
        evidence = self.evidence_from_bundle(bundle)
        readiness = self.narrative_readiness(checklist, evidence)
        stamp = utc_now()
        narrative_id = f"portfolio_narrative_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        sections = self.build_sections(checklist, bundle, evidence)
        narrative = {
            "ok": True,
            "narrative_id": narrative_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer-facing portfolio narrative export."),
            "portfolio_narrative_export_version": PORTFOLIO_NARRATIVE_EXPORT_VERSION,
            "app_version": self.app_version,
            "checklist_id": checklist.get("checklist_id"),
            "checklist_readiness": checklist.get("summary", {}).get("review_readiness"),
            "bundle_id": checklist.get("bundle_id"),
            "bundle_readiness": bundle.get("readiness_level"),
            "narrative_readiness": readiness,
            "evidence_summary": self.evidence_summary(evidence),
            "sections": sections,
            "talk_track": self.talk_track(evidence),
            "reviewer_handoff": self.reviewer_handoff(readiness),
            "approved_review_wording": self.review_wording,
            "claim_boundary": "Portfolio narrative explains infrastructure indicators, data-quality flags and engineering evidence; it is not a crash prediction artifact.",
            "source_gis_modified": False,
            "mutates_config": False,
        }
        json_path = self.narratives_dir / f"{narrative_id}.json"
        md_path = self.narratives_dir / f"{narrative_id}.md"
        latest_path = self.narratives_dir / "latest_portfolio_narrative.json"
        narrative["files"] = {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)}
        write_json(json_path, narrative)
        write_json(latest_path, narrative)
        md_path.write_text(self.narrative_markdown(narrative), encoding="utf-8", newline="\n")
        return {"ok": True, "narrative": narrative, "source_gis_modified": False, "mutates_config": False}

    def resolve_checklist(self, body: dict) -> dict:
        checklist_id = str(body.get("checklist_id") or "")
        checklists = self.dependencies.get("bundle_review_checklist")
        if checklist_id and checklists:
            detail = safe_call(lambda: checklists.detail(checklist_id), {})
            return detail if isinstance(detail, dict) and not detail.get("error") else {}
        if body.get("create_checklist", True) and checklists:
            result = safe_call(
                lambda: checklists.create_checklist({
                    "created_by": str(body.get("created_by") or "portfolio_narrative_export"),
                    "notes": "Narrative-created bundle review checklist.",
                    "create_bundle": body.get("create_bundle", True),
                    "reuse_latest": body.get("reuse_latest", True),
                }),
                {},
            )
            if isinstance(result, dict) and result.get("ok"):
                checklist = result.get("checklist", {})
                return checklist if isinstance(checklist, dict) else {}
        return self.latest_checklist()

    def latest_checklist(self) -> dict:
        latest = read_json(self.checklists_dir / "latest_bundle_review_checklist.json")
        if latest:
            return latest
        checklists = self.dependencies.get("bundle_review_checklist")
        if checklists:
            rows = safe_call(lambda: checklists.list_checklists(1), [])
            if isinstance(rows, list) and rows:
                detail = safe_call(lambda: checklists.detail(str(rows[0].get("checklist_id") or "")), {})
                return detail if isinstance(detail, dict) else {}
        return {}

    def resolve_bundle(self, checklist: dict) -> dict:
        bundle_id = str(checklist.get("bundle_id") or "")
        portfolio_bundle = self.dependencies.get("portfolio_evidence_bundle")
        if bundle_id and portfolio_bundle:
            detail = safe_call(lambda: portfolio_bundle.detail(bundle_id), {})
            return detail if isinstance(detail, dict) and not detail.get("error") else {}
        return {}

    def evidence_from_bundle(self, bundle: dict) -> dict:
        copied_files = bundle.get("copied_files", []) if isinstance(bundle, dict) else []
        by_label = {str(item.get("label") or ""): Path(str(item.get("bundle_path") or "")) for item in copied_files}
        sample_rows = self.sample_csv_rows(by_label.get("sample_review_candidates", Path("")))
        return {
            "manifest": read_json(by_label.get("project_manifest", Path(""))),
            "validation": read_json(by_label.get("validation_summary", Path(""))),
            "api_contract": read_json(by_label.get("api_contract_summary", Path(""))),
            "portfolio_manifest": read_json(by_label.get("portfolio_manifest", Path(""))),
            "case_study_excerpt": read_text(by_label.get("portfolio_case_study", Path("")), limit=3500),
            "pitch_excerpt": read_text(by_label.get("portfolio_pitch", Path("")), limit=1800),
            "sample_rows": sample_rows[:5],
            "copied_file_count": len(copied_files),
            "copied_labels": sorted(by_label),
        }

    def sample_csv_rows(self, path: Path) -> list[dict]:
        try:
            if not path.exists():
                return []
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        except OSError:
            return []

    def narrative_readiness(self, checklist: dict, evidence: dict) -> str:
        summary = checklist.get("summary", {})
        validation = evidence.get("validation", {})
        api_contract = evidence.get("api_contract", {})
        if summary.get("failed_count", 0) > 0:
            return "not_ready_for_reviewer"
        if (
            summary.get("review_readiness") == "ready_to_share"
            and validation.get("passed") is True
            and validation.get("app_version") == self.app_version
            and api_contract.get("passed") is True
            and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints
        ):
            return "ready_for_reviewer"
        return "ready_with_review_warnings"

    def evidence_summary(self, evidence: dict) -> dict:
        validation = evidence.get("validation", {})
        api_contract = evidence.get("api_contract", {})
        manifest = evidence.get("manifest", {})
        return {
            "project_version": manifest.get("version"),
            "local_url": manifest.get("local_url"),
            "validation_passed": validation.get("passed"),
            "api_contract_passed": api_contract.get("passed"),
            "checked_endpoints": api_contract.get("checked_endpoints"),
            "pedestrian_generators": validation.get("generators") or validation.get("pbf_enriched_generators"),
            "crossings": validation.get("crossings") or validation.get("pbf_enriched_crossings"),
            "route_aware_rows": validation.get("route_aware_rows"),
            "route_aware_median_crossing_m": validation.get("route_aware_median_crossing_m"),
            "implemented_profiles": validation.get("profile_dashboard_profiles"),
            "copied_file_count": evidence.get("copied_file_count"),
            "sample_row_count": len(evidence.get("sample_rows", [])),
        }

    def default_sections(self) -> list[dict]:
        return [
            {"section_id": "positioning", "title": "Positioning"},
            {"section_id": "data_evidence", "title": "Data Evidence"},
            {"section_id": "analytics", "title": "Analytics"},
            {"section_id": "engineering", "title": "Engineering"},
            {"section_id": "claim_boundary", "title": "Claim Boundary"},
            {"section_id": "reviewer_walkthrough", "title": "Reviewer Walkthrough"},
            {"section_id": "next_steps", "title": "Next Steps"},
        ]

    def build_sections(self, checklist: dict, bundle: dict, evidence: dict) -> list[dict]:
        summary = self.evidence_summary(evidence)
        return [
            {
                "section_id": "positioning",
                "title": "Positioning",
                "body": "GeoReview Studio is a local-first GIS review workbench for infrastructure risk indicators, OSM data-quality evidence and reproducible portfolio analytics.",
                "evidence": {"app_version": self.app_version, "bundle_id": bundle.get("bundle_id"), "checklist_id": checklist.get("checklist_id")},
            },
            {
                "section_id": "data_evidence",
                "title": "Data Evidence",
                "body": "The Kfar Saba pilot uses inspected OSM/Geofabrik-derived layers, generated workspaces and copied evidence artifacts instead of unverified claims.",
                "evidence": {
                    "pedestrian_generators": summary.get("pedestrian_generators"),
                    "crossings": summary.get("crossings"),
                    "copied_file_count": summary.get("copied_file_count"),
                },
            },
            {
                "section_id": "analytics",
                "title": "Analytics",
                "body": "The project computes review-priority indicators such as crossing access, major-road proximity, route-aware distances and profile-specific scores.",
                "evidence": {
                    "route_aware_rows": summary.get("route_aware_rows"),
                    "route_aware_median_crossing_m": summary.get("route_aware_median_crossing_m"),
                    "implemented_profiles": summary.get("implemented_profiles"),
                },
            },
            {
                "section_id": "engineering",
                "title": "Engineering",
                "body": "The implementation exposes reusable profile contracts, API coverage, validation summaries, generated reports and local review dashboards.",
                "evidence": {
                    "validation_passed": summary.get("validation_passed"),
                    "api_contract_passed": summary.get("api_contract_passed"),
                    "checked_endpoints": summary.get("checked_endpoints"),
                },
            },
            {
                "section_id": "claim_boundary",
                "title": "Claim Boundary",
                "body": "The narrative stays within infrastructure indicators and field-review prioritization. Missing OSM tags are treated as data-quality flags, not real-world absence.",
                "evidence": {"approved_review_wording": self.review_wording},
            },
            {
                "section_id": "reviewer_walkthrough",
                "title": "Reviewer Walkthrough",
                "body": "A reviewer can open the local app, inspect the checklist, download the bundle report, and trace each claim to generated evidence files.",
                "evidence": {"checklist_readiness": checklist.get("summary", {}).get("review_readiness")},
            },
            {
                "section_id": "next_steps",
                "title": "Next Steps",
                "body": "The next product step is turning the narrative into a compact HTML handoff page and then adding more reusable analysis profiles.",
                "evidence": {"recommended_next_release": "v054 execution evidence packaging"},
            },
        ]

    def talk_track(self, evidence: dict) -> list[dict]:
        summary = self.evidence_summary(evidence)
        return [
            {"step": 1, "title": "Problem framing", "talking_point": "This is infrastructure review prioritization, not a crash model."},
            {"step": 2, "title": "Data audit", "talking_point": f"The pilot evidence includes {summary.get('pedestrian_generators')} generators and {summary.get('crossings')} crossings where available."},
            {"step": 3, "title": "Reusable analytics", "talking_point": "Safe Access, Transit and Park profiles share the same dashboard contract."},
            {"step": 4, "title": "Engineering quality", "talking_point": f"Validation and API contract evidence cover {summary.get('checked_endpoints')} endpoints in this release."},
            {"step": 5, "title": "Governance", "talking_point": "Source GIS files remain read-only and generated artifacts stay under analysis_output."},
            {"step": 6, "title": "Handoff", "talking_point": "The checklist and narrative make the portfolio review traceable and compact."},
        ]

    def reviewer_handoff(self, readiness: str) -> dict:
        return {
            "readiness": readiness,
            "recommended_demo_order": [
                "Open release readiness",
                "Open bundle review checklist",
                "Download portfolio evidence bundle",
                "Read this narrative export",
                "Inspect Safe Access candidates and profile dashboards",
            ],
            "shareable_artifacts": ["narrative Markdown", "narrative JSON", "bundle Markdown", "checklist Markdown"],
        }

    def list_narratives(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.narratives_dir.exists():
            return rows
        for path in sorted(self.narratives_dir.glob("portfolio_narrative_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "narrative_id": payload.get("narrative_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "checklist_id": payload.get("checklist_id"),
                "bundle_id": payload.get("bundle_id"),
                "narrative_readiness": payload.get("narrative_readiness"),
                "json_file": str(path),
                "markdown_file": payload.get("files", {}).get("markdown"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, narrative_id: str) -> dict:
        token = safe_token(narrative_id, "missing")
        path = self.narratives_dir / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "portfolio_narrative_not_found", "narrative_id": narrative_id, "source_gis_modified": False}
        return payload

    def output_file(self, narrative_id: str, output_id: str = "portfolio_narrative_report") -> dict:
        detail = self.detail(narrative_id)
        if detail.get("error"):
            return detail
        if output_id not in {"portfolio_narrative_report", "markdown"}:
            return {"ok": False, "error": "portfolio_narrative_output_not_found", "narrative_id": narrative_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists():
            return {"ok": False, "error": "portfolio_narrative_output_not_found", "narrative_id": narrative_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False}

    def narrative_markdown(self, narrative: dict) -> str:
        summary = narrative.get("evidence_summary", {})
        lines = [
            "# GeoReview Studio Portfolio Narrative",
            "",
            f"Narrative: `{narrative.get('narrative_id')}`",
            f"Created: `{narrative.get('created_at')}`",
            f"Readiness: `{narrative.get('narrative_readiness')}`",
            "",
            "Approved review wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Evidence Summary",
            "",
            f"- Project version: `{summary.get('project_version')}`",
            f"- Local URL: `{summary.get('local_url')}`",
            f"- Validation passed: `{summary.get('validation_passed')}`",
            f"- API contract passed: `{summary.get('api_contract_passed')}`",
            f"- Checked endpoints: `{summary.get('checked_endpoints')}`",
            f"- Pedestrian generators: `{summary.get('pedestrian_generators')}`",
            f"- Crossings: `{summary.get('crossings')}`",
            f"- Route-aware rows: `{summary.get('route_aware_rows')}`",
            "",
            "## Narrative",
            "",
        ]
        for section in narrative.get("sections", []):
            lines.extend([f"### {section.get('title')}", "", str(section.get("body") or ""), ""])
        lines.extend(["## Talk Track", ""])
        for item in narrative.get("talk_track", []):
            lines.append(f"{item.get('step')}. **{item.get('title')}** - {item.get('talking_point')}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            "This narrative supports infrastructure review prioritization and data-quality evidence only.",
            "It does not label a location and does not predict crashes.",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)
