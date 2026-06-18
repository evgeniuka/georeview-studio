from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


VISUAL_EVIDENCE_SIGNOFF_PACKET_VERSION = "visual_evidence_signoff_packet_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "visual_evidence_signoff_packet", max_len: int = 150) -> str:
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
        return {"error": "visual_evidence_signoff_packet_probe_failed", "detail": repr(exc)}


class VisualEvidenceSignoffPacketBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        visual_evidence_review_annotations: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.visual_evidence_review_annotations = visual_evidence_review_annotations
        self.expected_api_endpoints = expected_api_endpoints
        self.packets_dir = output_root / "georeview_studio_visual_evidence_signoff_packets"

    def status(self) -> dict:
        annotations = self.ready_annotations(100)
        packets = self.list_packets(100)
        ready_packets = [row for row in packets if row.get("packet_readiness") == "ready_for_visual_evidence_signoff_review"]
        latest_packet = ready_packets[0] if ready_packets else {}
        latest_annotation = annotations[0] if annotations else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "visual_evidence_signoff_packet_version": VISUAL_EVIDENCE_SIGNOFF_PACKET_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "package_visual_evidence_review_signoff",
            "output_dir": str(self.packets_dir),
            "ready_annotation_count": len(annotations),
            "latest_annotation_id": latest_annotation.get("annotation_id", ""),
            "packet_count": len(packets),
            "ready_packet_count": len(ready_packets),
            "latest_packet_id": latest_packet.get("packet_id", ""),
            "latest_signoff_status": latest_packet.get("signoff_status", ""),
            "latest_attention_count": latest_packet.get("needs_reviewer_attention", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_visual_evidence_signoff_packet" if annotations else "waiting_for_visual_evidence_annotations",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_packet(self, body: dict | None = None) -> dict:
        body = body or {}
        annotation_id = str(body.get("annotation_id") or "").strip()
        if not annotation_id:
            annotations = self.ready_annotations(20)
            annotation_id = str(annotations[0].get("annotation_id") or "") if annotations else ""
        if not annotation_id:
            return self.error("visual_evidence_signoff_packet_input_missing", "A ready visual evidence review annotation set is required.")
        annotations = self.resolve_annotations(annotation_id)
        if annotations.get("error"):
            return annotations
        if annotations.get("annotation_readiness") != "ready_for_visual_evidence_annotation_review":
            return self.error("visual_evidence_signoff_packet_not_ready", "Annotation set must be ready_for_visual_evidence_annotation_review.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        evidence = self.evidence_summary(annotations, validation, api_contract, manifest)
        stamp = utc_now()
        packet_id = f"visual_evidence_signoff_packet_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        packet_dir = self.packet_dir(packet_id)
        manifest_path = packet_dir / "visual_evidence_signoff_packet_manifest.json"
        markdown_path = packet_dir / "visual_evidence_signoff_packet.md"
        html_path = packet_dir / "visual_evidence_signoff_packet.html"
        latest_path = self.packets_dir / "latest_visual_evidence_signoff_packet.json"
        packet = {
            "ok": True,
            "visual_evidence_signoff_packet_version": VISUAL_EVIDENCE_SIGNOFF_PACKET_VERSION,
            "packet_id": packet_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "reviewer": str(body.get("reviewer") or body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Visual evidence sign-off packet for local portfolio review."),
            "app_version": self.app_version,
            "annotation_id": annotations.get("annotation_id"),
            "diff_id": annotations.get("diff_id"),
            "packet_readiness": "ready_for_visual_evidence_signoff_review",
            "signoff_status": evidence.get("signoff_status"),
            "target_count": evidence.get("target_count", 0),
            "needs_reviewer_attention": evidence.get("needs_reviewer_attention", 0),
            "accepted_no_action": evidence.get("accepted_no_action", 0),
            "evidence_summary": evidence,
            "reviewer_checklist": self.reviewer_checklist(evidence),
            "claim_boundaries": self.claim_boundaries(),
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
        write_json(manifest_path, packet)
        write_json(latest_path, packet)
        markdown_path.write_text(self.packet_markdown(packet), encoding="utf-8", newline="\n")
        html_path.write_text(self.packet_html(packet), encoding="utf-8", newline="\n")
        return {"ok": True, "packet": packet, "source_gis_modified": False, "mutates_config": False}

    def list_packets(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.packets_dir.exists():
            return rows
        manifests = sorted(
            self.packets_dir.glob("visual_evidence_signoff_packet_*/visual_evidence_signoff_packet_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("visual_evidence_signoff_packet_version") != VISUAL_EVIDENCE_SIGNOFF_PACKET_VERSION:
                continue
            rows.append({
                "packet_id": payload.get("packet_id"),
                "created_at": payload.get("created_at"),
                "packet_readiness": payload.get("packet_readiness"),
                "signoff_status": payload.get("signoff_status"),
                "annotation_id": payload.get("annotation_id"),
                "target_count": payload.get("target_count"),
                "needs_reviewer_attention": payload.get("needs_reviewer_attention"),
                "download_url": f"/api/visual-evidence-signoff-packet/packets/{payload.get('packet_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, packet_id: str) -> dict:
        path = self.packet_dir(packet_id) / "visual_evidence_signoff_packet_manifest.json"
        if not path.exists() or not self.safe_packet_path(path):
            return {"ok": False, "error": "visual_evidence_signoff_packet_not_found", "packet_id": packet_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "visual_evidence_signoff_packet_not_found", "packet_id": packet_id, "source_gis_modified": False}
        return payload

    def output_file(self, packet_id: str, output_id: str = "html") -> dict:
        detail = self.detail(packet_id)
        if detail.get("error"):
            return detail
        if output_id not in {"html", "review"}:
            return {"ok": False, "error": "visual_evidence_signoff_packet_output_not_found", "packet_id": packet_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists() or not self.safe_packet_path(path):
            return {"ok": False, "error": "visual_evidence_signoff_packet_output_not_found", "packet_id": packet_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_annotations(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.visual_evidence_review_annotations.list_annotations(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("annotation_readiness") == "ready_for_visual_evidence_annotation_review"]

    def resolve_annotations(self, annotation_id: str) -> dict:
        detail = safe_call(lambda: self.visual_evidence_review_annotations.detail(annotation_id), {})
        return detail if isinstance(detail, dict) else self.error("visual_evidence_review_annotations_not_found", "Visual evidence annotation detail failed.")

    def evidence_summary(self, annotations: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        needs_attention = int(annotations.get("needs_reviewer_attention") or 0)
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        validation_passed = validation.get("passed") is True
        api_passed = api_contract.get("passed") is True and api_checked >= self.expected_api_endpoints
        signoff_status = "signed_off_for_local_portfolio_demo"
        if needs_attention:
            signoff_status = "conditional_signoff_attention_required"
        if not validation_passed or not api_passed:
            signoff_status = "pending_validation_or_api_contract"
        return {
            "signoff_status": signoff_status,
            "annotation_id": annotations.get("annotation_id"),
            "diff_id": annotations.get("diff_id"),
            "target_count": annotations.get("target_count", 0),
            "needs_reviewer_attention": needs_attention,
            "accepted_no_action": annotations.get("accepted_no_action", 0),
            "validation_passed": validation_passed,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "validation_failed_gates": validation.get("release_readiness_failed_gates", ""),
            "api_contract_passed": api_passed,
            "api_contract_checked_endpoints": api_checked,
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
        }

    def reviewer_checklist(self, evidence: dict) -> list[dict]:
        return [
            {
                "item": "Validation passed",
                "status": "passed" if evidence.get("validation_passed") else "needs_action",
                "evidence": evidence.get("validation_release_readiness") or "Not available in inspected files",
            },
            {
                "item": "API contract passed",
                "status": "passed" if evidence.get("api_contract_passed") else "needs_action",
                "evidence": f"{evidence.get('api_contract_checked_endpoints')} checked endpoints",
            },
            {
                "item": "Visual annotation review",
                "status": "needs_review" if int(evidence.get("needs_reviewer_attention") or 0) else "passed",
                "evidence": f"{evidence.get('needs_reviewer_attention')} targets need reviewer attention",
            },
            {
                "item": "Claim boundary",
                "status": "passed",
                "evidence": "Infrastructure risk indicators only; no absolute safety claim.",
            },
            {
                "item": "Source GIS read-only",
                "status": "passed",
                "evidence": "Packet reads generated artifacts and writes only under analysis_output.",
            },
        ]

    def packet_markdown(self, packet: dict) -> str:
        evidence = packet.get("evidence_summary", {})
        lines = [
            "# Visual Evidence Sign-Off Packet",
            "",
            f"- Packet id: `{packet.get('packet_id')}`",
            f"- App version: `{packet.get('app_version')}`",
            f"- Annotation id: `{packet.get('annotation_id')}`",
            f"- Diff id: `{packet.get('diff_id')}`",
            f"- Readiness: `{packet.get('packet_readiness')}`",
            f"- Sign-off status: `{packet.get('signoff_status')}`",
            "",
            "## Evidence Summary",
            "",
            f"- Validation passed: `{evidence.get('validation_passed')}`",
            f"- Release readiness: `{evidence.get('validation_release_readiness')}`",
            f"- API contract passed: `{evidence.get('api_contract_passed')}`",
            f"- Checked endpoints: `{evidence.get('api_contract_checked_endpoints')}` / expected `{evidence.get('expected_api_endpoints')}`",
            f"- Targets: `{evidence.get('target_count')}`",
            f"- Needs reviewer attention: `{evidence.get('needs_reviewer_attention')}`",
            f"- Accepted no action: `{evidence.get('accepted_no_action')}`",
            "",
            "## Reviewer Checklist",
            "",
        ]
        for item in packet.get("reviewer_checklist", []):
            lines.append(f"- `{item.get('status')}` {item.get('item')}: {item.get('evidence')}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- This packet signs off generated local visual evidence for portfolio review only.",
            "- It is not field verification, crash prediction, or an absolute site condition claim.",
            "- Source GIS files remain read-only.",
            "",
        ])
        return "\n".join(lines)

    def packet_html(self, packet: dict) -> str:
        evidence = packet.get("evidence_summary", {})
        checklist = "".join(
            f"<tr><td>{html.escape(str(item.get('item') or ''))}</td><td><code>{html.escape(str(item.get('status') or ''))}</code></td><td>{html.escape(str(item.get('evidence') or ''))}</td></tr>"
            for item in packet.get("reviewer_checklist", [])
        )
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Visual Evidence Sign-Off Packet</title>
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
    <h1>Visual Evidence Sign-Off Packet</h1>
    <div class="summary">
      <p>Packet: <code>{html.escape(str(packet.get("packet_id") or ""))}</code>; readiness: <code>{html.escape(str(packet.get("packet_readiness") or ""))}</code>.</p>
      <p>Sign-off status: <code>{html.escape(str(packet.get("signoff_status") or ""))}</code>.</p>
      <p>Targets: <code>{html.escape(str(evidence.get("target_count") or 0))}</code>; needs reviewer attention: <code>{html.escape(str(evidence.get("needs_reviewer_attention") or 0))}</code>; checked endpoints: <code>{html.escape(str(evidence.get("api_contract_checked_endpoints") or 0))}</code>.</p>
      <p>{html.escape(self.review_wording)}</p>
    </div>
    <table>
      <thead><tr><th>Checklist item</th><th>Status</th><th>Evidence</th></tr></thead>
      <tbody>{checklist}</tbody>
    </table>
  </body>
</html>"""

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["generated visual evidence sign-off", "local portfolio readiness evidence", "reviewer checklist"],
            "not_allowed": ["field verification", "crash prediction", "absolute site condition claim"],
            "source_data_rule": "This feature reads generated evidence artifacts and writes sign-off artifacts under analysis_output only.",
        }

    def packet_dir(self, packet_id: str) -> Path:
        return self.packets_dir / safe_token(packet_id, "missing_visual_evidence_signoff_packet", 180)

    def safe_packet_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.packets_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
