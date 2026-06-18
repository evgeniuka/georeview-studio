from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


DEMO_REVIEW_PLAYBOOK_VERSION = "demo_review_playbook_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "demo_review_playbook", max_len: int = 150) -> str:
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
        return {"error": "demo_review_playbook_probe_failed", "detail": repr(exc)}


class DemoReviewPlaybookBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        public_portfolio_package: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.public_portfolio_package = public_portfolio_package
        self.expected_api_endpoints = expected_api_endpoints
        self.playbooks_dir = output_root / "georeview_studio_demo_review_playbooks"

    def status(self) -> dict:
        packages = self.ready_public_packages(100)
        playbooks = self.list_playbooks(100)
        ready_playbooks = [row for row in playbooks if row.get("playbook_readiness") == "ready_for_demo_review_playbook"]
        latest_package = packages[0] if packages else {}
        latest_playbook = ready_playbooks[0] if ready_playbooks else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "demo_review_playbook_version": DEMO_REVIEW_PLAYBOOK_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "turn_public_package_into_demo_review_flow",
            "output_dir": str(self.playbooks_dir),
            "ready_public_portfolio_package_count": len(packages),
            "latest_public_portfolio_package_id": latest_package.get("package_id", ""),
            "latest_public_portfolio_package_status": latest_package.get("package_status", ""),
            "playbook_count": len(playbooks),
            "ready_playbook_count": len(ready_playbooks),
            "latest_playbook_id": latest_playbook.get("playbook_id", ""),
            "latest_playbook_status": latest_playbook.get("playbook_status", ""),
            "latest_checklist_item_count": latest_playbook.get("sharing_checklist_item_count", 0),
            "latest_demo_agenda_item_count": latest_playbook.get("demo_agenda_item_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_demo_review_playbook" if packages else "waiting_for_public_portfolio_package",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_playbook(self, body: dict | None = None) -> dict:
        body = body or {}
        package_id = str(body.get("package_id") or "").strip()
        if not package_id:
            packages = self.ready_public_packages(20)
            package_id = str(packages[0].get("package_id") or "") if packages else ""
        if not package_id:
            return self.error("demo_review_playbook_input_missing", "A ready public portfolio package is required.")
        package = self.resolve_public_package(package_id)
        if package.get("error"):
            return package
        if package.get("package_readiness") != "ready_for_public_portfolio_package":
            return self.error("demo_review_playbook_not_ready", "Public portfolio package must be ready_for_public_portfolio_package.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        evidence = self.evidence_summary(package, validation, api_contract, manifest)
        agenda = self.demo_agenda(package, evidence)
        checklist = self.sharing_checklist(package, evidence)
        review_questions = self.review_questions(package, evidence)
        reviewer_notes = self.reviewer_notes(package, evidence)
        stamp = utc_now()
        playbook_id = f"demo_review_playbook_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        playbook_dir = self.playbook_dir(playbook_id)
        manifest_path = playbook_dir / "demo_review_playbook_manifest.json"
        playbook_path = playbook_dir / "demo_review_playbook.md"
        checklist_path = playbook_dir / "final_sharing_checklist.md"
        html_path = playbook_dir / "demo_review_playbook.html"
        latest_path = self.playbooks_dir / "latest_demo_review_playbook.json"
        playbook = {
            "ok": True,
            "demo_review_playbook_version": DEMO_REVIEW_PLAYBOOK_VERSION,
            "playbook_id": playbook_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "portfolio_reviewer"),
            "notes": str(body.get("notes") or "Demo review playbook and final sharing checklist for GeoReview Studio."),
            "app_version": self.app_version,
            "public_portfolio_package_id": package.get("package_id"),
            "playbook_readiness": "ready_for_demo_review_playbook",
            "playbook_status": evidence.get("playbook_status"),
            "headline": "GeoReview Studio demo review playbook",
            "demo_agenda_item_count": len(agenda),
            "sharing_checklist_item_count": len(checklist),
            "review_question_count": len(review_questions),
            "reviewer_note_count": len(reviewer_notes),
            "demo_agenda": agenda,
            "sharing_checklist": checklist,
            "review_questions": review_questions,
            "reviewer_notes": reviewer_notes,
            "claim_boundaries": self.claim_boundaries(),
            "evidence_summary": evidence,
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "playbook": str(playbook_path),
                "checklist": str(checklist_path),
                "html": str(html_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, playbook)
        write_json(latest_path, playbook)
        playbook_path.write_text(self.playbook_markdown(playbook), encoding="utf-8", newline="\n")
        checklist_path.write_text(self.checklist_markdown(playbook), encoding="utf-8", newline="\n")
        html_path.write_text(self.playbook_html(playbook), encoding="utf-8", newline="\n")
        return {"ok": True, "playbook": playbook, "source_gis_modified": False, "mutates_config": False}

    def list_playbooks(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.playbooks_dir.exists():
            return rows
        manifests = sorted(
            self.playbooks_dir.glob("demo_review_playbook_*/demo_review_playbook_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("demo_review_playbook_version") != DEMO_REVIEW_PLAYBOOK_VERSION:
                continue
            rows.append({
                "playbook_id": payload.get("playbook_id"),
                "created_at": payload.get("created_at"),
                "playbook_readiness": payload.get("playbook_readiness"),
                "playbook_status": payload.get("playbook_status"),
                "public_portfolio_package_id": payload.get("public_portfolio_package_id"),
                "demo_agenda_item_count": payload.get("demo_agenda_item_count"),
                "sharing_checklist_item_count": payload.get("sharing_checklist_item_count"),
                "review_question_count": payload.get("review_question_count"),
                "download_url": f"/api/demo-review-playbook/playbooks/{payload.get('playbook_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, playbook_id: str) -> dict:
        path = self.playbook_dir(playbook_id) / "demo_review_playbook_manifest.json"
        if not path.exists() or not self.safe_playbook_path(path):
            return {"ok": False, "error": "demo_review_playbook_not_found", "playbook_id": playbook_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "demo_review_playbook_not_found", "playbook_id": playbook_id, "source_gis_modified": False}
        return payload

    def output_file(self, playbook_id: str, output_id: str = "html") -> dict:
        detail = self.detail(playbook_id)
        if detail.get("error"):
            return detail
        if output_id not in {"html", "playbook", "checklist"}:
            return {"ok": False, "error": "demo_review_playbook_output_not_found", "playbook_id": playbook_id, "output_id": output_id}
        key = "html" if output_id == "html" else output_id
        path = Path(str(detail.get("files", {}).get(key) or ""))
        if not path.exists() or not self.safe_playbook_path(path):
            return {"ok": False, "error": "demo_review_playbook_output_not_found", "playbook_id": playbook_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_public_packages(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.public_portfolio_package.list_packages(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("package_readiness") == "ready_for_public_portfolio_package"]

    def resolve_public_package(self, package_id: str) -> dict:
        detail = safe_call(lambda: self.public_portfolio_package.detail(package_id), {})
        return detail if isinstance(detail, dict) else self.error("public_portfolio_package_not_found", "Public portfolio package detail failed.")

    def evidence_summary(self, package: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        validation_passed = validation.get("passed") is True
        api_passed = api_contract.get("passed") is True and api_checked >= self.expected_api_endpoints
        package_status = str(package.get("package_status") or "")
        playbook_status = "ready_for_final_sharing_review"
        if package_status == "ready_with_reviewer_attention_items":
            playbook_status = "ready_with_reviewer_attention_items"
        if not validation_passed or not api_passed:
            playbook_status = "pending_validation_or_api_contract"
        return {
            "playbook_status": playbook_status,
            "package_status": package_status,
            "public_portfolio_package_id": package.get("package_id"),
            "validation_passed": validation_passed,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "validation_failed_gates": validation.get("release_readiness_failed_gates", ""),
            "api_contract_passed": api_passed,
            "api_contract_checked_endpoints": api_checked,
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
            "current_release_focus": manifest.get("current_release_focus") if isinstance(manifest, dict) else "",
            "readme_section_count": package.get("readme_section_count", 0),
            "interview_step_count": package.get("interview_step_count", 0),
            "generators": validation.get("generators", 0),
            "crossings": validation.get("crossings", 0),
            "route_aware_rows": validation.get("route_aware_rows", 0),
            "review_wording": self.review_wording,
        }

    def demo_agenda(self, package: dict, evidence: dict) -> list[dict]:
        return [
            {"order": 1, "title": "Open with the product position", "action": "Present GeoReview Studio as a local-first GIS review workbench with Safe Access Israel as the first concrete profile.", "evidence": package.get("public_one_liner", "")},
            {"order": 2, "title": "Show the source-data boundary", "action": "Explain that source GIS files are read-only and generated artifacts live under analysis_output.", "evidence": "source_gis_modified=false is carried through manifests and gates."},
            {"order": 3, "title": "Show the Kfar Saba analytics", "action": "Use the dashboard to show pedestrian generators, crossings, major-road proximity, route-aware metrics and top review candidates.", "evidence": f"{evidence.get('generators')} generators and {evidence.get('crossings')} crossings are referenced by validation evidence."},
            {"order": 4, "title": "Explain the scoring boundary", "action": "Separate infrastructure risk indicators from missing-tag data-quality flags.", "evidence": self.review_wording},
            {"order": 5, "title": "Show reusability", "action": "Open product architecture and profile dashboard panels to show Safe Access, Transit, Park and OSM tag quality profile contracts.", "evidence": "The app is framed as a reusable GIS review studio, not a single notebook."},
            {"order": 6, "title": "Show release evidence", "action": "Open release readiness, validation summary, API contract and public portfolio package artifacts.", "evidence": f"Current API evidence checks {evidence.get('api_contract_checked_endpoints')} endpoints."},
            {"order": 7, "title": "Close with the roadmap", "action": "Explain why PostGIS, guarded uploads, reviewer sessions and MapLibre frontend are logical production extensions.", "evidence": "Roadmap keeps upload and config mutation behind explicit review gates."},
        ]

    def sharing_checklist(self, package: dict, evidence: dict) -> list[dict]:
        return [
            {"item": "Run validation", "required": True, "status": "passed" if evidence.get("validation_passed") else "needs_update", "check": "validation_summary.json should report passed=true."},
            {"item": "Run API contract", "required": True, "status": "passed" if evidence.get("api_contract_passed") else "needs_update", "check": f"api_contract_summary.json should cover at least {self.expected_api_endpoints} endpoints."},
            {"item": "Open public package HTML", "required": True, "status": "ready", "check": "Confirm the public package explains value, architecture, analytics and claim boundaries."},
            {"item": "Open demo playbook HTML", "required": True, "status": "ready", "check": "Confirm the agenda is suitable for a 7-10 minute portfolio walkthrough."},
            {"item": "Check claim boundary wording", "required": True, "status": "ready", "check": self.review_wording},
            {"item": "Check source-data policy", "required": True, "status": "ready", "check": "No source GIS file should be moved, renamed, deleted or overwritten."},
            {"item": "Prepare top evidence artifacts", "required": True, "status": "ready", "check": "Keep README, interview walkthrough, validation summary and API summary ready to open."},
            {"item": "Prepare reviewer questions", "required": True, "status": "ready", "check": "Be ready to explain OSM tag limitations and why missing tags are not scored as real-world absence."},
            {"item": "Choose next development step", "required": False, "status": "ready", "check": "v074 should create a GitHub-ready publication bundle and README export."},
        ]

    def review_questions(self, package: dict, evidence: dict) -> list[dict]:
        return [
            {"question": "What is the user value?", "answer": "A reviewer can prioritize locations for on-site infrastructure review using transparent mapped indicators and uncertainty flags."},
            {"question": "Why is this serious portfolio work?", "answer": "It combines GIS source inspection, CRS-aware spatial analysis, reusable profile contracts, backend APIs, UI panels and release evidence."},
            {"question": "What can be reused for other cities?", "answer": "The source onboarding, profile mapper, controlled execution, profile dashboard and evidence package layers are city-agnostic."},
            {"question": "What are the limits of OSM evidence?", "answer": "Missing tags are data-quality flags. The app does not treat absent tags as proof of real-world infrastructure absence."},
            {"question": "How would you scale it?", "answer": "Move from local CSV/GPKG artifacts to PostGIS, add spatial indexes, guarded uploads, jobs and reviewer workflows."},
            {"question": "What should be validated manually?", "answer": "Top-scoring candidates, crossing context, actual sidewalks, lighting, signal details and pilot boundary assumptions should be reviewed on-site."},
        ]

    def reviewer_notes(self, package: dict, evidence: dict) -> list[str]:
        return [
            "Lead with the universal GIS workbench idea, then show Safe Access Israel as the implemented proof.",
            "Use the approved review wording exactly when discussing row-level outputs.",
            "Treat Kfar Saba as an OSM/Geofabrik pilot polygon, not an official municipal boundary.",
            "Say that the score is a transparent prioritization aid for field review.",
            "Do not overstate missing sidewalk, lighting or traffic-calming tags.",
        ]

    def claim_boundaries(self) -> list[str]:
        return [
            self.review_wording,
            "This is an infrastructure indicator and field-review prioritization tool, not a crash prediction model.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "Scores are transparent prioritization aids and should be calibrated through field review.",
        ]

    def playbook_markdown(self, playbook: dict) -> str:
        lines = [
            "# Demo Review Playbook",
            "",
            f"- Playbook id: `{playbook.get('playbook_id')}`",
            f"- App version: `{playbook.get('app_version')}`",
            f"- Readiness: `{playbook.get('playbook_readiness')}`",
            f"- Status: `{playbook.get('playbook_status')}`",
            f"- Public package: `{playbook.get('public_portfolio_package_id')}`",
            "",
            "## Demo Agenda",
            "",
        ]
        for item in playbook.get("demo_agenda", []):
            lines.append(f"{item.get('order')}. **{item.get('title')}**")
            lines.append(f"   - Action: {item.get('action')}")
            lines.append(f"   - Evidence: {item.get('evidence')}")
            lines.append("")
        lines.extend(["## Likely Review Questions", ""])
        for item in playbook.get("review_questions", []):
            lines.append(f"- **{item.get('question')}** {item.get('answer')}")
        lines.extend(["", "## Reviewer Notes", ""])
        for note in playbook.get("reviewer_notes", []):
            lines.append(f"- {note}")
        lines.extend(["", "## Claim Boundaries", ""])
        for line in playbook.get("claim_boundaries", []):
            lines.append(f"- {line}")
        lines.extend(["", "Source GIS files remain read-only.", ""])
        return "\n".join(lines)

    def checklist_markdown(self, playbook: dict) -> str:
        lines = [
            "# Final Sharing Checklist",
            "",
            f"Playbook id: `{playbook.get('playbook_id')}`",
            "",
            "| Item | Required | Status | Check |",
            "|---|---:|---|---|",
        ]
        for item in playbook.get("sharing_checklist", []):
            lines.append(f"| {item.get('item')} | {str(item.get('required')).lower()} | {item.get('status')} | {item.get('check')} |")
        lines.extend(["", "## Approved Review Wording", "", f"`{self.review_wording}`", ""])
        return "\n".join(lines)

    def playbook_html(self, playbook: dict) -> str:
        agenda = "".join(
            f"<tr><td>{item.get('order')}</td><td>{html.escape(str(item.get('title') or ''))}</td><td>{html.escape(str(item.get('action') or ''))}</td><td>{html.escape(str(item.get('evidence') or ''))}</td></tr>"
            for item in playbook.get("demo_agenda", [])
        )
        checklist = "".join(
            f"<tr><td>{html.escape(str(item.get('item') or ''))}</td><td>{html.escape(str(item.get('required') or ''))}</td><td>{html.escape(str(item.get('status') or ''))}</td><td>{html.escape(str(item.get('check') or ''))}</td></tr>"
            for item in playbook.get("sharing_checklist", [])
        )
        questions = "".join(
            f"<li><strong>{html.escape(str(item.get('question') or ''))}</strong> {html.escape(str(item.get('answer') or ''))}</li>"
            for item in playbook.get("review_questions", [])
        )
        notes = "".join(f"<li>{html.escape(str(note))}</li>" for note in playbook.get("reviewer_notes", []))
        boundaries = "".join(f"<li>{html.escape(line)}</li>" for line in playbook.get("claim_boundaries", []))
        evidence = playbook.get("evidence_summary", {})
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Demo Review Playbook</title>
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
    <h1>Demo Review Playbook</h1>
    <div class="summary">
      <p><strong>{html.escape(str(playbook.get("headline") or ""))}</strong></p>
      <p>Playbook: <code>{html.escape(str(playbook.get("playbook_id") or ""))}</code>; status: <code>{html.escape(str(playbook.get("playbook_status") or ""))}</code>.</p>
      <p>Public package: <code>{html.escape(str(playbook.get("public_portfolio_package_id") or ""))}</code>; release readiness: <code>{html.escape(str(evidence.get("validation_release_readiness") or ""))}</code>; checked endpoints: <code>{html.escape(str(evidence.get("api_contract_checked_endpoints") or 0))}</code>.</p>
    </div>
    <section>
      <h2>Demo Agenda</h2>
      <table><thead><tr><th>#</th><th>Title</th><th>Action</th><th>Evidence</th></tr></thead><tbody>{agenda}</tbody></table>
    </section>
    <section>
      <h2>Final Sharing Checklist</h2>
      <table><thead><tr><th>Item</th><th>Required</th><th>Status</th><th>Check</th></tr></thead><tbody>{checklist}</tbody></table>
    </section>
    <section><h2>Likely Review Questions</h2><ul>{questions}</ul></section>
    <section><h2>Reviewer Notes</h2><ul>{notes}</ul></section>
    <section><h2>Claim Boundaries</h2><ul>{boundaries}</ul></section>
  </body>
</html>"""

    def playbook_dir(self, playbook_id: str) -> Path:
        return self.playbooks_dir / safe_token(playbook_id, "missing_demo_review_playbook", 180)

    def safe_playbook_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.playbooks_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
