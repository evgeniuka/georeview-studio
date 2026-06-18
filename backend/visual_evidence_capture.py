from __future__ import annotations

import base64
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen


VISUAL_EVIDENCE_CAPTURE_VERSION = "visual_evidence_capture_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "visual_evidence_capture", max_len: int = 150) -> str:
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
        return {"error": "visual_evidence_capture_probe_failed", "detail": repr(exc)}


class VisualEvidenceCaptureBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        visual_qa_ledger: object,
        demo_artifact_completeness: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.visual_qa_ledger = visual_qa_ledger
        self.demo_artifact_completeness = demo_artifact_completeness
        self.expected_api_endpoints = expected_api_endpoints
        self.captures_dir = output_root / "georeview_studio_visual_evidence_captures"

    def status(self) -> dict:
        captures = self.list_captures(100)
        ready = [row for row in captures if row.get("capture_readiness") == "ready_for_visual_evidence_review"]
        latest_ledger = self.resolve_ledger("")
        targets = latest_ledger.get("qa_items", []) if isinstance(latest_ledger, dict) else []
        browser = self.browser_executable()
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "visual_evidence_capture_version": VISUAL_EVIDENCE_CAPTURE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "headless_browser_capture_for_visual_qa_targets",
            "output_dir": str(self.captures_dir),
            "browser_path": str(browser) if browser else "",
            "browser_available": bool(browser),
            "latest_ledger_id": latest_ledger.get("ledger_id") if isinstance(latest_ledger, dict) else "",
            "target_count": len(targets),
            "capture_count": len(captures),
            "ready_capture_count": len(ready),
            "latest_capture_id": ready[0].get("capture_id") if ready else "",
            "latest_captured_count": ready[0].get("captured_count", 0) if ready else 0,
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_visual_evidence_capture" if browser and len(targets) >= 6 else "waiting_for_browser_or_visual_qa_targets",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_capture(self, body: dict | None = None) -> dict:
        body = body or {}
        browser = self.browser_executable()
        if not browser:
            return self.error("visual_evidence_capture_not_ready", "Chrome or Edge headless executable was not found.")
        ledger = self.resolve_ledger(str(body.get("ledger_id") or ""))
        if ledger.get("error"):
            return ledger
        if ledger.get("ledger_readiness") != "ready_for_visual_qa_tracking":
            return self.error("visual_evidence_capture_not_ready", "Selected Visual QA ledger must be ready_for_visual_qa_tracking.")
        targets = ledger.get("qa_items", [])
        if len(targets) < 6:
            return self.error("visual_evidence_capture_input_missing", "Visual evidence capture requires at least six Visual QA targets.")

        stamp = utc_now()
        capture_id = f"visual_evidence_capture_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        capture_dir = self.capture_dir(capture_id)
        screenshot_dir = capture_dir / "screenshots"
        profile_dir = capture_dir / "browser_profile"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        profile_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = capture_dir / "visual_evidence_capture_manifest.json"
        contact_sheet_path = capture_dir / "visual_evidence_contact_sheet.html"
        markdown_path = capture_dir / "visual_evidence_capture.md"
        latest_path = self.captures_dir / "latest_visual_evidence_capture.json"
        base_url = str(body.get("base_url") or "").strip()
        window_size = str(body.get("window_size") or "1365,900")
        rows = []
        for index, target in enumerate(targets, start=1):
            rows.append(self.capture_target(browser, profile_dir, screenshot_dir, index, target, base_url, window_size))
        captured = [row for row in rows if row.get("capture_status") == "captured"]
        expected_matches = [row for row in rows if row.get("expected_text_found") is True]
        failed = [row for row in rows if row.get("capture_status") != "captured"]
        readiness = "ready_for_visual_evidence_review" if len(captured) == len(rows) and len(rows) >= 6 else "needs_visual_capture_follow_up"
        capture = {
            "ok": True,
            "visual_evidence_capture_version": VISUAL_EVIDENCE_CAPTURE_VERSION,
            "capture_id": capture_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Headless browser visual evidence capture for Visual QA targets."),
            "app_version": self.app_version,
            "ledger_id": ledger.get("ledger_id"),
            "capture_readiness": readiness,
            "browser_path": str(browser),
            "base_url_override": base_url,
            "target_count": len(rows),
            "captured_count": len(captured),
            "failed_count": len(failed),
            "expected_text_match_count": len(expected_matches),
            "capture_rows": rows,
            "recommended_actions": self.recommended_actions(rows),
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "contact_sheet": str(contact_sheet_path),
                "markdown": str(markdown_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, capture)
        write_json(latest_path, capture)
        contact_sheet_path.write_text(self.contact_sheet_html(capture), encoding="utf-8", newline="\n")
        markdown_path.write_text(self.capture_markdown(capture), encoding="utf-8", newline="\n")
        return {"ok": True, "capture": capture, "source_gis_modified": False, "mutates_config": False}

    def list_captures(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.captures_dir.exists():
            return rows
        manifests = sorted(
            self.captures_dir.glob("visual_evidence_capture_*/visual_evidence_capture_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("visual_evidence_capture_version") != VISUAL_EVIDENCE_CAPTURE_VERSION:
                continue
            rows.append({
                "capture_id": payload.get("capture_id"),
                "created_at": payload.get("created_at"),
                "capture_readiness": payload.get("capture_readiness"),
                "ledger_id": payload.get("ledger_id"),
                "target_count": payload.get("target_count"),
                "captured_count": payload.get("captured_count"),
                "failed_count": payload.get("failed_count"),
                "download_url": f"/api/visual-evidence-capture/captures/{payload.get('capture_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, capture_id: str) -> dict:
        path = self.capture_dir(capture_id) / "visual_evidence_capture_manifest.json"
        if not path.exists() or not self.safe_capture_path(path):
            return {"ok": False, "error": "visual_evidence_capture_not_found", "capture_id": capture_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "visual_evidence_capture_not_found", "capture_id": capture_id, "source_gis_modified": False}
        return payload

    def output_file(self, capture_id: str, output_id: str = "contact_sheet") -> dict:
        detail = self.detail(capture_id)
        if detail.get("error"):
            return detail
        if output_id not in {"contact_sheet", "html"}:
            return {"ok": False, "error": "visual_evidence_capture_output_not_found", "capture_id": capture_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("contact_sheet") or ""))
        if not path.exists() or not self.safe_capture_path(path):
            return {"ok": False, "error": "visual_evidence_capture_output_not_found", "capture_id": capture_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def capture_target(self, browser: Path, profile_dir: Path, screenshot_dir: Path, index: int, target: dict, base_url: str, window_size: str) -> dict:
        target_id = safe_token(target.get("target_id"), f"target_{index}", 90)
        original_url = str(target.get("url") or "")
        capture_url = self.rewrite_url(original_url, base_url)
        screenshot_path = screenshot_dir / f"{index:02d}_{target_id}.png"
        user_data_dir = profile_dir / target_id
        user_data_dir.mkdir(parents=True, exist_ok=True)
        expected_text = str(target.get("expected_text") or "")
        text_probe = self.text_probe(capture_url, expected_text)
        command = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--disable-background-networking",
            f"--user-data-dir={user_data_dir}",
            f"--window-size={window_size}",
            f"--screenshot={screenshot_path}",
            capture_url,
        ]
        status = "failed"
        reason = ""
        return_code = None
        stderr_tail = ""
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=75)
            return_code = completed.returncode
            stderr_tail = (completed.stderr or completed.stdout or "")[-500:]
        except subprocess.TimeoutExpired as exc:
            reason = f"browser_timeout_after_{exc.timeout}s"
        except OSError as exc:
            reason = f"browser_launch_failed:{exc!r}"
        if not reason:
            self.wait_for_file(screenshot_path, min_size=1000, timeout_seconds=5)
            if screenshot_path.exists() and screenshot_path.stat().st_size > 1000:
                status = "captured"
            else:
                reason = f"missing_or_small_screenshot:return_code={return_code}"
        return {
            "target_id": target_id,
            "original_url": original_url,
            "capture_url": capture_url,
            "selector_hint": target.get("selector_hint"),
            "expected_text": expected_text,
            "expected_text_found": text_probe.get("expected_text_found"),
            "text_probe_status": text_probe.get("status"),
            "capture_status": status,
            "failure_reason": reason,
            "browser_return_code": return_code,
            "browser_output_tail": stderr_tail,
            "screenshot_path": str(screenshot_path),
            "screenshot_size_bytes": screenshot_path.stat().st_size if screenshot_path.exists() else 0,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def text_probe(self, url: str, expected_text: str) -> dict:
        if not expected_text:
            return {"status": "not_required", "expected_text_found": None}
        try:
            with urlopen(url, timeout=30) as response:
                body = response.read(300000).decode("utf-8", errors="ignore")
            return {"status": "probed", "expected_text_found": expected_text in body}
        except Exception as exc:
            return {"status": f"probe_failed:{exc.__class__.__name__}", "expected_text_found": False}

    def rewrite_url(self, url: str, base_url: str) -> str:
        if not base_url:
            return url
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)
        if not parsed_url.scheme or not parsed_url.netloc or not parsed_base.scheme or not parsed_base.netloc:
            return url
        return urlunparse(parsed_url._replace(scheme=parsed_base.scheme, netloc=parsed_base.netloc))

    def wait_for_file(self, path: Path, min_size: int, timeout_seconds: float) -> None:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if path.exists() and path.stat().st_size >= min_size:
                return
            time.sleep(0.2)

    def resolve_ledger(self, ledger_id: str) -> dict:
        if ledger_id:
            detail = safe_call(lambda: self.visual_qa_ledger.detail(ledger_id), {})
            return detail if isinstance(detail, dict) else self.error("visual_qa_ledger_not_found", "Visual QA ledger detail failed.")
        rows = safe_call(lambda: self.visual_qa_ledger.list_ledgers(1), [])
        if not isinstance(rows, list) or not rows:
            return self.error("visual_evidence_capture_input_missing", "At least one Visual QA ledger is required.")
        detail = safe_call(lambda: self.visual_qa_ledger.detail(str(rows[0].get("ledger_id") or "")), {})
        return detail if isinstance(detail, dict) else self.error("visual_qa_ledger_not_found", "Visual QA ledger detail failed.")

    def browser_executable(self) -> Path | None:
        candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def recommended_actions(self, rows: list[dict]) -> list[str]:
        actions = []
        for row in rows:
            if row.get("capture_status") != "captured":
                actions.append(f"{row.get('target_id')}: inspect screenshot capture failure ({row.get('failure_reason')}).")
            elif row.get("expected_text_found") is False:
                actions.append(f"{row.get('target_id')}: screenshot captured, but expected text probe did not match.")
        if not actions:
            actions.append("All Visual QA targets were captured. Attach the contact sheet to the local reviewer walkthrough.")
        return actions[:10]

    def capture_markdown(self, capture: dict) -> str:
        lines = [
            "# Visual Evidence Capture",
            "",
            f"- Capture id: `{capture.get('capture_id')}`",
            f"- App version: `{capture.get('app_version')}`",
            f"- Ledger: `{capture.get('ledger_id')}`",
            f"- Readiness: `{capture.get('capture_readiness')}`",
            f"- Captured targets: `{capture.get('captured_count')}` / `{capture.get('target_count')}`",
            f"- Failed targets: `{capture.get('failed_count')}`",
            f"- Expected text matches: `{capture.get('expected_text_match_count')}`",
            "",
            "## Capture Rows",
            "",
        ]
        for row in capture.get("capture_rows", []):
            lines.extend([
                f"### {row.get('target_id')}",
                "",
                f"- Status: `{row.get('capture_status')}`",
                f"- URL: `{row.get('capture_url')}`",
                f"- Expected text found: `{row.get('expected_text_found')}`",
                f"- Screenshot bytes: `{row.get('screenshot_size_bytes')}`",
                "",
            ])
        lines.extend(["## Claim Boundary", "", f"- Approved review wording: {self.review_wording}", "- This artifact captures demo screens only. It is not field verification, crash prediction, or an absolute site condition claim.", "- Source GIS files remain read-only.", ""])
        return "\n".join(lines)

    def contact_sheet_html(self, capture: dict) -> str:
        cards = []
        for row in capture.get("capture_rows", []):
            image_html = "<p>No screenshot captured.</p>"
            path = Path(str(row.get("screenshot_path") or ""))
            if path.exists() and self.safe_capture_path(path):
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                image_html = f'<img src="data:image/png;base64,{encoded}" alt="{row.get("target_id")}" />'
            cards.append(f"""
              <article class="card">
                <h2>{row.get("target_id")}</h2>
                <p>Status: <code>{row.get("capture_status")}</code>; expected text: <code>{row.get("expected_text_found")}</code></p>
                <p>{row.get("capture_url")}</p>
                {image_html}
              </article>
            """)
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Visual Evidence Capture</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f4; color: #1f2933; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }}
      .card {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; }}
      img {{ width: 100%; border: 1px solid #c9cbc3; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Visual Evidence Capture</h1>
    <p>Capture: <code>{capture.get("capture_id")}</code>; readiness: <code>{capture.get("capture_readiness")}</code>; captured: <code>{capture.get("captured_count")}</code> / <code>{capture.get("target_count")}</code>.</p>
    <p>{self.review_wording}</p>
    <div class="grid">
      {''.join(cards)}
    </div>
  </body>
</html>"""

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["browser screenshot evidence", "demo target capture", "visual QA support", "portfolio reviewer evidence"],
            "not_allowed": ["field verification", "crash prediction", "absolute site judgement"],
            "source_data_rule": "This feature captures local app/demo screens only; it does not read or mutate source GIS files.",
        }

    def capture_dir(self, capture_id: str) -> Path:
        return self.captures_dir / safe_token(capture_id, "missing_visual_evidence_capture", 180)

    def safe_capture_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.captures_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
