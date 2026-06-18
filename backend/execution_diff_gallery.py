from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


EXECUTION_DIFF_GALLERY_VERSION = "execution_diff_gallery_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "execution_diff_gallery") -> str:
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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def safe_call(fn: Callable[[], object], default: object) -> object:
    try:
        result = fn()
        return result if result is not None else default
    except Exception as exc:
        return {"error": "execution_diff_gallery_probe_failed", "detail": repr(exc)}


class ExecutionDiffGalleryBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        execution_result_diff: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.execution_result_diff = execution_result_diff
        self.expected_api_endpoints = expected_api_endpoints
        self.galleries_dir = output_root / "georeview_studio_execution_diff_galleries"

    def status(self) -> dict:
        items = self.items(limit=500)
        galleries = self.list_galleries(limit=500)
        ready_items = [row for row in items if row.get("diff_readiness") == "ready_for_reviewer"]
        review_queue = [row for row in items if row.get("review_priority", 0) >= 70]
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "execution_diff_gallery_version": EXECUTION_DIFF_GALLERY_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "index_execution_result_diffs_for_reviewer_gallery",
            "output_dir": str(self.galleries_dir),
            "indexed_diff_count": len(items),
            "ready_diff_count": len(ready_items),
            "review_queue_count": len(review_queue),
            "gallery_count": len(galleries),
            "ready_gallery_count": len([row for row in galleries if row.get("gallery_readiness") == "ready_for_reviewer"]),
            "classification_counts": self.counts(items, "diff_classification"),
            "readiness_counts": self.counts(items, "diff_readiness"),
            "scope_counts": self.counts(items, "comparison_scope"),
            "latest_diff_id": items[0].get("diff_id") if items else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_diff_gallery" if ready_items else "waiting_for_reviewer_ready_diffs",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def items(
        self,
        limit: int = 20,
        classification: str = "",
        readiness: str = "",
        scope: str = "",
    ) -> list[dict]:
        raw_rows = safe_call(lambda: self.execution_result_diff.list_diffs(500), [])
        if not isinstance(raw_rows, list):
            return []
        rows: list[dict] = []
        for raw in raw_rows:
            diff_id = str(raw.get("diff_id") or "")
            if not diff_id:
                continue
            detail = safe_call(lambda diff_id=diff_id: self.execution_result_diff.detail(diff_id), {})
            if not isinstance(detail, dict) or detail.get("error"):
                continue
            item = self.gallery_item(detail)
            if classification and item.get("diff_classification") != classification:
                continue
            if readiness and item.get("diff_readiness") != readiness:
                continue
            if scope and item.get("comparison_scope") != scope:
                continue
            rows.append(item)
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def create_gallery(self, body: dict | None = None) -> dict:
        body = body or {}
        classification = str(body.get("classification") or "").strip()
        readiness = str(body.get("readiness") or "").strip()
        scope = str(body.get("scope") or "").strip()
        items = self.items(
            limit=max(1, min(int(body.get("limit") or 50), 500)),
            classification=classification,
            readiness=readiness,
            scope=scope,
        )
        if not items:
            return self.error("execution_diff_gallery_not_ready", "No execution result diff items are available for the requested gallery filters.")

        status = self.status()
        stamp = utc_now()
        gallery_id = f"execution_diff_gallery_{safe_token(stamp.replace(':', '_'))}"
        json_path = self.gallery_path(gallery_id, ".json")
        md_path = self.gallery_path(gallery_id, ".md")
        latest_path = self.galleries_dir / "latest_execution_diff_gallery.json"
        review_queue = [row for row in items if row.get("review_priority", 0) >= 70]
        gallery = {
            "ok": True,
            "execution_diff_gallery_version": EXECUTION_DIFF_GALLERY_VERSION,
            "gallery_id": gallery_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer-facing gallery of execution result diffs."),
            "app_version": self.app_version,
            "gallery_readiness": "ready_for_reviewer" if status.get("ready_diff_count", 0) >= 1 else "needs_execution_diffs",
            "filters": {"classification": classification, "readiness": readiness, "scope": scope},
            "summary": status,
            "item_count": len(items),
            "review_queue_count": len(review_queue),
            "items": items,
            "review_queue": sorted(review_queue, key=lambda row: row.get("review_priority", 0), reverse=True)[:20],
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)},
        }
        write_json(json_path, gallery)
        write_json(latest_path, gallery)
        md_path.write_text(self.gallery_markdown(gallery), encoding="utf-8", newline="\n")
        return {"ok": True, "gallery": gallery, "source_gis_modified": False, "mutates_config": False}

    def list_galleries(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.galleries_dir.exists():
            return rows
        for path in sorted(self.galleries_dir.glob("execution_diff_gallery_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("execution_diff_gallery_version") != EXECUTION_DIFF_GALLERY_VERSION:
                continue
            rows.append({
                "gallery_id": data.get("gallery_id"),
                "created_at": data.get("created_at"),
                "gallery_readiness": data.get("gallery_readiness"),
                "item_count": data.get("item_count"),
                "review_queue_count": data.get("review_queue_count"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, gallery_id: str) -> dict:
        path = self.gallery_path(gallery_id, ".json")
        if not path.exists() or not self.safe_gallery_path(path):
            return {"ok": False, "error": "execution_diff_gallery_not_found", "gallery_id": gallery_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "execution_diff_gallery_not_found", "gallery_id": gallery_id, "source_gis_modified": False}
        return payload

    def output_file(self, gallery_id: str, output_id: str = "execution_diff_gallery") -> dict:
        detail = self.detail(gallery_id)
        if detail.get("error"):
            return detail
        if output_id not in {"execution_diff_gallery", "markdown"}:
            return {"ok": False, "error": "execution_diff_gallery_output_not_found", "gallery_id": gallery_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_gallery_path(path):
            return {"ok": False, "error": "execution_diff_gallery_output_not_found", "gallery_id": gallery_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def gallery_item(self, detail: dict) -> dict:
        comparison = detail.get("comparison", {}) if isinstance(detail.get("comparison"), dict) else {}
        table_diffs = comparison.get("table_diffs", []) if isinstance(comparison.get("table_diffs"), list) else []
        output_diff = comparison.get("output_diff", {}) if isinstance(comparison.get("output_diff"), dict) else {}
        quality_checks = detail.get("quality_checks", []) if isinstance(detail.get("quality_checks"), list) else []
        row_change_count = len([row for row in table_diffs if row.get("status") == "changed"])
        output_delta_count = sum(len(output_diff.get(key, [])) for key in ["only_left", "only_right", "expected_only_left", "expected_only_right"])
        quality_warning_count = len([row for row in quality_checks if row.get("passed") is not True])
        classification = str(detail.get("diff_classification") or "")
        readiness = str(detail.get("diff_readiness") or "")
        priority = self.review_priority(classification, readiness, row_change_count, output_delta_count, quality_warning_count)
        return {
            "diff_id": detail.get("diff_id"),
            "created_at": detail.get("created_at"),
            "diff_readiness": readiness,
            "diff_classification": classification,
            "comparison_scope": detail.get("comparison_scope"),
            "left_package_id": detail.get("left_package_id"),
            "right_package_id": detail.get("right_package_id"),
            "left_workspace_id": detail.get("left_workspace_id"),
            "right_workspace_id": detail.get("right_workspace_id"),
            "row_change_count": row_change_count,
            "output_delta_count": output_delta_count,
            "quality_warning_count": quality_warning_count,
            "review_priority": priority,
            "portfolio_label": self.portfolio_label(classification, priority),
            "download_url": f"/api/execution-result-diff/diffs/{detail.get('diff_id')}/download",
            "source_gis_modified": False,
            "mutates_config": False,
        }

    @staticmethod
    def review_priority(classification: str, readiness: str, row_changes: int, output_deltas: int, quality_warnings: int) -> int:
        if readiness != "ready_for_reviewer":
            return 95
        if classification == "result_difference_review_needed":
            return 85
        if classification == "lineage_difference_review":
            return 70
        if row_changes or output_deltas or quality_warnings:
            return 60
        return 20

    @staticmethod
    def portfolio_label(classification: str, priority: int) -> str:
        if priority >= 80:
            return "review_needed"
        if classification == "lineage_difference_review":
            return "lineage_review"
        return "reproducibility_evidence"

    @staticmethod
    def counts(rows: list[dict], key: str) -> dict:
        result: dict[str, int] = {}
        for row in rows:
            value = str(row.get(key) or "unknown")
            result[value] = result.get(value, 0) + 1
        return dict(sorted(result.items()))

    def gallery_markdown(self, gallery: dict) -> str:
        summary = gallery.get("summary", {})
        lines = [
            "# Execution Diff Gallery",
            "",
            f"Gallery: `{gallery.get('gallery_id')}`",
            f"Created: `{gallery.get('created_at')}`",
            f"Readiness: `{gallery.get('gallery_readiness')}`",
            f"Item count: `{gallery.get('item_count')}`",
            f"Review queue count: `{gallery.get('review_queue_count')}`",
            "",
            "Approved review wording:",
            "",
            f"> {self.review_wording}",
            "",
            "## Summary",
            "",
            f"- Indexed diffs: `{summary.get('indexed_diff_count')}`",
            f"- Ready diffs: `{summary.get('ready_diff_count')}`",
            f"- Latest diff: `{summary.get('latest_diff_id')}`",
            f"- Expected API endpoints: `{summary.get('expected_api_endpoints')}`",
            f"- Classification counts: `{json.dumps(summary.get('classification_counts', {}), ensure_ascii=False)}`",
            f"- Scope counts: `{json.dumps(summary.get('scope_counts', {}), ensure_ascii=False)}`",
            "",
            "## Reviewer Queue",
            "",
        ]
        queue = gallery.get("review_queue", [])
        if not queue:
            lines.append("No high-priority result differences are currently queued for review.")
        for row in queue:
            lines.append(f"- `{row.get('diff_id')}`: `{row.get('portfolio_label')}`, priority `{row.get('review_priority')}`, classification `{row.get('diff_classification')}`")
        lines.extend(["", "## Gallery Items", ""])
        for row in gallery.get("items", [])[:50]:
            lines.extend([
                f"### `{row.get('diff_id')}`",
                "",
                f"- Readiness: `{row.get('diff_readiness')}`",
                f"- Classification: `{row.get('diff_classification')}`",
                f"- Scope: `{row.get('comparison_scope')}`",
                f"- Row changes: `{row.get('row_change_count')}`",
                f"- Output deltas: `{row.get('output_delta_count')}`",
                f"- Quality warnings: `{row.get('quality_warning_count')}`",
                f"- Portfolio label: `{row.get('portfolio_label')}`",
                "",
            ])
        lines.extend(["## Boundaries", ""])
        for item in self.claim_boundaries():
            lines.append(f"- {item}")
        lines.extend(["", "Source GIS modified: `false`", "Config mutated: `false`", ""])
        return "\n".join(lines)

    def claim_boundaries(self) -> list[str]:
        return [
            "The gallery indexes execution result evidence; it does not make crash predictions.",
            "Reproducible diffs are engineering evidence about generated outputs, not proof of real-world safety outcomes.",
            "Review-needed diffs are prompts for data and pipeline investigation.",
            "Source GIS files remain read-only; gallery artifacts are written under analysis_output only.",
            self.review_wording,
        ]

    def gallery_path(self, gallery_id: str, suffix: str) -> Path:
        return self.galleries_dir / f"{safe_token(gallery_id)}{suffix}"

    def safe_gallery_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.galleries_dir.resolve())
            return True
        except ValueError:
            return False

    def error(self, error: str, detail: str) -> dict:
        return {"ok": False, "error": error, "detail": detail, "source_gis_modified": False, "mutates_config": False}
