from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


EXECUTION_DIFF_DETAIL_VERSION = "execution_diff_detail_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "execution_diff_detail") -> str:
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
        return {"error": "execution_diff_detail_probe_failed", "detail": repr(exc)}


class ExecutionDiffDetailDrilldownBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        execution_result_diff: object,
        execution_diff_gallery: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.execution_result_diff = execution_result_diff
        self.execution_diff_gallery = execution_diff_gallery
        self.expected_api_endpoints = expected_api_endpoints
        self.details_dir = output_root / "georeview_studio_execution_diff_details"

    def status(self) -> dict:
        baselines = self.baselines(limit=500)
        details = self.list_drilldowns(limit=500)
        ready_details = [row for row in details if row.get("drilldown_readiness") == "ready_for_reviewer"]
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "execution_diff_detail_version": EXECUTION_DIFF_DETAIL_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "select_baseline_and_inspect_execution_diff_detail",
            "output_dir": str(self.details_dir),
            "baseline_candidate_count": len(baselines),
            "preferred_baseline_id": baselines[0].get("diff_id") if baselines else "",
            "detail_count": len(details),
            "ready_detail_count": len(ready_details),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_diff_drilldown" if baselines else "waiting_for_diff_gallery_items",
            "drilldown_dimensions": [
                "baseline_selection",
                "lineage",
                "table_row_deltas",
                "output_set_delta",
                "quality_check_delta",
                "validation_evidence",
                "review_actions",
            ],
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def baselines(self, limit: int = 20) -> list[dict]:
        gallery_items = safe_call(lambda: self.execution_diff_gallery.items(limit=500), [])
        if not isinstance(gallery_items, list):
            return []
        rows = []
        for item in gallery_items:
            score = self.baseline_score(item)
            rows.append({
                "diff_id": item.get("diff_id"),
                "created_at": item.get("created_at"),
                "baseline_score": score,
                "baseline_role": "preferred" if score >= 90 else "candidate",
                "diff_classification": item.get("diff_classification"),
                "comparison_scope": item.get("comparison_scope"),
                "diff_readiness": item.get("diff_readiness"),
                "row_change_count": item.get("row_change_count", 0),
                "output_delta_count": item.get("output_delta_count", 0),
                "quality_warning_count": item.get("quality_warning_count", 0),
                "portfolio_label": item.get("portfolio_label"),
                "reason": self.baseline_reason(item, score),
                "source_gis_modified": False,
                "mutates_config": False,
            })
        rows.sort(key=lambda row: (row.get("baseline_score", 0), str(row.get("created_at") or "")), reverse=True)
        return rows[: max(1, min(int(limit or 20), 500))]

    def inspect_diff(self, diff_id: str = "", baseline_diff_id: str = "") -> dict:
        target_id = str(diff_id or "").strip()
        baselines = self.baselines(limit=500)
        if not target_id:
            if not baselines:
                return self.error("execution_diff_detail_input_missing", "A diff_id is required when no baseline candidate exists.")
            target_id = str(baselines[0].get("diff_id") or "")
        baseline_id = str(baseline_diff_id or "").strip() or (str(baselines[0].get("diff_id") or "") if baselines else target_id)
        target = safe_call(lambda: self.execution_result_diff.detail(target_id), {})
        if not isinstance(target, dict) or target.get("error"):
            return {"ok": False, "error": "execution_result_diff_not_found", "diff_id": target_id, "source_gis_modified": False}
        baseline = safe_call(lambda: self.execution_result_diff.detail(baseline_id), {})
        if not isinstance(baseline, dict) or baseline.get("error"):
            baseline = target
            baseline_id = target_id
        return {
            "ok": True,
            "execution_diff_detail_version": EXECUTION_DIFF_DETAIL_VERSION,
            "app_version": self.app_version,
            "diff_id": target_id,
            "baseline_diff_id": baseline_id,
            "drilldown": self.build_drilldown(target, baseline),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_drilldown(self, body: dict | None = None) -> dict:
        body = body or {}
        inspected = self.inspect_diff(str(body.get("diff_id") or ""), str(body.get("baseline_diff_id") or ""))
        if inspected.get("error"):
            return inspected
        drilldown = inspected.get("drilldown", {})
        if not drilldown:
            return self.error("execution_diff_detail_not_ready", "Diff detail drilldown could not be built from the selected diff.")
        target = drilldown.get("selected_diff", {})
        stamp = utc_now()
        detail_id = f"execution_diff_detail_{safe_token(target.get('diff_id'))}_{safe_token(stamp.replace(':', '_'))}"
        json_path = self.detail_path(detail_id, ".json")
        md_path = self.detail_path(detail_id, ".md")
        latest_path = self.details_dir / "latest_execution_diff_detail.json"
        ready = target.get("diff_readiness") == "ready_for_reviewer" and bool(drilldown.get("table_breakdown"))
        artifact = {
            "ok": True,
            "execution_diff_detail_version": EXECUTION_DIFF_DETAIL_VERSION,
            "detail_id": detail_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer-facing drilldown for one execution result diff."),
            "app_version": self.app_version,
            "diff_id": target.get("diff_id"),
            "baseline_diff_id": drilldown.get("baseline_diff", {}).get("diff_id"),
            "drilldown_readiness": "ready_for_reviewer" if ready else "needs_diff_review",
            "drilldown": drilldown,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)},
        }
        write_json(json_path, artifact)
        write_json(latest_path, artifact)
        md_path.write_text(self.drilldown_markdown(artifact), encoding="utf-8", newline="\n")
        return {"ok": True, "detail": artifact, "source_gis_modified": False, "mutates_config": False}

    def list_drilldowns(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.details_dir.exists():
            return rows
        for path in sorted(self.details_dir.glob("execution_diff_detail_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("execution_diff_detail_version") != EXECUTION_DIFF_DETAIL_VERSION:
                continue
            drilldown = data.get("drilldown", {}) if isinstance(data.get("drilldown"), dict) else {}
            rows.append({
                "detail_id": data.get("detail_id"),
                "created_at": data.get("created_at"),
                "diff_id": data.get("diff_id"),
                "baseline_diff_id": data.get("baseline_diff_id"),
                "drilldown_readiness": data.get("drilldown_readiness"),
                "changed_table_count": drilldown.get("changed_table_count"),
                "output_delta_count": drilldown.get("output_delta_count"),
                "review_action_count": len(drilldown.get("review_actions", [])) if isinstance(drilldown.get("review_actions"), list) else 0,
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, detail_id: str) -> dict:
        path = self.detail_path(detail_id, ".json")
        if not path.exists() or not self.safe_detail_path(path):
            return {"ok": False, "error": "execution_diff_detail_not_found", "detail_id": detail_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "execution_diff_detail_not_found", "detail_id": detail_id, "source_gis_modified": False}
        return payload

    def output_file(self, detail_id: str, output_id: str = "execution_diff_detail") -> dict:
        detail = self.detail(detail_id)
        if detail.get("error"):
            return detail
        if output_id not in {"execution_diff_detail", "markdown"}:
            return {"ok": False, "error": "execution_diff_detail_output_not_found", "detail_id": detail_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_detail_path(path):
            return {"ok": False, "error": "execution_diff_detail_output_not_found", "detail_id": detail_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def build_drilldown(self, target: dict, baseline: dict) -> dict:
        comparison = target.get("comparison", {}) if isinstance(target.get("comparison"), dict) else {}
        baseline_comparison = baseline.get("comparison", {}) if isinstance(baseline.get("comparison"), dict) else {}
        table_breakdown = self.table_breakdown(comparison.get("table_diffs", []))
        output_breakdown = self.output_breakdown(comparison.get("output_diff", {}))
        quality_breakdown = self.quality_breakdown(comparison.get("quality_check_diffs", []), target.get("quality_checks", []))
        selected_summary = self.diff_summary(target)
        baseline_summary = self.diff_summary(baseline)
        return {
            "selected_diff": selected_summary,
            "baseline_diff": baseline_summary,
            "baseline_relation": "same_diff" if selected_summary.get("diff_id") == baseline_summary.get("diff_id") else "compared_to_baseline",
            "baseline_comparison": self.compare_summaries(selected_summary, baseline_summary),
            "lineage": comparison.get("lineage", {}),
            "table_breakdown": table_breakdown,
            "changed_table_count": len([row for row in table_breakdown if row.get("status") == "changed"]),
            "output_breakdown": output_breakdown,
            "output_delta_count": sum(len(output_breakdown.get(key, [])) for key in ["only_left", "only_right", "expected_only_left", "expected_only_right"]),
            "quality_breakdown": quality_breakdown,
            "validation_evidence": comparison.get("validation_diff", {}),
            "review_actions": self.review_actions(selected_summary, table_breakdown, output_breakdown, quality_breakdown),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    @staticmethod
    def table_breakdown(rows: object) -> list[dict]:
        result = []
        if not isinstance(rows, list):
            return result
        for row in rows:
            result.append({
                "table": row.get("table"),
                "left_rows": row.get("left_rows"),
                "right_rows": row.get("right_rows"),
                "delta_rows": row.get("delta_rows"),
                "status": row.get("status"),
                "review_note": "row counts match" if row.get("status") == "same" else "row count changed; inspect source and runner evidence",
            })
        return result

    @staticmethod
    def output_breakdown(output_diff: object) -> dict:
        if not isinstance(output_diff, dict):
            output_diff = {}
        return {
            "only_left": list(output_diff.get("only_left", [])),
            "only_right": list(output_diff.get("only_right", [])),
            "shared": list(output_diff.get("shared", [])),
            "expected_only_left": list(output_diff.get("expected_only_left", [])),
            "expected_only_right": list(output_diff.get("expected_only_right", [])),
        }

    @staticmethod
    def quality_breakdown(quality_diffs: object, checks: object) -> list[dict]:
        rows = []
        if isinstance(quality_diffs, list):
            for row in quality_diffs:
                rows.append({
                    "check_id": row.get("check_id"),
                    "left_status": row.get("left_status"),
                    "right_status": row.get("right_status"),
                    "status": row.get("status"),
                    "review_note": "quality status matches" if row.get("status") == "same" else "quality status changed",
                })
        if not rows and isinstance(checks, list):
            for row in checks:
                rows.append({
                    "check_id": row.get("check_id"),
                    "left_status": row.get("status"),
                    "right_status": row.get("status"),
                    "status": row.get("status"),
                    "review_note": "artifact-level quality check",
                })
        return rows

    def diff_summary(self, detail: dict) -> dict:
        comparison = detail.get("comparison", {}) if isinstance(detail.get("comparison"), dict) else {}
        table_rows = comparison.get("table_diffs", []) if isinstance(comparison.get("table_diffs"), list) else []
        output_diff = comparison.get("output_diff", {}) if isinstance(comparison.get("output_diff"), dict) else {}
        return {
            "diff_id": detail.get("diff_id"),
            "created_at": detail.get("created_at"),
            "diff_readiness": detail.get("diff_readiness"),
            "diff_classification": detail.get("diff_classification"),
            "comparison_scope": detail.get("comparison_scope"),
            "left_package_id": detail.get("left_package_id"),
            "right_package_id": detail.get("right_package_id"),
            "left_workspace_id": detail.get("left_workspace_id"),
            "right_workspace_id": detail.get("right_workspace_id"),
            "table_count": len(table_rows),
            "changed_table_count": len([row for row in table_rows if row.get("status") == "changed"]),
            "output_delta_count": sum(len(output_diff.get(key, [])) for key in ["only_left", "only_right", "expected_only_left", "expected_only_right"]),
        }

    @staticmethod
    def compare_summaries(selected: dict, baseline: dict) -> dict:
        return {
            "same_diff": selected.get("diff_id") == baseline.get("diff_id"),
            "same_classification": selected.get("diff_classification") == baseline.get("diff_classification"),
            "same_scope": selected.get("comparison_scope") == baseline.get("comparison_scope"),
            "changed_table_delta": (selected.get("changed_table_count") or 0) - (baseline.get("changed_table_count") or 0),
            "output_delta_delta": (selected.get("output_delta_count") or 0) - (baseline.get("output_delta_count") or 0),
        }

    def review_actions(self, summary: dict, table_rows: list[dict], output_diff: dict, quality_rows: list[dict]) -> list[str]:
        actions = []
        if summary.get("diff_classification") == "reproducible_match":
            actions.append("Use this diff as reproducibility evidence for generated outputs.")
        else:
            actions.append("Review lineage, table deltas and output set differences before sharing.")
        if any(row.get("status") == "changed" for row in table_rows):
            actions.append("Inspect changed table row counts against package lineage and source handoff evidence.")
        if output_diff.get("only_left") or output_diff.get("only_right"):
            actions.append("Check whether output files were added or dropped between executions.")
        if any(row.get("status") not in {"same", "passed"} for row in quality_rows):
            actions.append("Review quality-check deltas before using this diff as portfolio evidence.")
        actions.append("Keep infrastructure indicator wording separate from real-world safety outcome claims.")
        return actions

    @staticmethod
    def baseline_score(item: dict) -> int:
        score = 0
        if item.get("diff_readiness") == "ready_for_reviewer":
            score += 30
        if item.get("diff_classification") == "reproducible_match":
            score += 30
        if item.get("comparison_scope") == "repeat_execution":
            score += 20
        if int(item.get("row_change_count") or 0) == 0:
            score += 10
        if int(item.get("output_delta_count") or 0) == 0:
            score += 10
        return score

    @staticmethod
    def baseline_reason(item: dict, score: int) -> str:
        if score >= 90:
            return "ready reproducible repeat execution with no table or output deltas"
        if item.get("diff_readiness") == "ready_for_reviewer":
            return "ready diff evidence candidate"
        return "candidate needs review before baseline use"

    def drilldown_markdown(self, artifact: dict) -> str:
        drilldown = artifact.get("drilldown", {})
        selected = drilldown.get("selected_diff", {})
        baseline = drilldown.get("baseline_diff", {})
        lines = [
            "# Execution Diff Detail Drilldown",
            "",
            f"Detail: `{artifact.get('detail_id')}`",
            f"Created: `{artifact.get('created_at')}`",
            f"Readiness: `{artifact.get('drilldown_readiness')}`",
            f"Selected diff: `{selected.get('diff_id')}`",
            f"Baseline diff: `{baseline.get('diff_id')}`",
            "",
            "Approved review wording:",
            "",
            f"> {self.review_wording}",
            "",
            "## Selected Diff",
            "",
            f"- Classification: `{selected.get('diff_classification')}`",
            f"- Scope: `{selected.get('comparison_scope')}`",
            f"- Changed tables: `{selected.get('changed_table_count')}`",
            f"- Output deltas: `{selected.get('output_delta_count')}`",
            "",
            "## Baseline Comparison",
            "",
        ]
        for key, value in drilldown.get("baseline_comparison", {}).items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "## Table Breakdown", ""])
        for row in drilldown.get("table_breakdown", []):
            lines.append(f"- `{row.get('table')}`: left `{row.get('left_rows')}`, right `{row.get('right_rows')}`, delta `{row.get('delta_rows')}`, status `{row.get('status')}` - {row.get('review_note')}")
        lines.extend(["", "## Output Breakdown", ""])
        output = drilldown.get("output_breakdown", {})
        for key in ["only_left", "only_right", "shared", "expected_only_left", "expected_only_right"]:
            lines.append(f"- `{key}`: `{', '.join(output.get(key, []))}`")
        lines.extend(["", "## Quality Breakdown", ""])
        for row in drilldown.get("quality_breakdown", []):
            lines.append(f"- `{row.get('check_id')}`: left `{row.get('left_status')}`, right `{row.get('right_status')}`, status `{row.get('status')}`")
        lines.extend(["", "## Review Actions", ""])
        for action in drilldown.get("review_actions", []):
            lines.append(f"- {action}")
        lines.extend(["", "## Boundaries", ""])
        for item in self.claim_boundaries():
            lines.append(f"- {item}")
        lines.extend(["", "Source GIS modified: `false`", "Config mutated: `false`", ""])
        return "\n".join(lines)

    def claim_boundaries(self) -> list[str]:
        return [
            "Diff drilldown is engineering evidence about generated artifacts, not crash prediction.",
            "A selected baseline supports reproducibility review only.",
            "Changed tables or outputs are investigation prompts, not field conclusions.",
            "Source GIS files remain read-only; drilldown artifacts are written under analysis_output only.",
            self.review_wording,
        ]

    def detail_path(self, detail_id: str, suffix: str) -> Path:
        return self.details_dir / f"{safe_token(detail_id)}{suffix}"

    def safe_detail_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.details_dir.resolve())
            return True
        except ValueError:
            return False

    def error(self, error: str, detail: str) -> dict:
        return {"ok": False, "error": error, "detail": detail, "source_gis_modified": False, "mutates_config": False}
