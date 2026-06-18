from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


VISUAL_QA_SNAPSHOT_LEDGER_VERSION = "visual_qa_snapshot_ledger_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "visual_qa_ledger", max_len: int = 140) -> str:
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
        return {"error": "visual_qa_ledger_probe_failed", "detail": repr(exc)}


class VisualQASnapshotLedgerBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        demo_script_pack: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.demo_script_pack = demo_script_pack
        self.expected_api_endpoints = expected_api_endpoints
        self.ledgers_dir = output_root / "georeview_studio_visual_qa_ledgers"

    def status(self) -> dict:
        ledgers = self.list_ledgers(100)
        ready_ledgers = [row for row in ledgers if row.get("ledger_readiness") == "ready_for_visual_qa_tracking"]
        demo_status = safe_call(self.demo_script_pack.status, {})
        demo_rows = self.demo_pack_rows(100)
        latest_pack = self.resolve_demo_pack("")
        targets = latest_pack.get("screenshot_targets", []) if isinstance(latest_pack, dict) else []
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "visual_qa_snapshot_ledger_version": VISUAL_QA_SNAPSHOT_LEDGER_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "manual_visual_review_tracking_for_demo_screenshots",
            "output_dir": str(self.ledgers_dir),
            "demo_pack_count": len(demo_rows),
            "ready_demo_pack_count": len([row for row in demo_rows if row.get("pack_readiness") == "ready_for_demo_walkthrough"]),
            "screenshot_target_count": len(targets) or int(demo_status.get("screenshot_target_count") or 0) if isinstance(demo_status, dict) else len(targets),
            "ledger_count": len(ledgers),
            "ready_ledger_count": len(ready_ledgers),
            "latest_demo_pack_id": latest_pack.get("pack_id") if isinstance(latest_pack, dict) else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_visual_qa_tracking" if self.is_ready(demo_status, targets) else "waiting_for_demo_script_pack",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_ledger(self, body: dict | None = None) -> dict:
        body = body or {}
        pack = self.resolve_demo_pack(str(body.get("pack_id") or ""))
        if pack.get("error"):
            return pack
        if pack.get("pack_readiness") != "ready_for_demo_walkthrough":
            return self.error("visual_qa_ledger_not_ready", "The selected demo script pack must be ready_for_demo_walkthrough.")

        targets = pack.get("screenshot_targets", [])
        if len(targets) < 6:
            return self.error("visual_qa_ledger_input_missing", "Visual QA ledger requires at least six screenshot targets.")

        observations = body.get("observations") if isinstance(body.get("observations"), dict) else {}
        stamp = utc_now()
        ledger_id = f"visual_qa_ledger_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        ledger_dir = self.ledger_dir(ledger_id)
        ledger_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = ledger_dir / "visual_qa_ledger_manifest.json"
        markdown_path = ledger_dir / "visual_qa_ledger.md"
        contact_sheet_path = ledger_dir / "visual_qa_contact_sheet.html"
        latest_path = self.ledgers_dir / "latest_visual_qa_ledger.json"
        qa_items = self.qa_items(targets, observations)
        ledger = {
            "ok": True,
            "visual_qa_snapshot_ledger_version": VISUAL_QA_SNAPSHOT_LEDGER_VERSION,
            "ledger_id": ledger_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Manual visual QA ledger for demo screenshot capture and review notes."),
            "app_version": self.app_version,
            "demo_script_pack_id": pack.get("pack_id"),
            "ledger_readiness": "ready_for_visual_qa_tracking",
            "screenshot_target_count": len(targets),
            "qa_item_count": len(qa_items),
            "pending_capture_count": len([item for item in qa_items if item.get("capture_status") == "pending_manual_capture"]),
            "review_passed_count": len([item for item in qa_items if item.get("review_status") == "passed"]),
            "review_follow_up_count": len([item for item in qa_items if item.get("review_status") == "needs_follow_up"]),
            "qa_items": qa_items,
            "release_comparison": {
                "baseline_ledger_id": str(body.get("baseline_ledger_id") or ""),
                "comparison_scope": "manual visual notes across release versions",
                "automation_level": "metadata ledger only",
            },
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "markdown": str(markdown_path),
                "contact_sheet": str(contact_sheet_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, ledger)
        write_json(latest_path, ledger)
        markdown_path.write_text(self.ledger_markdown(ledger), encoding="utf-8", newline="\n")
        contact_sheet_path.write_text(self.contact_sheet_html(ledger), encoding="utf-8", newline="\n")
        return {"ok": True, "ledger": ledger, "source_gis_modified": False, "mutates_config": False}

    def list_ledgers(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.ledgers_dir.exists():
            return rows
        manifests = sorted(
            self.ledgers_dir.glob("visual_qa_ledger_*/visual_qa_ledger_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("visual_qa_snapshot_ledger_version") != VISUAL_QA_SNAPSHOT_LEDGER_VERSION:
                continue
            rows.append({
                "ledger_id": payload.get("ledger_id"),
                "created_at": payload.get("created_at"),
                "ledger_readiness": payload.get("ledger_readiness"),
                "demo_script_pack_id": payload.get("demo_script_pack_id"),
                "screenshot_target_count": payload.get("screenshot_target_count"),
                "pending_capture_count": payload.get("pending_capture_count"),
                "review_follow_up_count": payload.get("review_follow_up_count"),
                "download_url": f"/api/visual-qa-snapshot-ledger/ledgers/{payload.get('ledger_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, ledger_id: str) -> dict:
        path = self.ledger_dir(ledger_id) / "visual_qa_ledger_manifest.json"
        if not path.exists() or not self.safe_ledger_path(path):
            return {"ok": False, "error": "visual_qa_ledger_not_found", "ledger_id": ledger_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "visual_qa_ledger_not_found", "ledger_id": ledger_id, "source_gis_modified": False}
        return payload

    def output_file(self, ledger_id: str, output_id: str = "markdown") -> dict:
        detail = self.detail(ledger_id)
        if detail.get("error"):
            return detail
        if output_id not in {"markdown", "ledger"}:
            return {"ok": False, "error": "visual_qa_ledger_output_not_found", "ledger_id": ledger_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_ledger_path(path):
            return {"ok": False, "error": "visual_qa_ledger_output_not_found", "ledger_id": ledger_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def resolve_demo_pack(self, pack_id: str) -> dict:
        if pack_id:
            detail = safe_call(lambda: self.demo_script_pack.detail(pack_id), {})
            return detail if isinstance(detail, dict) else self.error("demo_script_pack_not_found", "Demo script pack detail failed.")
        rows = self.demo_pack_rows(1)
        if not rows:
            return self.error("visual_qa_ledger_input_missing", "At least one demo script pack is required.")
        detail = safe_call(lambda: self.demo_script_pack.detail(str(rows[0].get("pack_id") or "")), {})
        return detail if isinstance(detail, dict) else self.error("demo_script_pack_not_found", "Demo script pack detail failed.")

    def demo_pack_rows(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.demo_script_pack.list_packs(limit), [])
        return rows if isinstance(rows, list) else []

    def is_ready(self, demo_status: object, targets: list[dict]) -> bool:
        if not isinstance(demo_status, dict):
            return False
        target_count = len(targets) or int(demo_status.get("screenshot_target_count") or 0)
        return (
            demo_status.get("demo_script_pack_version") == "demo_script_pack_v001"
            and int(demo_status.get("script_step_count") or 0) >= 6
            and target_count >= 6
        )

    def qa_items(self, targets: list[dict], observations: dict) -> list[dict]:
        items = []
        for index, target in enumerate(targets, start=1):
            target_id = str(target.get("target_id") or f"target_{index}")
            note = observations.get(target_id) if isinstance(observations.get(target_id), dict) else {}
            selector_hint = str(target.get("selector_hint") or "")
            items.append({
                "sequence": index,
                "target_id": target_id,
                "url": target.get("url"),
                "selector_hint": selector_hint,
                "expected_text": target.get("expected_text"),
                "capture_status": str(note.get("capture_status") or "pending_manual_capture"),
                "review_status": str(note.get("review_status") or "pending_review"),
                "issue_severity": str(note.get("issue_severity") or "none"),
                "observed_text": str(note.get("observed_text") or ""),
                "visual_notes": str(note.get("visual_notes") or ""),
                "recommended_action": "call_endpoint_and_confirm_text" if selector_hint == "json" else "capture_screen_and_confirm_expected_text",
            })
        return items

    def ledger_markdown(self, ledger: dict) -> str:
        lines = [
            "# Visual QA Snapshot Ledger",
            "",
            f"- Ledger id: `{ledger.get('ledger_id')}`",
            f"- App version: `{ledger.get('app_version')}`",
            f"- Demo script pack: `{ledger.get('demo_script_pack_id')}`",
            f"- Readiness: `{ledger.get('ledger_readiness')}`",
            f"- Screenshot targets: `{ledger.get('screenshot_target_count')}`",
            f"- Pending captures: `{ledger.get('pending_capture_count')}`",
            "",
            "## Purpose",
            "",
            "This ledger tracks manual visual QA observations for portfolio demo screenshots and API smoke targets. It is evidence tracking only; it does not modify source GIS files.",
            "",
            "## QA Items",
            "",
        ]
        for item in ledger.get("qa_items", []):
            lines.extend([
                f"### {item.get('sequence')}. {item.get('target_id')}",
                "",
                f"- URL: `{item.get('url')}`",
                f"- Expected text: `{item.get('expected_text')}`",
                f"- Selector hint: `{item.get('selector_hint')}`",
                f"- Capture status: `{item.get('capture_status')}`",
                f"- Review status: `{item.get('review_status')}`",
                f"- Action: `{item.get('recommended_action')}`",
                f"- Notes: {item.get('visual_notes') or 'Pending manual review.'}",
                "",
            ])
        lines.extend([
            "## Claim Boundary",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- Visual QA confirms demo presentation and artifact readability. It is not a field survey and not a crash model.",
            "- Missing OSM tags remain data-quality evidence unless an explicit mapped value is present.",
            "",
        ])
        return "\n".join(lines)

    def contact_sheet_html(self, ledger: dict) -> str:
        cards = "\n".join(
            f"<section><h2>{item.get('sequence')}. {item.get('target_id')}</h2><p><code>{item.get('url')}</code></p><p>Expected: <strong>{item.get('expected_text')}</strong></p><p>Status: {item.get('capture_status')} / {item.get('review_status')}</p></section>"
            for item in ledger.get("qa_items", [])
        )
        return f"""<!doctype html>
<html lang=\"en\">
<head><meta charset=\"utf-8\"><title>Visual QA Snapshot Ledger</title>
<style>body{{font-family:Arial,sans-serif;margin:24px;background:#f7f7f5;color:#1d1d1b}}section{{border:1px solid #bbb;background:#fff;margin:12px 0;padding:16px;border-radius:6px}}code{{font-size:13px}}</style></head>
<body>
<h1>Visual QA Snapshot Ledger</h1>
<p>Ledger: <code>{ledger.get('ledger_id')}</code></p>
{cards}
<h2>Claim Boundary</h2>
<p>{self.review_wording}</p>
</body>
</html>"""

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["visual QA notes", "screenshot capture status", "reviewer observations", "artifact readability checks"],
            "not_allowed": ["crash prediction", "field-survey replacement", "absolute site judgement"],
            "source_data_rule": "Source GIS files remain read-only; this ledger records only generated demo review metadata.",
        }

    def ledger_dir(self, ledger_id: str) -> Path:
        return self.ledgers_dir / safe_token(ledger_id, "missing_ledger", 180)

    def safe_ledger_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.ledgers_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
