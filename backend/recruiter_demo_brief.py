from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


RECRUITER_DEMO_BRIEF_VERSION = "recruiter_demo_brief_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "recruiter_demo_brief", max_len: int = 150) -> str:
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
        return {"error": "recruiter_demo_brief_probe_failed", "detail": repr(exc)}


class RecruiterDemoBriefBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        final_reviewer_launch_checklist: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.final_reviewer_launch_checklist = final_reviewer_launch_checklist
        self.expected_api_endpoints = expected_api_endpoints
        self.briefs_dir = output_root / "georeview_studio_recruiter_demo_briefs"

    def status(self) -> dict:
        checklists = self.ready_launch_checklists(100)
        briefs = self.list_briefs(100)
        ready_briefs = [row for row in briefs if row.get("brief_readiness") == "ready_for_recruiter_demo"]
        latest_checklist = checklists[0] if checklists else {}
        latest_brief = ready_briefs[0] if ready_briefs else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "recruiter_demo_brief_version": RECRUITER_DEMO_BRIEF_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "package_recruiter_demo_brief",
            "output_dir": str(self.briefs_dir),
            "ready_launch_checklist_count": len(checklists),
            "latest_launch_checklist_id": latest_checklist.get("checklist_id", ""),
            "latest_launch_status": latest_checklist.get("launch_status", ""),
            "brief_count": len(briefs),
            "ready_brief_count": len(ready_briefs),
            "latest_brief_id": latest_brief.get("brief_id", ""),
            "latest_brief_status": latest_brief.get("brief_status", ""),
            "latest_section_count": latest_brief.get("section_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_recruiter_demo_brief" if checklists else "waiting_for_final_reviewer_launch_checklist",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_brief(self, body: dict | None = None) -> dict:
        body = body or {}
        checklist_id = str(body.get("checklist_id") or "").strip()
        if not checklist_id:
            checklists = self.ready_launch_checklists(20)
            checklist_id = str(checklists[0].get("checklist_id") or "") if checklists else ""
        if not checklist_id:
            return self.error("recruiter_demo_brief_input_missing", "A ready final reviewer launch checklist is required.")
        checklist = self.resolve_launch_checklist(checklist_id)
        if checklist.get("error"):
            return checklist
        if checklist.get("checklist_readiness") != "ready_for_final_reviewer_launch":
            return self.error("recruiter_demo_brief_not_ready", "Launch checklist must be ready_for_final_reviewer_launch.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        evidence = self.evidence_summary(checklist, validation, api_contract, manifest)
        sections = self.brief_sections(checklist, evidence)
        proof_points = self.proof_points(checklist, evidence)
        demo_flow = self.demo_flow(checklist, evidence)
        stamp = utc_now()
        brief_id = f"recruiter_demo_brief_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        brief_dir = self.brief_dir(brief_id)
        manifest_path = brief_dir / "recruiter_demo_brief_manifest.json"
        markdown_path = brief_dir / "recruiter_demo_brief.md"
        html_path = brief_dir / "recruiter_demo_brief.html"
        latest_path = self.briefs_dir / "latest_recruiter_demo_brief.json"
        brief = {
            "ok": True,
            "recruiter_demo_brief_version": RECRUITER_DEMO_BRIEF_VERSION,
            "brief_id": brief_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "technical_recruiter"),
            "notes": str(body.get("notes") or "One-page portfolio demo brief for GeoReview Studio."),
            "app_version": self.app_version,
            "launch_checklist_id": checklist.get("checklist_id"),
            "signoff_packet_id": checklist.get("signoff_packet_id"),
            "brief_readiness": "ready_for_recruiter_demo",
            "brief_status": evidence.get("brief_status"),
            "section_count": len(sections),
            "proof_point_count": len(proof_points),
            "demo_step_count": len(demo_flow),
            "headline": "GeoReview Studio: local-first GIS evidence workbench for infrastructure review",
            "one_liner": "A portfolio-ready GIS app that turns OSM/Geofabrik data into transparent infrastructure risk indicators, data-quality flags and reviewer evidence.",
            "sections": sections,
            "proof_points": proof_points,
            "demo_flow": demo_flow,
            "must_say_lines": self.must_say_lines(evidence),
            "avoid_claims": self.avoid_claims(),
            "evidence_summary": evidence,
            "download_targets": self.download_targets(checklist, evidence),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "markdown": str(markdown_path),
                "html": str(html_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, brief)
        write_json(latest_path, brief)
        markdown_path.write_text(self.brief_markdown(brief), encoding="utf-8", newline="\n")
        html_path.write_text(self.brief_html(brief), encoding="utf-8", newline="\n")
        return {"ok": True, "brief": brief, "source_gis_modified": False, "mutates_config": False}

    def list_briefs(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.briefs_dir.exists():
            return rows
        manifests = sorted(
            self.briefs_dir.glob("recruiter_demo_brief_*/recruiter_demo_brief_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("recruiter_demo_brief_version") != RECRUITER_DEMO_BRIEF_VERSION:
                continue
            rows.append({
                "brief_id": payload.get("brief_id"),
                "created_at": payload.get("created_at"),
                "brief_readiness": payload.get("brief_readiness"),
                "brief_status": payload.get("brief_status"),
                "launch_checklist_id": payload.get("launch_checklist_id"),
                "section_count": payload.get("section_count"),
                "proof_point_count": payload.get("proof_point_count"),
                "download_url": f"/api/recruiter-demo-brief/briefs/{payload.get('brief_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, brief_id: str) -> dict:
        path = self.brief_dir(brief_id) / "recruiter_demo_brief_manifest.json"
        if not path.exists() or not self.safe_brief_path(path):
            return {"ok": False, "error": "recruiter_demo_brief_not_found", "brief_id": brief_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "recruiter_demo_brief_not_found", "brief_id": brief_id, "source_gis_modified": False}
        return payload

    def output_file(self, brief_id: str, output_id: str = "html") -> dict:
        detail = self.detail(brief_id)
        if detail.get("error"):
            return detail
        if output_id not in {"html", "review"}:
            return {"ok": False, "error": "recruiter_demo_brief_output_not_found", "brief_id": brief_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists() or not self.safe_brief_path(path):
            return {"ok": False, "error": "recruiter_demo_brief_output_not_found", "brief_id": brief_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_launch_checklists(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.final_reviewer_launch_checklist.list_checklists(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("checklist_readiness") == "ready_for_final_reviewer_launch"]

    def resolve_launch_checklist(self, checklist_id: str) -> dict:
        detail = safe_call(lambda: self.final_reviewer_launch_checklist.detail(checklist_id), {})
        return detail if isinstance(detail, dict) else self.error("final_reviewer_launch_checklist_not_found", "Launch checklist detail failed.")

    def evidence_summary(self, checklist: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        validation_passed = validation.get("passed") is True
        api_passed = api_contract.get("passed") is True and api_checked >= self.expected_api_endpoints
        launch_status = str(checklist.get("launch_status") or "")
        brief_status = "ready_for_recruiter_walkthrough"
        if launch_status == "ready_with_reviewer_attention_items":
            brief_status = "ready_with_reviewer_attention_items"
        if not validation_passed or not api_passed:
            brief_status = "pending_validation_or_api_contract"
        return {
            "brief_status": brief_status,
            "launch_status": launch_status,
            "launch_checklist_id": checklist.get("checklist_id"),
            "signoff_packet_id": checklist.get("signoff_packet_id"),
            "launch_action_count": checklist.get("action_count", 0),
            "must_say_count": checklist.get("must_say_count", 0),
            "validation_passed": validation_passed,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "validation_failed_gates": validation.get("release_readiness_failed_gates", ""),
            "api_contract_passed": api_passed,
            "api_contract_checked_endpoints": api_checked,
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
            "profile_rows": validation.get("postgis_profile_result_rows") or validation.get("profile_dashboard_safe_access_rows") or 0,
            "generators": validation.get("generators", 0),
            "crossings": validation.get("crossings", 0),
            "route_aware_rows": validation.get("route_aware_rows", 0),
            "network_nodes": validation.get("route_aware_network_nodes", 0),
        }

    def brief_sections(self, checklist: dict, evidence: dict) -> list[dict]:
        return [
            {"title": "Project", "body": "GeoReview Studio is a local-first GIS analytics workbench built from inspected OSM/Geofabrik data and generated evidence artifacts."},
            {"title": "Problem", "body": "The product helps prioritize pedestrian infrastructure locations for field review near schools, bus stops, parks, playgrounds and crossings."},
            {"title": "Data", "body": f"Kfar Saba pilot evidence includes {evidence.get('generators')} pedestrian generators, {evidence.get('crossings')} crossings and route-aware result rows."},
            {"title": "Engineering", "body": "The app demonstrates source scanning, profile contracts, controlled execution, reproducible reports, API coverage and local dashboard delivery."},
            {"title": "Claim Boundary", "body": self.review_wording},
            {"title": "Demo Proof", "body": f"Validation readiness is {evidence.get('validation_release_readiness')}; API contract checks {evidence.get('api_contract_checked_endpoints')} endpoints."},
            {"title": "Close", "body": "The next production step is replacing local artifacts with PostGIS-backed storage, authenticated review sessions and repeatable deployment automation."},
        ]

    def proof_points(self, checklist: dict, evidence: dict) -> list[dict]:
        return [
            {"label": "Local app", "value": evidence.get("local_url") or "Not available in inspected files"},
            {"label": "Release readiness", "value": evidence.get("validation_release_readiness") or "Not available in inspected files"},
            {"label": "API contract", "value": f"{evidence.get('api_contract_checked_endpoints')} checked endpoints"},
            {"label": "Launch checklist", "value": checklist.get("checklist_id")},
            {"label": "Approved wording", "value": self.review_wording},
        ]

    def demo_flow(self, checklist: dict, evidence: dict) -> list[dict]:
        return [
            {"order": 1, "step": "Open the local app", "show": evidence.get("local_url") or "local dashboard"},
            {"order": 2, "step": "Show the Kfar Saba pilot", "show": "pedestrian generators, crossings, roads and risk flags"},
            {"order": 3, "step": "Explain data quality", "show": "missing OSM tags remain separate data-quality flags"},
            {"order": 4, "step": "Open evidence stack", "show": "validation, API contract, sign-off packet and launch checklist"},
            {"order": 5, "step": "Close with architecture", "show": "local prototype path to PostGIS, API and web map productionization"},
        ]

    def must_say_lines(self, evidence: dict) -> list[str]:
        return [
            self.review_wording,
            "This is an infrastructure indicator and field-review prioritization tool, not a crash prediction model.",
            "Missing OSM tags are data-quality flags, not proof that real-world infrastructure is absent.",
            "The strongest MVP story is Kfar Saba pilot first, then reusable GIS review profiles.",
        ]

    def avoid_claims(self) -> list[str]:
        return [
            "Do not claim crash prediction.",
            "Do not claim field truth from missing OSM tags.",
            "Do not claim that a location is proven to have a safety problem.",
        ]

    def download_targets(self, checklist: dict, evidence: dict) -> list[dict]:
        return [
            {"label": "Dashboard", "url": evidence.get("local_url") or "http://127.0.0.1:8835", "type": "local_app"},
            {"label": "Recruiter demo brief", "url": "self", "type": "html"},
            {"label": "Final launch checklist", "url": f"/api/final-reviewer-launch-checklist/checklists/{checklist.get('checklist_id')}/download", "type": "html"},
            {"label": "Validation summary", "url": str(self.project_dir / "validation_summary.json"), "type": "json"},
            {"label": "API contract summary", "url": str(self.project_dir / "api_contract_summary.json"), "type": "json"},
        ]

    def brief_markdown(self, brief: dict) -> str:
        evidence = brief.get("evidence_summary", {})
        lines = [
            "# Recruiter-Facing Demo Brief",
            "",
            f"- Brief id: `{brief.get('brief_id')}`",
            f"- App version: `{brief.get('app_version')}`",
            f"- Readiness: `{brief.get('brief_readiness')}`",
            f"- Status: `{brief.get('brief_status')}`",
            "",
            f"**One-liner:** {brief.get('one_liner')}",
            "",
            "## Sections",
            "",
        ]
        for section in brief.get("sections", []):
            lines.append(f"- **{section.get('title')}**: {section.get('body')}")
        lines.extend(["", "## Proof Points", ""])
        for point in brief.get("proof_points", []):
            lines.append(f"- {point.get('label')}: `{point.get('value')}`")
        lines.extend(["", "## Demo Flow", ""])
        for step in brief.get("demo_flow", []):
            lines.append(f"{step.get('order')}. {step.get('step')} - {step.get('show')}")
        lines.extend([
            "",
            "## Evidence",
            "",
            f"- Release readiness: `{evidence.get('validation_release_readiness')}`",
            f"- API endpoints: `{evidence.get('api_contract_checked_endpoints')}` / expected `{evidence.get('expected_api_endpoints')}`",
            f"- Launch checklist: `{evidence.get('launch_checklist_id')}`",
            "- Source GIS files remain read-only.",
            "",
        ])
        return "\n".join(lines)

    def brief_html(self, brief: dict) -> str:
        sections = "".join(
            f"<section><h2>{html.escape(str(section.get('title') or ''))}</h2><p>{html.escape(str(section.get('body') or ''))}</p></section>"
            for section in brief.get("sections", [])
        )
        proof_points = "".join(
            f"<li><strong>{html.escape(str(point.get('label') or ''))}:</strong> {html.escape(str(point.get('value') or ''))}</li>"
            for point in brief.get("proof_points", [])
        )
        flow = "".join(
            f"<tr><td>{step.get('order')}</td><td>{html.escape(str(step.get('step') or ''))}</td><td>{html.escape(str(step.get('show') or ''))}</td></tr>"
            for step in brief.get("demo_flow", [])
        )
        must_say = "".join(f"<li>{html.escape(line)}</li>" for line in brief.get("must_say_lines", []))
        avoid = "".join(f"<li>{html.escape(line)}</li>" for line in brief.get("avoid_claims", []))
        evidence = brief.get("evidence_summary", {})
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Recruiter-Facing Demo Brief</title>
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
    <h1>Recruiter-Facing Demo Brief</h1>
    <div class="summary">
      <p><strong>{html.escape(str(brief.get("headline") or ""))}</strong></p>
      <p>{html.escape(str(brief.get("one_liner") or ""))}</p>
      <p>Brief: <code>{html.escape(str(brief.get("brief_id") or ""))}</code>; status: <code>{html.escape(str(brief.get("brief_status") or ""))}</code>.</p>
      <p>Release readiness: <code>{html.escape(str(evidence.get("validation_release_readiness") or ""))}</code>; checked endpoints: <code>{html.escape(str(evidence.get("api_contract_checked_endpoints") or 0))}</code>.</p>
    </div>
    {sections}
    <section><h2>Proof Points</h2><ul>{proof_points}</ul></section>
    <section>
      <h2>Demo Flow</h2>
      <table><thead><tr><th>#</th><th>Step</th><th>Show</th></tr></thead><tbody>{flow}</tbody></table>
    </section>
    <section><h2>Must Say</h2><ul>{must_say}</ul></section>
    <section><h2>Claim Boundaries</h2><ul>{avoid}</ul></section>
  </body>
</html>"""

    def brief_dir(self, brief_id: str) -> Path:
        return self.briefs_dir / safe_token(brief_id, "missing_recruiter_demo_brief", 180)

    def safe_brief_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.briefs_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
