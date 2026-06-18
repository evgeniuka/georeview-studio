from __future__ import annotations

import base64
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


VISUAL_EVIDENCE_REVIEW_DIFF_VERSION = "visual_evidence_review_diff_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "visual_evidence_review_diff", max_len: int = 150) -> str:
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
        return {"error": "visual_evidence_review_diff_probe_failed", "detail": repr(exc)}


class VisualEvidenceReviewDiffBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        visual_evidence_capture: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.visual_evidence_capture = visual_evidence_capture
        self.expected_api_endpoints = expected_api_endpoints
        self.diffs_dir = output_root / "georeview_studio_visual_evidence_review_diffs"
        self.captures_dir = output_root / "georeview_studio_visual_evidence_captures"

    def status(self) -> dict:
        captures = self.ready_captures(100)
        diffs = self.list_diffs(100)
        ready_diffs = [row for row in diffs if row.get("diff_readiness") == "ready_for_visual_evidence_diff_review"]
        latest_diff = ready_diffs[0] if ready_diffs else {}
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "visual_evidence_review_diff_version": VISUAL_EVIDENCE_REVIEW_DIFF_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "compare_visual_evidence_capture_sets",
            "output_dir": str(self.diffs_dir),
            "capture_count": len(captures),
            "baseline_candidate_count": max(0, len(captures) - 1),
            "latest_capture_id": captures[0].get("capture_id") if captures else "",
            "diff_count": len(diffs),
            "ready_diff_count": len(ready_diffs),
            "latest_diff_id": latest_diff.get("diff_id", ""),
            "latest_changed_screenshots": latest_diff.get("changed_screenshots", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_visual_evidence_diff" if len(captures) >= 2 else "waiting_for_two_visual_evidence_captures",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_diff(self, body: dict | None = None) -> dict:
        body = body or {}
        latest_id = str(body.get("latest_capture_id") or "").strip()
        baseline_id = str(body.get("baseline_capture_id") or "").strip()
        captures = self.ready_captures(20)
        if not latest_id and captures:
            latest_id = str(captures[0].get("capture_id") or "")
        if not baseline_id:
            for row in captures:
                candidate = str(row.get("capture_id") or "")
                if candidate and candidate != latest_id:
                    baseline_id = candidate
                    break
        if not latest_id or not baseline_id:
            return self.error("visual_evidence_review_diff_input_missing", "At least two ready visual evidence captures are required.")
        if latest_id == baseline_id:
            return self.error("visual_evidence_review_diff_input_missing", "Latest and baseline captures must be different.")

        latest = self.resolve_capture(latest_id)
        baseline = self.resolve_capture(baseline_id)
        if latest.get("error"):
            return latest
        if baseline.get("error"):
            return baseline
        if latest.get("capture_readiness") != "ready_for_visual_evidence_review" or baseline.get("capture_readiness") != "ready_for_visual_evidence_review":
            return self.error("visual_evidence_review_diff_not_ready", "Both captures must be ready_for_visual_evidence_review.")

        delta = self.compare_captures(baseline, latest)
        stamp = utc_now()
        diff_id = f"visual_evidence_review_diff_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        diff_dir = self.diff_dir(diff_id)
        manifest_path = diff_dir / "visual_evidence_review_diff_manifest.json"
        markdown_path = diff_dir / "visual_evidence_review_diff.md"
        html_path = diff_dir / "visual_evidence_review_diff.html"
        latest_path = self.diffs_dir / "latest_visual_evidence_review_diff.json"
        summary = delta.get("summary", {})
        diff = {
            "ok": True,
            "visual_evidence_review_diff_version": VISUAL_EVIDENCE_REVIEW_DIFF_VERSION,
            "diff_id": diff_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Visual evidence review diff for captured screenshot sets."),
            "app_version": self.app_version,
            "baseline_capture_id": baseline.get("capture_id"),
            "latest_capture_id": latest.get("capture_id"),
            "diff_readiness": "ready_for_visual_evidence_diff_review",
            "baseline_target_count": len(baseline.get("capture_rows", [])),
            "latest_target_count": len(latest.get("capture_rows", [])),
            "changed_screenshots": summary.get("changed_screenshots", 0),
            "unchanged_screenshots": summary.get("unchanged_screenshots", 0),
            "added_targets": summary.get("added_targets", 0),
            "removed_targets": summary.get("removed_targets", 0),
            "diff_summary": summary,
            "diff_rows": delta.get("rows", []),
            "review_recommendations": self.review_recommendations(summary),
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
        write_json(manifest_path, diff)
        write_json(latest_path, diff)
        markdown_path.write_text(self.diff_markdown(diff), encoding="utf-8", newline="\n")
        html_path.write_text(self.diff_html(diff), encoding="utf-8", newline="\n")
        return {"ok": True, "diff": diff, "source_gis_modified": False, "mutates_config": False}

    def list_diffs(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.diffs_dir.exists():
            return rows
        manifests = sorted(
            self.diffs_dir.glob("visual_evidence_review_diff_*/visual_evidence_review_diff_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("visual_evidence_review_diff_version") != VISUAL_EVIDENCE_REVIEW_DIFF_VERSION:
                continue
            rows.append({
                "diff_id": payload.get("diff_id"),
                "created_at": payload.get("created_at"),
                "diff_readiness": payload.get("diff_readiness"),
                "baseline_capture_id": payload.get("baseline_capture_id"),
                "latest_capture_id": payload.get("latest_capture_id"),
                "changed_screenshots": payload.get("changed_screenshots"),
                "added_targets": payload.get("added_targets"),
                "removed_targets": payload.get("removed_targets"),
                "download_url": f"/api/visual-evidence-review-diff/diffs/{payload.get('diff_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, diff_id: str) -> dict:
        path = self.diff_dir(diff_id) / "visual_evidence_review_diff_manifest.json"
        if not path.exists() or not self.safe_diff_path(path):
            return {"ok": False, "error": "visual_evidence_review_diff_not_found", "diff_id": diff_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "visual_evidence_review_diff_not_found", "diff_id": diff_id, "source_gis_modified": False}
        return payload

    def output_file(self, diff_id: str, output_id: str = "html") -> dict:
        detail = self.detail(diff_id)
        if detail.get("error"):
            return detail
        if output_id not in {"html", "review"}:
            return {"ok": False, "error": "visual_evidence_review_diff_output_not_found", "diff_id": diff_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists() or not self.safe_diff_path(path):
            return {"ok": False, "error": "visual_evidence_review_diff_output_not_found", "diff_id": diff_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_captures(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.visual_evidence_capture.list_captures(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("capture_readiness") == "ready_for_visual_evidence_review"]

    def resolve_capture(self, capture_id: str) -> dict:
        detail = safe_call(lambda: self.visual_evidence_capture.detail(capture_id), {})
        return detail if isinstance(detail, dict) else self.error("visual_evidence_capture_not_found", "Visual evidence capture detail failed.")

    def compare_captures(self, baseline: dict, latest: dict) -> dict:
        baseline_rows = {str(row.get("target_id") or ""): row for row in baseline.get("capture_rows", []) if row.get("target_id")}
        latest_rows = {str(row.get("target_id") or ""): row for row in latest.get("capture_rows", []) if row.get("target_id")}
        rows = []
        for target_id in sorted(set(baseline_rows) | set(latest_rows)):
            base = baseline_rows.get(target_id)
            new = latest_rows.get(target_id)
            if base is None:
                rows.append(self.diff_row(target_id, "added", {}, new or {}))
            elif new is None:
                rows.append(self.diff_row(target_id, "removed", base, {}))
            else:
                rows.append(self.diff_row(target_id, "compared", base, new))
        summary = {
            "baseline_capture_id": baseline.get("capture_id"),
            "latest_capture_id": latest.get("capture_id"),
            "baseline_targets": len(baseline_rows),
            "latest_targets": len(latest_rows),
            "added_targets": len([row for row in rows if row.get("diff_status") == "added"]),
            "removed_targets": len([row for row in rows if row.get("diff_status") == "removed"]),
            "changed_screenshots": len([row for row in rows if row.get("screenshot_changed") is True]),
            "unchanged_screenshots": len([row for row in rows if row.get("screenshot_changed") is False and row.get("diff_status") == "compared"]),
            "metadata_changed_targets": len([row for row in rows if row.get("metadata_changed") is True]),
            "review_required_targets": len([row for row in rows if row.get("review_priority") == "review_required"]),
        }
        return {"summary": summary, "rows": rows}

    def diff_row(self, target_id: str, diff_status: str, baseline: dict, latest: dict) -> dict:
        base_path = Path(str(baseline.get("screenshot_path") or ""))
        latest_path = Path(str(latest.get("screenshot_path") or ""))
        base_hash = self.hash_file(base_path)
        latest_hash = self.hash_file(latest_path)
        screenshot_changed = None
        if diff_status == "compared":
            screenshot_changed = bool(base_hash and latest_hash and base_hash != latest_hash)
        metadata_fields = ["capture_status", "expected_text_found", "capture_url", "expected_text", "selector_hint"]
        metadata_changed = any(str(baseline.get(field) or "") != str(latest.get(field) or "") for field in metadata_fields)
        review_required = diff_status in {"added", "removed"} or screenshot_changed is True or metadata_changed
        return {
            "target_id": target_id,
            "diff_status": diff_status,
            "baseline_capture_status": baseline.get("capture_status"),
            "latest_capture_status": latest.get("capture_status"),
            "baseline_expected_text_found": baseline.get("expected_text_found"),
            "latest_expected_text_found": latest.get("expected_text_found"),
            "baseline_screenshot_path": str(base_path) if str(base_path) != "." else "",
            "latest_screenshot_path": str(latest_path) if str(latest_path) != "." else "",
            "baseline_screenshot_size_bytes": baseline.get("screenshot_size_bytes", 0),
            "latest_screenshot_size_bytes": latest.get("screenshot_size_bytes", 0),
            "size_delta_bytes": int(latest.get("screenshot_size_bytes") or 0) - int(baseline.get("screenshot_size_bytes") or 0),
            "baseline_sha256": base_hash,
            "latest_sha256": latest_hash,
            "screenshot_changed": screenshot_changed,
            "metadata_changed": metadata_changed,
            "review_priority": "review_required" if review_required else "no_change",
        }

    def hash_file(self, path: Path) -> str:
        if not path.exists() or not self.safe_capture_path(path):
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def review_recommendations(self, summary: dict) -> list[str]:
        recommendations = []
        if int(summary.get("changed_screenshots") or 0):
            recommendations.append("Review changed screenshots in the HTML side-by-side diff before recording the demo.")
        if int(summary.get("metadata_changed_targets") or 0):
            recommendations.append("Check changed expected text, target URLs or capture statuses before sharing.")
        if int(summary.get("added_targets") or 0) or int(summary.get("removed_targets") or 0):
            recommendations.append("Confirm added or removed visual targets match the intended demo flow.")
        if not recommendations:
            recommendations.append("No screenshot or target metadata changes detected; keep the diff as reproducibility evidence.")
        recommendations.append("Use this as local visual evidence only; it does not verify real-world infrastructure.")
        return recommendations

    def diff_markdown(self, diff: dict) -> str:
        summary = diff.get("diff_summary", {})
        lines = [
            "# Visual Evidence Review Diff",
            "",
            f"- Diff id: `{diff.get('diff_id')}`",
            f"- App version: `{diff.get('app_version')}`",
            f"- Baseline capture: `{diff.get('baseline_capture_id')}`",
            f"- Latest capture: `{diff.get('latest_capture_id')}`",
            f"- Readiness: `{diff.get('diff_readiness')}`",
            "",
            "## Summary",
            "",
            f"- Baseline targets: `{summary.get('baseline_targets')}`",
            f"- Latest targets: `{summary.get('latest_targets')}`",
            f"- Changed screenshots: `{summary.get('changed_screenshots')}`",
            f"- Metadata changed targets: `{summary.get('metadata_changed_targets')}`",
            f"- Review-required targets: `{summary.get('review_required_targets')}`",
            "",
            "## Target Rows",
            "",
        ]
        for row in diff.get("diff_rows", []):
            lines.extend([
                f"### {row.get('target_id')}",
                "",
                f"- Status: `{row.get('diff_status')}`",
                f"- Screenshot changed: `{row.get('screenshot_changed')}`",
                f"- Metadata changed: `{row.get('metadata_changed')}`",
                f"- Review priority: `{row.get('review_priority')}`",
                f"- Size delta bytes: `{row.get('size_delta_bytes')}`",
                "",
            ])
        lines.extend(["## Recommendations", ""])
        for item in diff.get("review_recommendations", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- This diff compares generated local screenshots only. It is not field verification, crash prediction, or an absolute site condition claim.",
            "- Source GIS files remain read-only.",
            "",
        ])
        return "\n".join(lines)

    def diff_html(self, diff: dict) -> str:
        cards = []
        for row in diff.get("diff_rows", []):
            baseline_image = self.image_html(row.get("baseline_screenshot_path"), f"{row.get('target_id')} baseline")
            latest_image = self.image_html(row.get("latest_screenshot_path"), f"{row.get('target_id')} latest")
            cards.append(f"""
              <article class="card">
                <h2>{html.escape(str(row.get("target_id") or ""))}</h2>
                <p>Status: <code>{html.escape(str(row.get("diff_status") or ""))}</code>; screenshot changed: <code>{html.escape(str(row.get("screenshot_changed")))}</code>; metadata changed: <code>{html.escape(str(row.get("metadata_changed")))}</code></p>
                <p>Size delta: <code>{html.escape(str(row.get("size_delta_bytes") or 0))}</code> bytes; review: <code>{html.escape(str(row.get("review_priority") or ""))}</code></p>
                <div class="pair">
                  <section><h3>Baseline</h3>{baseline_image}</section>
                  <section><h3>Latest</h3>{latest_image}</section>
                </div>
              </article>
            """)
        summary = diff.get("diff_summary", {})
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Visual Evidence Review Diff</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7f4; color: #1f2933; }}
      .summary, .card {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; margin-bottom: 16px; }}
      .pair {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px; }}
      img {{ width: 100%; border: 1px solid #c9cbc3; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>Visual Evidence Review Diff</h1>
    <div class="summary">
      <p>Diff: <code>{html.escape(str(diff.get("diff_id") or ""))}</code>; readiness: <code>{html.escape(str(diff.get("diff_readiness") or ""))}</code>.</p>
      <p>Changed screenshots: <code>{html.escape(str(summary.get("changed_screenshots") or 0))}</code>; metadata changed targets: <code>{html.escape(str(summary.get("metadata_changed_targets") or 0))}</code>; review-required targets: <code>{html.escape(str(summary.get("review_required_targets") or 0))}</code>.</p>
      <p>{html.escape(self.review_wording)}</p>
    </div>
    {''.join(cards)}
  </body>
</html>"""

    def image_html(self, path_value: object, alt: str) -> str:
        path = Path(str(path_value or ""))
        if not path.exists() or not self.safe_capture_path(path):
            return "<p>No screenshot available.</p>"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f'<img src="data:image/png;base64,{encoded}" alt="{html.escape(alt)}" />'

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["visual screenshot evidence comparison", "review target prioritization", "local portfolio QA evidence"],
            "not_allowed": ["field verification", "crash prediction", "absolute site judgement"],
            "source_data_rule": "This feature compares generated screenshot artifacts only; it does not read or mutate source GIS files.",
        }

    def diff_dir(self, diff_id: str) -> Path:
        return self.diffs_dir / safe_token(diff_id, "missing_visual_evidence_review_diff", 180)

    def safe_diff_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.diffs_dir.resolve()))
        except OSError:
            return False

    def safe_capture_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.captures_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
