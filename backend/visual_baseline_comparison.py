from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


VISUAL_BASELINE_COMPARISON_VERSION = "visual_baseline_comparison_manifest_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "visual_baseline_comparison", max_len: int = 150) -> str:
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
        return {"error": "visual_baseline_comparison_probe_failed", "detail": repr(exc)}


class VisualBaselineComparisonManifestBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        visual_qa_ledger: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.visual_qa_ledger = visual_qa_ledger
        self.expected_api_endpoints = expected_api_endpoints
        self.comparisons_dir = output_root / "georeview_studio_visual_baseline_comparisons"

    def status(self) -> dict:
        ledgers = self.ledger_rows(100)
        comparisons = self.list_comparisons(100)
        ready_comparisons = [row for row in comparisons if row.get("comparison_readiness") == "ready_for_visual_baseline_review"]
        latest = self.resolve_ledger("")
        latest_items = latest.get("qa_items", []) if isinstance(latest, dict) else []
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "visual_baseline_comparison_version": VISUAL_BASELINE_COMPARISON_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "compare_manual_visual_qa_ledgers_across_releases",
            "output_dir": str(self.comparisons_dir),
            "ledger_count": len(ledgers),
            "baseline_candidate_count": max(0, len(ledgers) - 1),
            "latest_ledger_id": latest.get("ledger_id") if isinstance(latest, dict) else "",
            "latest_target_count": len(latest_items),
            "comparison_count": len(comparisons),
            "ready_comparison_count": len(ready_comparisons),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_visual_baseline_comparison" if len(ledgers) >= 2 else "waiting_for_two_visual_qa_ledgers",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_comparison(self, body: dict | None = None) -> dict:
        body = body or {}
        latest_id = str(body.get("latest_ledger_id") or "").strip()
        baseline_id = str(body.get("baseline_ledger_id") or "").strip()
        ledgers = self.ledger_rows(20)
        if not latest_id and ledgers:
            latest_id = str(ledgers[0].get("ledger_id") or "")
        if not baseline_id:
            for row in ledgers:
                candidate = str(row.get("ledger_id") or "")
                if candidate and candidate != latest_id:
                    baseline_id = candidate
                    break
        if not latest_id or not baseline_id:
            return self.error("visual_baseline_comparison_input_missing", "At least two visual QA ledgers are required.")

        latest = self.resolve_ledger(latest_id)
        baseline = self.resolve_ledger(baseline_id)
        if latest.get("error"):
            return latest
        if baseline.get("error"):
            return baseline
        if latest.get("ledger_readiness") != "ready_for_visual_qa_tracking" or baseline.get("ledger_readiness") != "ready_for_visual_qa_tracking":
            return self.error("visual_baseline_comparison_not_ready", "Both visual QA ledgers must be ready_for_visual_qa_tracking.")

        delta = self.compare_ledgers(baseline, latest)
        stamp = utc_now()
        comparison_id = f"visual_baseline_comparison_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        comparison_dir = self.comparison_dir(comparison_id)
        manifest_path = comparison_dir / "visual_baseline_comparison_manifest.json"
        markdown_path = comparison_dir / "visual_baseline_comparison.md"
        latest_path = self.comparisons_dir / "latest_visual_baseline_comparison.json"
        comparison = {
            "ok": True,
            "visual_baseline_comparison_version": VISUAL_BASELINE_COMPARISON_VERSION,
            "comparison_id": comparison_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Visual baseline comparison over manual QA ledgers."),
            "app_version": self.app_version,
            "baseline_ledger_id": baseline.get("ledger_id"),
            "latest_ledger_id": latest.get("ledger_id"),
            "comparison_readiness": "ready_for_visual_baseline_review",
            "baseline_target_count": len(baseline.get("qa_items", [])),
            "latest_target_count": len(latest.get("qa_items", [])),
            "target_delta_summary": delta.get("summary", {}),
            "target_deltas": delta.get("deltas", []),
            "review_recommendations": self.review_recommendations(delta),
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "markdown": str(markdown_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, comparison)
        write_json(latest_path, comparison)
        markdown_path.write_text(self.comparison_markdown(comparison), encoding="utf-8", newline="\n")
        return {"ok": True, "comparison": comparison, "source_gis_modified": False, "mutates_config": False}

    def list_comparisons(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.comparisons_dir.exists():
            return rows
        manifests = sorted(
            self.comparisons_dir.glob("visual_baseline_comparison_*/visual_baseline_comparison_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("visual_baseline_comparison_version") != VISUAL_BASELINE_COMPARISON_VERSION:
                continue
            summary = payload.get("target_delta_summary", {})
            rows.append({
                "comparison_id": payload.get("comparison_id"),
                "created_at": payload.get("created_at"),
                "comparison_readiness": payload.get("comparison_readiness"),
                "baseline_ledger_id": payload.get("baseline_ledger_id"),
                "latest_ledger_id": payload.get("latest_ledger_id"),
                "added_targets": summary.get("added_targets"),
                "removed_targets": summary.get("removed_targets"),
                "changed_targets": summary.get("changed_targets"),
                "download_url": f"/api/visual-baseline-comparison/comparisons/{payload.get('comparison_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, comparison_id: str) -> dict:
        path = self.comparison_dir(comparison_id) / "visual_baseline_comparison_manifest.json"
        if not path.exists() or not self.safe_comparison_path(path):
            return {"ok": False, "error": "visual_baseline_comparison_not_found", "comparison_id": comparison_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "visual_baseline_comparison_not_found", "comparison_id": comparison_id, "source_gis_modified": False}
        return payload

    def output_file(self, comparison_id: str, output_id: str = "markdown") -> dict:
        detail = self.detail(comparison_id)
        if detail.get("error"):
            return detail
        if output_id not in {"markdown", "comparison"}:
            return {"ok": False, "error": "visual_baseline_comparison_output_not_found", "comparison_id": comparison_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_comparison_path(path):
            return {"ok": False, "error": "visual_baseline_comparison_output_not_found", "comparison_id": comparison_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ledger_rows(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.visual_qa_ledger.list_ledgers(limit), [])
        return rows if isinstance(rows, list) else []

    def resolve_ledger(self, ledger_id: str) -> dict:
        if ledger_id:
            detail = safe_call(lambda: self.visual_qa_ledger.detail(ledger_id), {})
            return detail if isinstance(detail, dict) else self.error("visual_qa_ledger_not_found", "Visual QA ledger detail failed.")
        rows = self.ledger_rows(1)
        if not rows:
            return self.error("visual_baseline_comparison_input_missing", "At least one visual QA ledger is required.")
        detail = safe_call(lambda: self.visual_qa_ledger.detail(str(rows[0].get("ledger_id") or "")), {})
        return detail if isinstance(detail, dict) else self.error("visual_qa_ledger_not_found", "Visual QA ledger detail failed.")

    def compare_ledgers(self, baseline: dict, latest: dict) -> dict:
        baseline_items = {str(item.get("target_id") or ""): item for item in baseline.get("qa_items", []) if item.get("target_id")}
        latest_items = {str(item.get("target_id") or ""): item for item in latest.get("qa_items", []) if item.get("target_id")}
        deltas = []
        for target_id in sorted(set(baseline_items) | set(latest_items)):
            base = baseline_items.get(target_id)
            new = latest_items.get(target_id)
            if base is None:
                deltas.append(self.delta_row(target_id, "added", {}, new or {}))
            elif new is None:
                deltas.append(self.delta_row(target_id, "removed", base, {}))
            else:
                changed_fields = self.changed_fields(base, new)
                change_type = "changed" if changed_fields else "unchanged"
                row = self.delta_row(target_id, change_type, base, new)
                row["changed_fields"] = changed_fields
                deltas.append(row)
        summary = {
            "baseline_ledger_id": baseline.get("ledger_id"),
            "latest_ledger_id": latest.get("ledger_id"),
            "baseline_targets": len(baseline_items),
            "latest_targets": len(latest_items),
            "added_targets": len([row for row in deltas if row.get("change_type") == "added"]),
            "removed_targets": len([row for row in deltas if row.get("change_type") == "removed"]),
            "changed_targets": len([row for row in deltas if row.get("change_type") == "changed"]),
            "unchanged_targets": len([row for row in deltas if row.get("change_type") == "unchanged"]),
        }
        return {"summary": summary, "deltas": deltas}

    def changed_fields(self, baseline: dict, latest: dict) -> list[str]:
        fields = ["url", "selector_hint", "expected_text", "capture_status", "review_status", "issue_severity", "recommended_action"]
        return [field for field in fields if str(baseline.get(field) or "") != str(latest.get(field) or "")]

    def delta_row(self, target_id: str, change_type: str, baseline: dict, latest: dict) -> dict:
        return {
            "target_id": target_id,
            "change_type": change_type,
            "baseline_url": baseline.get("url"),
            "latest_url": latest.get("url"),
            "baseline_expected_text": baseline.get("expected_text"),
            "latest_expected_text": latest.get("expected_text"),
            "baseline_review_status": baseline.get("review_status"),
            "latest_review_status": latest.get("review_status"),
            "review_priority": "review_required" if change_type in {"added", "removed", "changed"} else "no_change",
        }

    def review_recommendations(self, delta: dict) -> list[str]:
        summary = delta.get("summary", {})
        recommendations = ["Keep the latest Visual QA ledger as the screenshot capture source for the current release."]
        if int(summary.get("added_targets") or 0):
            recommendations.append("Capture screenshots for added targets before recording the portfolio walkthrough.")
        if int(summary.get("removed_targets") or 0):
            recommendations.append("Confirm removed targets are intentionally absent from the current demo flow.")
        if int(summary.get("changed_targets") or 0):
            recommendations.append("Review changed target URLs, expected text and statuses before sharing the release.")
        if not any(int(summary.get(key) or 0) for key in ["added_targets", "removed_targets", "changed_targets"]):
            recommendations.append("No visual target changes detected; keep this comparison as reproducibility evidence.")
        return recommendations

    def comparison_markdown(self, comparison: dict) -> str:
        summary = comparison.get("target_delta_summary", {})
        lines = [
            "# Visual Baseline Comparison Manifest",
            "",
            f"- Comparison id: `{comparison.get('comparison_id')}`",
            f"- App version: `{comparison.get('app_version')}`",
            f"- Baseline ledger: `{comparison.get('baseline_ledger_id')}`",
            f"- Latest ledger: `{comparison.get('latest_ledger_id')}`",
            f"- Readiness: `{comparison.get('comparison_readiness')}`",
            "",
            "## Delta Summary",
            "",
            f"- Baseline targets: `{summary.get('baseline_targets')}`",
            f"- Latest targets: `{summary.get('latest_targets')}`",
            f"- Added targets: `{summary.get('added_targets')}`",
            f"- Removed targets: `{summary.get('removed_targets')}`",
            f"- Changed targets: `{summary.get('changed_targets')}`",
            f"- Unchanged targets: `{summary.get('unchanged_targets')}`",
            "",
            "## Target Deltas",
            "",
        ]
        for row in comparison.get("target_deltas", []):
            lines.extend([
                f"### {row.get('target_id')}",
                "",
                f"- Change type: `{row.get('change_type')}`",
                f"- Review priority: `{row.get('review_priority')}`",
                f"- Baseline URL: `{row.get('baseline_url')}`",
                f"- Latest URL: `{row.get('latest_url')}`",
                f"- Changed fields: `{', '.join(row.get('changed_fields', []))}`",
                "",
            ])
        lines.extend([
            "## Recommendations",
            "",
        ])
        for item in comparison.get("review_recommendations", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- This comparison reviews generated demo QA metadata only. It is not field verification and not a safety claim.",
            "- Source GIS files remain read-only.",
            "",
        ])
        return "\n".join(lines)

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["visual QA baseline comparison", "target metadata deltas", "review recommendations", "portfolio reproducibility evidence"],
            "not_allowed": ["field verification", "crash prediction", "absolute site judgement"],
            "source_data_rule": "This feature compares generated QA ledgers only; it does not read or mutate source GIS files.",
        }

    def comparison_dir(self, comparison_id: str) -> Path:
        return self.comparisons_dir / safe_token(comparison_id, "missing_comparison", 180)

    def safe_comparison_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.comparisons_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
