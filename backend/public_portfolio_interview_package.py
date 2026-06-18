from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PUBLIC_PORTFOLIO_INTERVIEW_PACKAGE_VERSION = "public_portfolio_interview_package_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "public_portfolio_package", max_len: int = 150) -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:max_len] or fallback


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
        return {"error": "public_portfolio_package_probe_failed", "detail": repr(exc)}


class PublicPortfolioInterviewPackageBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        recruiter_demo_brief: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.recruiter_demo_brief = recruiter_demo_brief
        self.expected_api_endpoints = expected_api_endpoints
        self.packages_dir = output_root / "georeview_studio_public_portfolio_packages"

    def status(self) -> dict:
        briefs = self.ready_recruiter_briefs(100)
        packages = self.list_packages(100)
        ready_packages = [row for row in packages if row.get("package_readiness") == "ready_for_public_portfolio_package"]
        latest_brief = briefs[0] if briefs else {}
        latest_package = ready_packages[0] if ready_packages else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "public_portfolio_interview_package_version": PUBLIC_PORTFOLIO_INTERVIEW_PACKAGE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "package_public_portfolio_interview_material",
            "output_dir": str(self.packages_dir),
            "ready_recruiter_demo_brief_count": len(briefs),
            "latest_recruiter_demo_brief_id": latest_brief.get("brief_id", ""),
            "latest_recruiter_demo_brief_status": latest_brief.get("brief_status", ""),
            "package_count": len(packages),
            "ready_package_count": len(ready_packages),
            "latest_package_id": latest_package.get("package_id", ""),
            "latest_package_status": latest_package.get("package_status", ""),
            "latest_readme_section_count": latest_package.get("readme_section_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_public_portfolio_package" if briefs else "waiting_for_recruiter_demo_brief",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_package(self, body: dict | None = None) -> dict:
        body = body or {}
        brief_id = str(body.get("brief_id") or "").strip()
        if not brief_id:
            briefs = self.ready_recruiter_briefs(20)
            brief_id = str(briefs[0].get("brief_id") or "") if briefs else ""
        if not brief_id:
            return self.error("public_portfolio_package_input_missing", "A ready recruiter demo brief is required.")
        brief = self.resolve_brief(brief_id)
        if brief.get("error"):
            return brief
        if brief.get("brief_readiness") != "ready_for_recruiter_demo":
            return self.error("public_portfolio_package_not_ready", "Recruiter demo brief must be ready_for_recruiter_demo.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        evidence = self.evidence_summary(brief, validation, api_contract, manifest)
        readme_sections = self.readme_sections(brief, evidence)
        interview_steps = self.interview_steps(brief, evidence)
        architecture_notes = self.architecture_notes(evidence)
        implementation_plan = self.implementation_plan()
        stamp = utc_now()
        package_id = f"public_portfolio_package_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        package_dir = self.package_dir(package_id)
        manifest_path = package_dir / "public_portfolio_interview_package_manifest.json"
        readme_path = package_dir / "public_portfolio_readme.md"
        interview_path = package_dir / "interview_walkthrough.md"
        html_path = package_dir / "public_portfolio_interview_package.html"
        latest_path = self.packages_dir / "latest_public_portfolio_interview_package.json"
        package = {
            "ok": True,
            "public_portfolio_interview_package_version": PUBLIC_PORTFOLIO_INTERVIEW_PACKAGE_VERSION,
            "package_id": package_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "portfolio_reviewer"),
            "notes": str(body.get("notes") or "Public portfolio README and interview package for GeoReview Studio."),
            "app_version": self.app_version,
            "recruiter_demo_brief_id": brief.get("brief_id"),
            "package_readiness": "ready_for_public_portfolio_package",
            "package_status": evidence.get("package_status"),
            "readme_section_count": len(readme_sections),
            "interview_step_count": len(interview_steps),
            "architecture_note_count": len(architecture_notes),
            "headline": "GeoReview Studio: local-first GIS analytics for infrastructure review indicators",
            "public_one_liner": "A reusable GIS review workbench that ingests local OSM/Geofabrik evidence, runs transparent infrastructure indicator profiles, and packages the results for field-review prioritization.",
            "readme_sections": readme_sections,
            "interview_steps": interview_steps,
            "architecture_notes": architecture_notes,
            "implementation_plan": implementation_plan,
            "claim_boundaries": self.claim_boundaries(),
            "evidence_summary": evidence,
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "readme": str(readme_path),
                "interview_walkthrough": str(interview_path),
                "html": str(html_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, package)
        write_json(latest_path, package)
        readme_path.write_text(self.readme_markdown(package), encoding="utf-8", newline="\n")
        interview_path.write_text(self.interview_markdown(package), encoding="utf-8", newline="\n")
        html_path.write_text(self.package_html(package), encoding="utf-8", newline="\n")
        return {"ok": True, "package": package, "source_gis_modified": False, "mutates_config": False}

    def list_packages(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.packages_dir.exists():
            return rows
        manifests = sorted(
            self.packages_dir.glob("public_portfolio_package_*/public_portfolio_interview_package_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("public_portfolio_interview_package_version") != PUBLIC_PORTFOLIO_INTERVIEW_PACKAGE_VERSION:
                continue
            rows.append({
                "package_id": payload.get("package_id"),
                "created_at": payload.get("created_at"),
                "package_readiness": payload.get("package_readiness"),
                "package_status": payload.get("package_status"),
                "recruiter_demo_brief_id": payload.get("recruiter_demo_brief_id"),
                "readme_section_count": payload.get("readme_section_count"),
                "interview_step_count": payload.get("interview_step_count"),
                "download_url": f"/api/public-portfolio-package/packages/{payload.get('package_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, package_id: str) -> dict:
        path = self.package_dir(package_id) / "public_portfolio_interview_package_manifest.json"
        if not path.exists() or not self.safe_package_path(path):
            return {"ok": False, "error": "public_portfolio_package_not_found", "package_id": package_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "public_portfolio_package_not_found", "package_id": package_id, "source_gis_modified": False}
        return payload

    def output_file(self, package_id: str, output_id: str = "html") -> dict:
        detail = self.detail(package_id)
        if detail.get("error"):
            return detail
        if output_id not in {"html", "review"}:
            return {"ok": False, "error": "public_portfolio_package_output_not_found", "package_id": package_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists() or not self.safe_package_path(path):
            return {"ok": False, "error": "public_portfolio_package_output_not_found", "package_id": package_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_recruiter_briefs(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.recruiter_demo_brief.list_briefs(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("brief_readiness") == "ready_for_recruiter_demo"]

    def resolve_brief(self, brief_id: str) -> dict:
        detail = safe_call(lambda: self.recruiter_demo_brief.detail(brief_id), {})
        return detail if isinstance(detail, dict) else self.error("recruiter_demo_brief_not_found", "Recruiter demo brief detail failed.")

    def evidence_summary(self, brief: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        validation_passed = validation.get("passed") is True
        api_passed = api_contract.get("passed") is True and api_checked >= self.expected_api_endpoints
        brief_status = str(brief.get("brief_status") or "")
        package_status = "ready_for_public_portfolio_review"
        if brief_status == "ready_with_reviewer_attention_items":
            package_status = "ready_with_reviewer_attention_items"
        if not validation_passed or not api_passed:
            package_status = "pending_validation_or_api_contract"
        return {
            "package_status": package_status,
            "brief_status": brief_status,
            "brief_id": brief.get("brief_id"),
            "validation_passed": validation_passed,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "validation_failed_gates": validation.get("release_readiness_failed_gates", ""),
            "api_contract_passed": api_passed,
            "api_contract_checked_endpoints": api_checked,
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
            "current_release_focus": manifest.get("current_release_focus") if isinstance(manifest, dict) else "",
            "generators": validation.get("generators", 0),
            "crossings": validation.get("crossings", 0),
            "route_aware_rows": validation.get("route_aware_rows", 0),
            "network_nodes": validation.get("route_aware_network_nodes", 0),
            "review_wording": self.review_wording,
        }

    def readme_sections(self, brief: dict, evidence: dict) -> list[dict]:
        return [
            {"title": "Project Value", "body": "GeoReview Studio helps turn local GIS and OSM evidence into reviewable infrastructure indicators, not absolute field claims."},
            {"title": "Best Portfolio Angle", "body": "The strongest story is a universal local-first GIS review studio with Safe Access Israel as the first concrete profile."},
            {"title": "MVP Scope", "body": "Kfar Saba pilot, pedestrian generators, crossings, major-road proximity, route-aware metrics, transparent flags and exportable evidence."},
            {"title": "Data Evidence", "body": f"Current validation references {evidence.get('generators')} generators, {evidence.get('crossings')} crossings and {evidence.get('route_aware_rows')} route-aware rows."},
            {"title": "Architecture", "body": "The app separates source onboarding, profile contracts, controlled execution, evidence packages, release gates, dashboard API and reviewer artifacts."},
            {"title": "Analytics", "body": "Useful insights include nearest crossing distance, crossing availability buffers, major-road exposure, traffic signal context and missing-tag data-quality flags."},
            {"title": "Validation", "body": f"Release readiness is {evidence.get('validation_release_readiness')}; API evidence covers {evidence.get('api_contract_checked_endpoints')} checked endpoints."},
            {"title": "Claim Boundary", "body": self.review_wording},
            {"title": "Next Step", "body": "v073 should add a demo review playbook and final sharing checklist for portfolio publication."},
        ]

    def interview_steps(self, brief: dict, evidence: dict) -> list[dict]:
        return [
            {"order": 1, "question": "What problem does this solve?", "answer": "It prioritizes places for on-site pedestrian infrastructure review using mapped indicators and transparent uncertainty flags."},
            {"order": 2, "question": "Why is this useful beyond one city?", "answer": "The profile contract model can ingest other local OSM/GIS extracts and produce comparable dashboards and reports."},
            {"order": 3, "question": "What are the hard engineering parts?", "answer": "GIS source inspection, CRS-aware distance analysis, schema normalization, reproducible outputs, API coverage and claim-boundary enforcement."},
            {"order": 4, "question": "What insight can we show now?", "answer": "Kfar Saba pilot can show generators with long mapped crossing access, major-road proximity and explicit infrastructure tags where available."},
            {"order": 5, "question": "What are the data limitations?", "answer": "Missing OSM tags are data-quality gaps; they are not treated as proof that real-world infrastructure is absent."},
            {"order": 6, "question": "How would this become production-grade?", "answer": "Move generated artifacts into PostGIS, add authenticated review sessions, upload guardrails, repeatable jobs and a hosted MapLibre frontend."},
        ]

    def architecture_notes(self, evidence: dict) -> list[dict]:
        return [
            {"layer": "Source Onboarding", "decision": "Read local GIS files as evidence and never mutate source data."},
            {"layer": "Profile Contracts", "decision": "Represent Safe Access, Transit and Park analysis as reusable profile contracts."},
            {"layer": "Spatial Analytics", "decision": "Use projected CRS for metric calculations and keep risk flags separate from data-quality flags."},
            {"layer": "Evidence Packaging", "decision": "Generate JSON, Markdown and HTML artifacts that can be reviewed without rerunning heavy GIS work."},
            {"layer": "Release Gates", "decision": "Make validation, API contract, docs and UI integration visible through release-readiness checks."},
            {"layer": "Future Backend", "decision": "Use PostGIS when the scope grows from local pilot artifacts to larger regional datasets and concurrent users."},
        ]

    def implementation_plan(self) -> list[dict]:
        return [
            {"phase": "v0.1", "scope": "Kfar Saba Safe Access pilot", "deliverable": "Dashboard, CSV exports and top review candidates."},
            {"phase": "v0.2", "scope": "Universal source intake", "deliverable": "Load additional OSM/GIS datasets through guarded metadata-only intake."},
            {"phase": "v0.3", "scope": "Profile marketplace", "deliverable": "Reusable profiles for pedestrian access, transit stops, parks and tag quality."},
            {"phase": "v0.4", "scope": "PostGIS migration", "deliverable": "Spatial database, indexed queries and larger-region analysis."},
            {"phase": "v0.5", "scope": "Reviewer workflow", "deliverable": "Review sessions, annotations, status tracking and shareable reports."},
        ]

    def claim_boundaries(self) -> list[str]:
        return [
            self.review_wording,
            "This is an infrastructure indicator and field-review prioritization tool, not a crash prediction model.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "Scores are transparent prioritization aids and should be calibrated through field review.",
        ]

    def readme_markdown(self, package: dict) -> str:
        lines = [
            "# GeoReview Studio",
            "",
            package.get("public_one_liner", ""),
            "",
            f"- Package id: `{package.get('package_id')}`",
            f"- App version: `{package.get('app_version')}`",
            f"- Readiness: `{package.get('package_readiness')}`",
            f"- Status: `{package.get('package_status')}`",
            "",
            "## Public Portfolio README",
            "",
        ]
        for section in package.get("readme_sections", []):
            lines.append(f"### {section.get('title')}")
            lines.append(section.get("body", ""))
            lines.append("")
        lines.extend([
            "## Architecture Notes",
            "",
        ])
        for note in package.get("architecture_notes", []):
            lines.append(f"- **{note.get('layer')}**: {note.get('decision')}")
        lines.extend(["", "## Implementation Plan", ""])
        for item in package.get("implementation_plan", []):
            lines.append(f"- **{item.get('phase')}**: {item.get('scope')} - {item.get('deliverable')}")
        lines.extend(["", "## Claim Boundaries", ""])
        for line in package.get("claim_boundaries", []):
            lines.append(f"- {line}")
        lines.extend(["", "Source GIS files remain read-only.", ""])
        return "\n".join(lines)

    def interview_markdown(self, package: dict) -> str:
        lines = [
            "# Public Portfolio Interview Package",
            "",
            f"Package id: `{package.get('package_id')}`",
            "",
            "## Interview Walkthrough",
            "",
        ]
        for step in package.get("interview_steps", []):
            lines.append(f"{step.get('order')}. **{step.get('question')}**")
            lines.append(f"   {step.get('answer')}")
            lines.append("")
        lines.extend(["## Approved Review Wording", "", f"`{self.review_wording}`", ""])
        return "\n".join(lines)

    def package_html(self, package: dict) -> str:
        sections = "".join(
            f"<section><h2>{html.escape(str(section.get('title') or ''))}</h2><p>{html.escape(str(section.get('body') or ''))}</p></section>"
            for section in package.get("readme_sections", [])
        )
        steps = "".join(
            f"<tr><td>{step.get('order')}</td><td>{html.escape(str(step.get('question') or ''))}</td><td>{html.escape(str(step.get('answer') or ''))}</td></tr>"
            for step in package.get("interview_steps", [])
        )
        architecture = "".join(
            f"<li><strong>{html.escape(str(note.get('layer') or ''))}:</strong> {html.escape(str(note.get('decision') or ''))}</li>"
            for note in package.get("architecture_notes", [])
        )
        plan = "".join(
            f"<li><strong>{html.escape(str(item.get('phase') or ''))}:</strong> {html.escape(str(item.get('scope') or ''))} - {html.escape(str(item.get('deliverable') or ''))}</li>"
            for item in package.get("implementation_plan", [])
        )
        boundaries = "".join(f"<li>{html.escape(line)}</li>" for line in package.get("claim_boundaries", []))
        evidence = package.get("evidence_summary", {})
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Public Portfolio Interview Package</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f8f4; color: #1f2933; }}
      .summary, section {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
      table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 8px; }}
      th, td {{ border: 1px solid #d7d8d2; padding: 8px; vertical-align: top; }}
      th {{ background: #eef0ea; text-align: left; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Public Portfolio Interview Package</h1>
    <div class="summary">
      <p><strong>{html.escape(str(package.get("headline") or ""))}</strong></p>
      <p>{html.escape(str(package.get("public_one_liner") or ""))}</p>
      <p>Package: <code>{html.escape(str(package.get("package_id") or ""))}</code>; status: <code>{html.escape(str(package.get("package_status") or ""))}</code>.</p>
      <p>Release readiness: <code>{html.escape(str(evidence.get("validation_release_readiness") or ""))}</code>; checked endpoints: <code>{html.escape(str(evidence.get("api_contract_checked_endpoints") or 0))}</code>.</p>
    </div>
    {sections}
    <section>
      <h2>Interview Walkthrough</h2>
      <table><thead><tr><th>#</th><th>Question</th><th>Answer</th></tr></thead><tbody>{steps}</tbody></table>
    </section>
    <section><h2>Architecture Notes</h2><ul>{architecture}</ul></section>
    <section><h2>Implementation Plan</h2><ul>{plan}</ul></section>
    <section><h2>Claim Boundaries</h2><ul>{boundaries}</ul></section>
  </body>
</html>"""

    def package_dir(self, package_id: str) -> Path:
        return self.packages_dir / safe_token(package_id, "missing_public_portfolio_package", 180)

    def safe_package_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.packages_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
