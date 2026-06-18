from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


VISUAL_EVIDENCE_REVIEW_ANNOTATIONS_VERSION = "visual_evidence_review_annotations_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "visual_evidence_review_annotations", max_len: int = 150) -> str:
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
        return {"error": "visual_evidence_review_annotations_probe_failed", "detail": repr(exc)}


class VisualEvidenceReviewAnnotationsBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        visual_evidence_review_diff: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.visual_evidence_review_diff = visual_evidence_review_diff
        self.expected_api_endpoints = expected_api_endpoints
        self.annotations_dir = output_root / "georeview_studio_visual_evidence_review_annotations"

    def status(self) -> dict:
        diffs = self.ready_diffs(100)
        annotations = self.list_annotations(100)
        ready_annotations = [row for row in annotations if row.get("annotation_readiness") == "ready_for_visual_evidence_annotation_review"]
        latest_annotation = ready_annotations[0] if ready_annotations else {}
        latest_diff = diffs[0] if diffs else {}
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "visual_evidence_review_annotations_version": VISUAL_EVIDENCE_REVIEW_ANNOTATIONS_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "annotate_visual_evidence_review_diffs",
            "output_dir": str(self.annotations_dir),
            "ready_diff_count": len(diffs),
            "latest_diff_id": latest_diff.get("diff_id", ""),
            "annotation_count": len(annotations),
            "ready_annotation_count": len(ready_annotations),
            "latest_annotation_id": latest_annotation.get("annotation_id", ""),
            "latest_pending_review_count": latest_annotation.get("needs_reviewer_attention", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_visual_evidence_annotations" if diffs else "waiting_for_visual_evidence_review_diff",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_annotations(self, body: dict | None = None) -> dict:
        body = body or {}
        diff_id = str(body.get("diff_id") or "").strip()
        if not diff_id:
            diffs = self.ready_diffs(20)
            diff_id = str(diffs[0].get("diff_id") or "") if diffs else ""
        if not diff_id:
            return self.error("visual_evidence_review_annotations_input_missing", "A ready visual evidence review diff is required.")
        diff = self.resolve_diff(diff_id)
        if diff.get("error"):
            return diff
        if diff.get("diff_readiness") != "ready_for_visual_evidence_diff_review":
            return self.error("visual_evidence_review_annotations_not_ready", "Diff must be ready_for_visual_evidence_diff_review.")

        rows = self.annotation_rows(diff, body)
        summary = self.annotation_summary(rows)
        stamp = utc_now()
        annotation_id = f"visual_evidence_review_annotations_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        annotation_dir = self.annotation_dir(annotation_id)
        manifest_path = annotation_dir / "visual_evidence_review_annotations_manifest.json"
        markdown_path = annotation_dir / "visual_evidence_review_annotations.md"
        html_path = annotation_dir / "visual_evidence_review_annotations.html"
        latest_path = self.annotations_dir / "latest_visual_evidence_review_annotations.json"
        annotations = {
            "ok": True,
            "visual_evidence_review_annotations_version": VISUAL_EVIDENCE_REVIEW_ANNOTATIONS_VERSION,
            "annotation_id": annotation_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "reviewer": str(body.get("reviewer") or body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer annotation set for visual evidence diff."),
            "app_version": self.app_version,
            "diff_id": diff.get("diff_id"),
            "annotation_readiness": "ready_for_visual_evidence_annotation_review",
            "annotation_summary": summary,
            "annotation_rows": rows,
            "target_count": summary.get("target_count", 0),
            "needs_reviewer_attention": summary.get("needs_reviewer_attention", 0),
            "accepted_no_action": summary.get("accepted_no_action", 0),
            "review_guidance": self.review_guidance(summary),
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
        write_json(manifest_path, annotations)
        write_json(latest_path, annotations)
        markdown_path.write_text(self.annotations_markdown(annotations), encoding="utf-8", newline="\n")
        html_path.write_text(self.annotations_html(annotations), encoding="utf-8", newline="\n")
        return {"ok": True, "annotations": annotations, "source_gis_modified": False, "mutates_config": False}

    def list_annotations(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.annotations_dir.exists():
            return rows
        manifests = sorted(
            self.annotations_dir.glob("visual_evidence_review_annotations_*/visual_evidence_review_annotations_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("visual_evidence_review_annotations_version") != VISUAL_EVIDENCE_REVIEW_ANNOTATIONS_VERSION:
                continue
            rows.append({
                "annotation_id": payload.get("annotation_id"),
                "created_at": payload.get("created_at"),
                "annotation_readiness": payload.get("annotation_readiness"),
                "diff_id": payload.get("diff_id"),
                "target_count": payload.get("target_count"),
                "needs_reviewer_attention": payload.get("needs_reviewer_attention"),
                "accepted_no_action": payload.get("accepted_no_action"),
                "download_url": f"/api/visual-evidence-review-annotations/annotations/{payload.get('annotation_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, annotation_id: str) -> dict:
        path = self.annotation_dir(annotation_id) / "visual_evidence_review_annotations_manifest.json"
        if not path.exists() or not self.safe_annotation_path(path):
            return {"ok": False, "error": "visual_evidence_review_annotations_not_found", "annotation_id": annotation_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "visual_evidence_review_annotations_not_found", "annotation_id": annotation_id, "source_gis_modified": False}
        return payload

    def output_file(self, annotation_id: str, output_id: str = "html") -> dict:
        detail = self.detail(annotation_id)
        if detail.get("error"):
            return detail
        if output_id not in {"html", "review"}:
            return {"ok": False, "error": "visual_evidence_review_annotations_output_not_found", "annotation_id": annotation_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("html") or ""))
        if not path.exists() or not self.safe_annotation_path(path):
            return {"ok": False, "error": "visual_evidence_review_annotations_output_not_found", "annotation_id": annotation_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_diffs(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.visual_evidence_review_diff.list_diffs(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("diff_readiness") == "ready_for_visual_evidence_diff_review"]

    def resolve_diff(self, diff_id: str) -> dict:
        detail = safe_call(lambda: self.visual_evidence_review_diff.detail(diff_id), {})
        return detail if isinstance(detail, dict) else self.error("visual_evidence_review_diff_not_found", "Visual evidence review diff detail failed.")

    def annotation_rows(self, diff: dict, body: dict) -> list[dict]:
        manual_notes = body.get("target_notes") if isinstance(body.get("target_notes"), dict) else {}
        rows = []
        for row in diff.get("diff_rows", []):
            target_id = str(row.get("target_id") or "")
            screenshot_changed = row.get("screenshot_changed") is True
            metadata_changed = row.get("metadata_changed") is True
            diff_status = str(row.get("diff_status") or "")
            review_required = row.get("review_priority") == "review_required"
            if review_required:
                decision = "needs_reviewer_attention"
                action = self.recommended_action(diff_status, screenshot_changed, metadata_changed)
            else:
                decision = "accepted_no_action"
                action = "Keep as reproducibility evidence; no manual follow-up is required from this generated diff."
            rows.append({
                "target_id": target_id,
                "diff_status": diff_status,
                "screenshot_changed": screenshot_changed,
                "metadata_changed": metadata_changed,
                "size_delta_bytes": row.get("size_delta_bytes", 0),
                "review_priority": row.get("review_priority"),
                "annotation_status": decision,
                "reviewer_decision": "review_before_sharing" if review_required else "accepted_for_demo_evidence",
                "reviewer_note": str(manual_notes.get(target_id) or self.default_note(row, action)),
                "recommended_action": action,
                "source_gis_modified": False,
            })
        return rows

    def annotation_summary(self, rows: list[dict]) -> dict:
        return {
            "target_count": len(rows),
            "needs_reviewer_attention": len([row for row in rows if row.get("annotation_status") == "needs_reviewer_attention"]),
            "accepted_no_action": len([row for row in rows if row.get("annotation_status") == "accepted_no_action"]),
            "screenshot_changed_targets": len([row for row in rows if row.get("screenshot_changed") is True]),
            "metadata_changed_targets": len([row for row in rows if row.get("metadata_changed") is True]),
            "added_or_removed_targets": len([row for row in rows if row.get("diff_status") in {"added", "removed"}]),
        }

    def recommended_action(self, diff_status: str, screenshot_changed: bool, metadata_changed: bool) -> str:
        if diff_status in {"added", "removed"}:
            return "Confirm the target list change matches the intended release walkthrough."
        if screenshot_changed and metadata_changed:
            return "Review the screenshot pair and target metadata before using this evidence in a demo."
        if screenshot_changed:
            return "Review the screenshot pair and confirm the visual change is expected."
        if metadata_changed:
            return "Check changed URL, expected text or capture status before sharing."
        return "Review this target before sharing because the diff marked it for attention."

    @staticmethod
    def default_note(row: dict, action: str) -> str:
        return f"{action} Target diff status is {row.get('diff_status')}; screenshot_changed={row.get('screenshot_changed')}; metadata_changed={row.get('metadata_changed')}."

    def review_guidance(self, summary: dict) -> list[str]:
        guidance = []
        if int(summary.get("needs_reviewer_attention") or 0):
            guidance.append("Inspect all targets marked needs_reviewer_attention before recording or sharing the local demo.")
        else:
            guidance.append("All targets are accepted as generated evidence; keep the annotation set for traceability.")
        guidance.append("Use annotations as QA notes over generated screenshots, not as field observations.")
        guidance.append("Keep missing or uncertain infrastructure evidence as data-quality context, not as automatic risk proof.")
        return guidance

    def annotations_markdown(self, annotations: dict) -> str:
        summary = annotations.get("annotation_summary", {})
        lines = [
            "# Visual Evidence Review Annotations",
            "",
            f"- Annotation id: `{annotations.get('annotation_id')}`",
            f"- App version: `{annotations.get('app_version')}`",
            f"- Diff id: `{annotations.get('diff_id')}`",
            f"- Readiness: `{annotations.get('annotation_readiness')}`",
            f"- Reviewer: `{annotations.get('reviewer')}`",
            "",
            "## Summary",
            "",
            f"- Targets: `{summary.get('target_count')}`",
            f"- Needs reviewer attention: `{summary.get('needs_reviewer_attention')}`",
            f"- Accepted no action: `{summary.get('accepted_no_action')}`",
            f"- Screenshot changed targets: `{summary.get('screenshot_changed_targets')}`",
            f"- Metadata changed targets: `{summary.get('metadata_changed_targets')}`",
            "",
            "## Annotation Rows",
            "",
        ]
        for row in annotations.get("annotation_rows", []):
            lines.extend([
                f"### {row.get('target_id')}",
                "",
                f"- Annotation status: `{row.get('annotation_status')}`",
                f"- Reviewer decision: `{row.get('reviewer_decision')}`",
                f"- Recommended action: {row.get('recommended_action')}",
                f"- Reviewer note: {row.get('reviewer_note')}",
                "",
            ])
        lines.extend(["## Guidance", ""])
        for item in annotations.get("review_guidance", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- These annotations review generated screenshot evidence only.",
            "- Source GIS files remain read-only.",
            "",
        ])
        return "\n".join(lines)

    def annotations_html(self, annotations: dict) -> str:
        rows = []
        for row in annotations.get("annotation_rows", []):
            rows.append(f"""
              <tr>
                <td>{html.escape(str(row.get("target_id") or ""))}</td>
                <td><code>{html.escape(str(row.get("annotation_status") or ""))}</code></td>
                <td>{html.escape(str(row.get("recommended_action") or ""))}</td>
                <td>{html.escape(str(row.get("reviewer_note") or ""))}</td>
              </tr>
            """)
        summary = annotations.get("annotation_summary", {})
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Visual Evidence Review Annotations</title>
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
    <h1>Visual Evidence Review Annotations</h1>
    <div class="summary">
      <p>Annotation: <code>{html.escape(str(annotations.get("annotation_id") or ""))}</code>; readiness: <code>{html.escape(str(annotations.get("annotation_readiness") or ""))}</code>.</p>
      <p>Targets: <code>{html.escape(str(summary.get("target_count") or 0))}</code>; needs reviewer attention: <code>{html.escape(str(summary.get("needs_reviewer_attention") or 0))}</code>; accepted no action: <code>{html.escape(str(summary.get("accepted_no_action") or 0))}</code>.</p>
      <p>{html.escape(self.review_wording)}</p>
    </div>
    <table>
      <thead><tr><th>Target</th><th>Status</th><th>Recommended action</th><th>Reviewer note</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </body>
</html>"""

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["generated visual QA annotations", "reviewer action notes", "portfolio evidence traceability"],
            "not_allowed": ["field verification", "crash prediction", "absolute site condition claim"],
            "source_data_rule": "This feature reads generated visual diff artifacts and writes annotation artifacts under analysis_output only.",
        }

    def annotation_dir(self, annotation_id: str) -> Path:
        return self.annotations_dir / safe_token(annotation_id, "missing_visual_evidence_review_annotations", 180)

    def safe_annotation_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.annotations_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
