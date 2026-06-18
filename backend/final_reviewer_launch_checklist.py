from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


FINAL_REVIEWER_LAUNCH_CHECKLIST_VERSION = "final_reviewer_launch_checklist_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "final_reviewer_launch_checklist", max_len: int = 150) -> str:
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
        return {"error": "final_reviewer_launch_checklist_probe_failed", "detail": repr(exc)}


class FinalReviewerLaunchChecklistBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        visual_evidence_signoff_packet: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.visual_evidence_signoff_packet = visual_evidence_signoff_packet
        self.expected_api_endpoints = expected_api_endpoints
        self.checklists_dir = output_root / "georeview_studio_final_reviewer_launch_checklists"

    def status(self) -> dict:
        packets = self.ready_signoff_packets(100)
        checklists = self.list_checklists(100)
        ready_checklists = [row for row in checklists if row.get("checklist_readiness") == "ready_for_final_reviewer_launch"]
        latest_packet = packets[0] if packets else {}
        latest_checklist = ready_checklists[0] if ready_checklists else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "final_reviewer_launch_checklist_version": FINAL_REVIEWER_LAUNCH_CHECKLIST_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "package_final_reviewer_launch_checklist",
            "output_dir": str(self.checklists_dir),
            "ready_signoff_packet_count": len(packets),
            "latest_signoff_packet_id": latest_packet.get("packet_id", ""),
            "latest_signoff_status": latest_packet.get("signoff_status", ""),
            "checklist_count": len(checklists),
            "ready_checklist_count": len(ready_checklists),
            "latest_checklist_id": latest_checklist.get("checklist_id", ""),
            "latest_launch_status": latest_checklist.get("launch_status", ""),
            "latest_action_count": latest_checklist.get("action_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_final_reviewer_launch_checklist" if packets else "waiting_for_visual_evidence_signoff_packet",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_checklist(self, body: dict | None = None) -> dict:
        body = body or {}
        packet_id = str(body.get("packet_id") or "").strip()
        if not packet_id:
            packets = self.ready_signoff_packets(20)
            packet_id = str(packets[0].get("packet_id") or "") if packets else ""
        if not packet_id:
            return self.error("final_reviewer_launch_checklist_input_missing", "A ready visual evidence sign-off packet is required.")
        packet = self.resolve_signoff_packet(packet_id)
        if packet.get("error"):
            return packet
        if packet.get("packet_readiness") != "ready_for_visual_evidence_signoff_review":
            return self.error("final_reviewer_launch_checklist_not_ready", "Sign-off packet must be ready_for_visual_evidence_signoff_review.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        evidence = self.evidence_summary(packet, validation, api_contract, manifest)
        checklist_items = self.checklist_items(packet, evidence)
        stamp = utc_now()
        checklist_id = f"final_reviewer_launch_checklist_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        checklist_dir = self.checklist_dir(checklist_id)
        manifest_path = checklist_dir / "final_reviewer_launch_checklist_manifest.json"
        markdown_path = checklist_dir / "final_reviewer_launch_checklist.md"
        html_path = checklist_dir / "final_reviewer_launch_checklist.html"
        latest_path = self.checklists_dir / "latest_final_reviewer_launch_checklist.json"
        checklist = {
            "ok": True,
            "final_reviewer_launch_checklist_version": FINAL_REVIEWER_LAUNCH_CHECKLIST_VERSION,
            "checklist_id": checklist_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "reviewer": str(body.get("reviewer") or body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Final reviewer launch checklist for local portfolio walkthrough."),
            "app_version": self.app_version,
            "signoff_packet_id": packet.get("packet_id"),
            "annotation_id": packet.get("annotation_id"),
            "checklist_readiness": "ready_for_final_reviewer_launch",
            "launch_status": evidence.get("launch_status"),
            "action_count": len(checklist_items),
            "must_say_count": len(self.must_say_lines(evidence)),
            "download_targets": self.download_targets(packet, evidence),
            "launch_steps": checklist_items,
            "must_say_lines": self.must_say_lines(evidence),
            "evidence_summary": evidence,
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
        write_json(manifest_path, checklist)
        write_json(latest_path, checklist)
        markdown_path.write_text(self.checklist_markdown(checklist), encoding="utf-8", newline="\n")
        html_path.write_text(self.checklist_html(checklist), encoding="utf-8", newline="\n")
        return {"ok": True, "checklist": checklist, "source_gis_modified": False, "mutates_config": False}

    def list_checklists(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.checklists_dir.exists():
            return rows
        manifests = sorted(
            self.checklists_dir.glob("final_reviewer_launch_checklist_*/final_reviewer_launch_checklist_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("final_reviewer_launch_checklist_version") != FINAL_REVIEWER_LAUNCH_CHECKLIST_VERSION:
                continue
            rows.append({
                "checklist_id": payload.get("checklist_id"),
                "created_at": payload.get("created_at"),
                "checklist_readiness": payload.get("checklist_readiness"),
                "launch_status": payload.get("launch_status"),
                "signoff_packet_id": payload.get("signoff_packet_id"),
                "action_count": payload.get("action_count"),
                "must_say_count": payload.get("must_say_count"),
                "download_url": f"/api/final-reviewer-launch-checklist/checklists/{payload.get('checklist_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, checklist_id: str) -> dict:
        path = self.checklist_dir(checklist_id) / "final_reviewer_launch_checklist_manifest.json"
        if not path.exists() or not self.safe_checklist_path(path):
            return {"ok": False, "error": "final_reviewer_launch_checklist_not_found", "checklist_id": checklist_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "final_reviewer_launch_checklist_not_found", "checklist_id": checklist_id, "source_gis_modified": False}
        return payload

    def output_file(self, checklist_id: str, output_id: str = "html") -> dict:
        detail = self.detail(checklist_id)
        if detail.get("error"):
            return detail
        if output_id not in {"html", "review"}:
            return {"ok": False, "error": "final_reviewer_launch_checklist_output_not_found", "checklist_id": checklist_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists() or not self.safe_checklist_path(path):
            return {"ok": False, "error": "final_reviewer_launch_checklist_output_not_found", "checklist_id": checklist_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_signoff_packets(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.visual_evidence_signoff_packet.list_packets(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("packet_readiness") == "ready_for_visual_evidence_signoff_review"]

    def resolve_signoff_packet(self, packet_id: str) -> dict:
        detail = safe_call(lambda: self.visual_evidence_signoff_packet.detail(packet_id), {})
        return detail if isinstance(detail, dict) else self.error("visual_evidence_signoff_packet_not_found", "Visual evidence sign-off packet detail failed.")

    def evidence_summary(self, packet: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        validation_passed = validation.get("passed") is True
        api_passed = api_contract.get("passed") is True and api_checked >= self.expected_api_endpoints
        signoff_status = str(packet.get("signoff_status") or "")
        launch_status = "ready_for_local_portfolio_walkthrough"
        if signoff_status == "conditional_signoff_attention_required":
            launch_status = "ready_with_reviewer_attention_items"
        if not validation_passed or not api_passed:
            launch_status = "pending_validation_or_api_contract"
        return {
            "launch_status": launch_status,
            "signoff_status": signoff_status,
            "signoff_packet_id": packet.get("packet_id"),
            "target_count": packet.get("target_count", 0),
            "needs_reviewer_attention": packet.get("needs_reviewer_attention", 0),
            "validation_passed": validation_passed,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "validation_failed_gates": validation.get("release_readiness_failed_gates", ""),
            "api_contract_passed": api_passed,
            "api_contract_checked_endpoints": api_checked,
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
        }

    def checklist_items(self, packet: dict, evidence: dict) -> list[dict]:
        local_url = evidence.get("local_url") or "http://127.0.0.1:8834"
        return [
            {"order": 1, "action": "Open local app", "target": local_url, "proof": "Health endpoint and dashboard load locally."},
            {"order": 2, "action": "Show Kfar Saba MVP dashboard", "target": "Safe Access route-aware workspace", "proof": "391 pedestrian generators and route-aware review scores are available."},
            {"order": 3, "action": "Show infrastructure indicators only", "target": "Risk flags and data-quality flags", "proof": self.review_wording},
            {"order": 4, "action": "Download final sign-off packet", "target": str(packet.get("packet_id") or ""), "proof": "Visual evidence sign-off packet HTML is available."},
            {"order": 5, "action": "Call out reviewer attention items", "target": str(evidence.get("needs_reviewer_attention") or 0), "proof": "Visual targets needing review are explicit and not hidden."},
            {"order": 6, "action": "Show API and validation evidence", "target": f"{evidence.get('api_contract_checked_endpoints')} endpoints", "proof": evidence.get("validation_release_readiness") or "Not available in inspected files"},
            {"order": 7, "action": "Explain limitations", "target": "OSM missing tags and field-review boundary", "proof": "Missing tags are data quality flags, not proof of absence."},
            {"order": 8, "action": "Close with next engineering step", "target": "Productionization path", "proof": "PostGIS/FastAPI/MapLibre path is documented separately."},
        ]

    def must_say_lines(self, evidence: dict) -> list[str]:
        return [
            self.review_wording,
            "This is an infrastructure risk indicator and field-review prioritization tool, not a crash prediction model.",
            "Missing OSM tags are treated as data-quality flags, not proof that infrastructure is absent.",
            f"Current release readiness: {evidence.get('validation_release_readiness') or 'Not available in inspected files'}.",
            f"API contract coverage checked: {evidence.get('api_contract_checked_endpoints')} endpoints.",
        ]

    def download_targets(self, packet: dict, evidence: dict) -> list[dict]:
        return [
            {"label": "Dashboard", "url": evidence.get("local_url") or "http://127.0.0.1:8834", "type": "local_app"},
            {"label": "Sign-off packet", "url": f"/api/visual-evidence-signoff-packet/packets/{packet.get('packet_id')}/download", "type": "html"},
            {"label": "Launch checklist", "url": "self", "type": "html"},
            {"label": "Validation summary", "url": str(self.project_dir / "validation_summary.json"), "type": "json"},
            {"label": "API contract summary", "url": str(self.project_dir / "api_contract_summary.json"), "type": "json"},
        ]

    def checklist_markdown(self, checklist: dict) -> str:
        evidence = checklist.get("evidence_summary", {})
        lines = [
            "# Final Reviewer Launch Checklist",
            "",
            f"- Checklist id: `{checklist.get('checklist_id')}`",
            f"- App version: `{checklist.get('app_version')}`",
            f"- Sign-off packet: `{checklist.get('signoff_packet_id')}`",
            f"- Readiness: `{checklist.get('checklist_readiness')}`",
            f"- Launch status: `{checklist.get('launch_status')}`",
            "",
            "## Launch Steps",
            "",
        ]
        for item in checklist.get("launch_steps", []):
            lines.append(f"{item.get('order')}. {item.get('action')} - {item.get('target')} ({item.get('proof')})")
        lines.extend(["", "## Must Say", ""])
        for line in checklist.get("must_say_lines", []):
            lines.append(f"- {line}")
        lines.extend([
            "",
            "## Evidence",
            "",
            f"- Release readiness: `{evidence.get('validation_release_readiness')}`",
            f"- Failed gates: `{evidence.get('validation_failed_gates')}`",
            f"- API endpoints: `{evidence.get('api_contract_checked_endpoints')}` / expected `{evidence.get('expected_api_endpoints')}`",
            f"- Visual targets needing review: `{evidence.get('needs_reviewer_attention')}`",
            "- Source GIS files remain read-only.",
            "",
        ])
        return "\n".join(lines)

    def checklist_html(self, checklist: dict) -> str:
        steps = "".join(
            f"<tr><td>{item.get('order')}</td><td>{html.escape(str(item.get('action') or ''))}</td><td>{html.escape(str(item.get('target') or ''))}</td><td>{html.escape(str(item.get('proof') or ''))}</td></tr>"
            for item in checklist.get("launch_steps", [])
        )
        must_say = "".join(f"<li>{html.escape(line)}</li>" for line in checklist.get("must_say_lines", []))
        evidence = checklist.get("evidence_summary", {})
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Final Reviewer Launch Checklist</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7f4; color: #1f2933; }}
      .summary {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; margin-bottom: 16px; }}
      table {{ width: 100%; border-collapse: collapse; background: white; }}
      th, td {{ border: 1px solid #d7d8d2; padding: 8px; vertical-align: top; }}
      th {{ background: #eef0ea; text-align: left; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Final Reviewer Launch Checklist</h1>
    <div class="summary">
      <p>Checklist: <code>{html.escape(str(checklist.get("checklist_id") or ""))}</code>; readiness: <code>{html.escape(str(checklist.get("checklist_readiness") or ""))}</code>.</p>
      <p>Launch status: <code>{html.escape(str(checklist.get("launch_status") or ""))}</code>; sign-off packet: <code>{html.escape(str(checklist.get("signoff_packet_id") or ""))}</code>.</p>
      <p>Release readiness: <code>{html.escape(str(evidence.get("validation_release_readiness") or ""))}</code>; checked endpoints: <code>{html.escape(str(evidence.get("api_contract_checked_endpoints") or 0))}</code>.</p>
    </div>
    <h2>Launch Steps</h2>
    <table>
      <thead><tr><th>#</th><th>Action</th><th>Target</th><th>Proof</th></tr></thead>
      <tbody>{steps}</tbody>
    </table>
    <h2>Must Say</h2>
    <ul>{must_say}</ul>
  </body>
</html>"""

    def checklist_dir(self, checklist_id: str) -> Path:
        return self.checklists_dir / safe_token(checklist_id, "missing_final_reviewer_launch_checklist", 180)

    def safe_checklist_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.checklists_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
