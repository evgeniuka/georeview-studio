from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


EXECUTION_RESULT_DIFF_VERSION = "execution_result_diff_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "execution_result_diff") -> str:
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
        return {"error": "execution_result_diff_probe_failed", "detail": repr(exc)}


class ExecutionResultDiffBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        execution_evidence_package: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.execution_evidence_package = execution_evidence_package
        self.expected_api_endpoints = expected_api_endpoints
        self.diffs_dir = output_root / "georeview_studio_execution_result_diffs"

    def status(self) -> dict:
        packages = self.ready_packages(200)
        candidates = self.candidates(200)
        diffs = self.list_diffs(200)
        ready = [row for row in diffs if row.get("diff_readiness") == "ready_for_reviewer"]
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "execution_result_diff_version": EXECUTION_RESULT_DIFF_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "compare_reviewer_ready_execution_evidence_packages",
            "output_dir": str(self.diffs_dir),
            "package_count": len(packages),
            "candidate_pair_count": len(candidates),
            "diff_count": len(diffs),
            "ready_diff_count": len(ready),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_to_compare_execution_packages" if len(packages) >= 2 else "waiting_for_two_ready_execution_packages",
            "diff_dimensions": [
                "lineage",
                "profile_dataset_pilot",
                "workspace_outputs",
                "quality_checks",
                "validation_and_api_evidence",
                "claim_boundaries",
            ],
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def ready_packages(self, limit: int = 20) -> list[dict]:
        rows = safe_call(lambda: self.execution_evidence_package.list_packages(max(1, min(int(limit or 20), 500))), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("package_readiness") == "ready_for_reviewer"]

    def candidates(self, limit: int = 20) -> list[dict]:
        packages = self.ready_packages(max(2, min(int(limit or 20) + 1, 500)))
        rows: list[dict] = []
        for index in range(max(0, len(packages) - 1)):
            left = packages[index]
            right = packages[index + 1]
            rows.append({
                "candidate_id": f"{left.get('package_id')}__vs__{right.get('package_id')}",
                "left_package_id": left.get("package_id"),
                "right_package_id": right.get("package_id"),
                "left_created_at": left.get("created_at"),
                "right_created_at": right.get("created_at"),
                "left_profile_id": left.get("profile_id"),
                "right_profile_id": right.get("profile_id"),
                "left_dataset_id": left.get("dataset_id"),
                "right_dataset_id": right.get("dataset_id"),
                "left_workspace_id": left.get("generated_workspace_id"),
                "right_workspace_id": right.get("generated_workspace_id"),
                "comparison_scope": self.scope_from_rows(left, right),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def create_diff(self, body: dict | None = None) -> dict:
        body = body or {}
        left_id = str(body.get("left_package_id") or body.get("package_id_a") or "").strip()
        right_id = str(body.get("right_package_id") or body.get("package_id_b") or "").strip()
        if not left_id or not right_id:
            candidates = self.candidates(1)
            if not candidates:
                return self.error("execution_result_diff_input_missing", "Two ready package ids are required when no diff candidate pair exists.")
            left_id = str(candidates[0].get("left_package_id") or "")
            right_id = str(candidates[0].get("right_package_id") or "")
        left = safe_call(lambda: self.execution_evidence_package.detail(left_id), {})
        right = safe_call(lambda: self.execution_evidence_package.detail(right_id), {})
        if not isinstance(left, dict) or left.get("error"):
            return {"ok": False, "error": "execution_evidence_package_not_found", "package_id": left_id, "source_gis_modified": False, "mutates_config": False}
        if not isinstance(right, dict) or right.get("error"):
            return {"ok": False, "error": "execution_evidence_package_not_found", "package_id": right_id, "source_gis_modified": False, "mutates_config": False}
        if left.get("package_readiness") != "ready_for_reviewer" or right.get("package_readiness") != "ready_for_reviewer":
            return self.error("execution_result_diff_not_ready", "Both packages must be ready_for_reviewer before diffing.")

        stamp = utc_now()
        diff_id = self.next_diff_id(left, right)
        json_path = self.diff_path(diff_id, ".json")
        md_path = self.diff_path(diff_id, ".md")
        latest_path = self.diffs_dir / "latest_execution_result_diff.json"
        comparison = self.compare_packages(left, right)
        checks = self.diff_quality_checks(left, right, comparison)
        ready = all(item.get("passed") for item in checks)
        diff = {
            "ok": True,
            "execution_result_diff_version": EXECUTION_RESULT_DIFF_VERSION,
            "diff_id": diff_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer-ready diff between execution evidence packages."),
            "app_version": self.app_version,
            "left_package_id": left.get("package_id"),
            "right_package_id": right.get("package_id"),
            "left_execution_id": left.get("execution_id"),
            "right_execution_id": right.get("execution_id"),
            "left_profile_id": left.get("profile_id"),
            "right_profile_id": right.get("profile_id"),
            "left_pilot_osm_id": left.get("pilot_osm_id"),
            "right_pilot_osm_id": right.get("pilot_osm_id"),
            "left_workspace_id": left.get("generated_workspace_id"),
            "right_workspace_id": right.get("generated_workspace_id"),
            "comparison_scope": self.scope_from_packages(left, right),
            "diff_readiness": "ready_for_reviewer" if ready else "diff_needs_review",
            "diff_classification": comparison.get("diff_classification"),
            "comparison": comparison,
            "quality_checks": checks,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)},
        }
        write_json(json_path, diff)
        write_json(latest_path, diff)
        md_path.write_text(self.diff_markdown(diff), encoding="utf-8", newline="\n")
        return {"ok": True, "diff": diff, "source_gis_modified": False, "mutates_config": False}

    def list_diffs(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.diffs_dir.exists():
            return rows
        for path in sorted(self.diffs_dir.glob("execution_result_diff_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("execution_result_diff_version") != EXECUTION_RESULT_DIFF_VERSION:
                continue
            rows.append({
                "diff_id": data.get("diff_id"),
                "created_at": data.get("created_at"),
                "left_package_id": data.get("left_package_id"),
                "right_package_id": data.get("right_package_id"),
                "comparison_scope": data.get("comparison_scope"),
                "diff_classification": data.get("diff_classification"),
                "diff_readiness": data.get("diff_readiness"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, diff_id: str) -> dict:
        path = self.diff_path(diff_id, ".json")
        if not path.exists() or not self.safe_diff_path(path):
            return {"ok": False, "error": "execution_result_diff_not_found", "diff_id": diff_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "execution_result_diff_not_found", "diff_id": diff_id, "source_gis_modified": False}
        return payload

    def output_file(self, diff_id: str, output_id: str = "execution_result_diff") -> dict:
        detail = self.detail(diff_id)
        if detail.get("error"):
            return detail
        if output_id not in {"execution_result_diff", "markdown"}:
            return {"ok": False, "error": "execution_result_diff_output_not_found", "diff_id": diff_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_diff_path(path):
            return {"ok": False, "error": "execution_result_diff_output_not_found", "diff_id": diff_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def compare_packages(self, left: dict, right: dict) -> dict:
        left_tables = self.table_rows(left)
        right_tables = self.table_rows(right)
        table_names = sorted(set(left_tables) | set(right_tables))
        table_diffs = []
        for table in table_names:
            left_rows = left_tables.get(table)
            right_rows = right_tables.get(table)
            delta = None if left_rows is None or right_rows is None else right_rows - left_rows
            table_diffs.append({
                "table": table,
                "left_rows": left_rows,
                "right_rows": right_rows,
                "delta_rows": delta,
                "status": "same" if delta == 0 else "changed",
            })
        left_outputs = set(self.workspace_outputs(left).get("actual_tables", []))
        right_outputs = set(self.workspace_outputs(right).get("actual_tables", []))
        expected_left = set(self.workspace_outputs(left).get("expected_outputs", []))
        expected_right = set(self.workspace_outputs(right).get("expected_outputs", []))
        output_diff = {
            "only_left": sorted(left_outputs - right_outputs),
            "only_right": sorted(right_outputs - left_outputs),
            "shared": sorted(left_outputs & right_outputs),
            "expected_only_left": sorted(expected_left - expected_right),
            "expected_only_right": sorted(expected_right - expected_left),
        }
        quality_left = {row.get("check_id"): row.get("status") for row in left.get("quality_checks", [])}
        quality_right = {row.get("check_id"): row.get("status") for row in right.get("quality_checks", [])}
        quality_diffs = [
            {
                "check_id": check_id,
                "left_status": quality_left.get(check_id),
                "right_status": quality_right.get(check_id),
                "status": "same" if quality_left.get(check_id) == quality_right.get(check_id) else "changed",
            }
            for check_id in sorted(set(quality_left) | set(quality_right))
        ]
        lineage = {
            "same_profile": left.get("profile_id") == right.get("profile_id"),
            "same_dataset": left.get("dataset_id") == right.get("dataset_id"),
            "same_pilot": left.get("pilot_osm_id") == right.get("pilot_osm_id"),
            "same_workspace": left.get("generated_workspace_id") == right.get("generated_workspace_id"),
            "left_created_at": left.get("created_at"),
            "right_created_at": right.get("created_at"),
        }
        row_changes = [row for row in table_diffs if row.get("delta_rows") not in (0, None)]
        output_changes = bool(output_diff["only_left"] or output_diff["only_right"] or output_diff["expected_only_left"] or output_diff["expected_only_right"])
        if lineage["same_profile"] and lineage["same_dataset"] and lineage["same_pilot"] and not row_changes and not output_changes:
            classification = "reproducible_match"
        elif row_changes or output_changes:
            classification = "result_difference_review_needed"
        else:
            classification = "lineage_difference_review"
        return {
            "diff_classification": classification,
            "lineage": lineage,
            "table_diffs": table_diffs,
            "output_diff": output_diff,
            "quality_check_diffs": quality_diffs,
            "validation_diff": {
                "left_checked_endpoints": self.validation(left).get("checked_endpoints"),
                "right_checked_endpoints": self.validation(right).get("checked_endpoints"),
                "left_api_contract_passed": self.validation(left).get("api_contract_passed"),
                "right_api_contract_passed": self.validation(right).get("api_contract_passed"),
            },
            "source_gis_modified": False,
        }

    def diff_quality_checks(self, left: dict, right: dict, comparison: dict) -> list[dict]:
        return [
            self.check("left_package_ready", left.get("package_readiness") == "ready_for_reviewer", {"left_package_readiness": left.get("package_readiness")}),
            self.check("right_package_ready", right.get("package_readiness") == "ready_for_reviewer", {"right_package_readiness": right.get("package_readiness")}),
            self.check("canonical_outputs_comparable", bool(comparison.get("output_diff", {}).get("shared")), comparison.get("output_diff", {})),
            self.check("table_rows_compared", len(comparison.get("table_diffs", [])) >= 1, {"table_diff_count": len(comparison.get("table_diffs", []))}),
            self.check("source_read_only", left.get("source_gis_modified") is False and right.get("source_gis_modified") is False, {"left": left.get("source_gis_modified"), "right": right.get("source_gis_modified")}),
            self.check("claim_boundary_preserved", left.get("approved_review_wording") == self.review_wording and right.get("approved_review_wording") == self.review_wording, {"approved_review_wording": self.review_wording}),
        ]

    @staticmethod
    def check(check_id: str, passed: bool, evidence: dict) -> dict:
        return {"check_id": check_id, "passed": passed, "status": "passed" if passed else "warning", "evidence": evidence}

    @staticmethod
    def workspace_outputs(package: dict) -> dict:
        return package.get("evidence_index", {}).get("workspace_outputs", {}) if isinstance(package.get("evidence_index"), dict) else {}

    @classmethod
    def table_rows(cls, package: dict) -> dict[str, int]:
        outputs = cls.workspace_outputs(package)
        rows: dict[str, int] = {}
        for item in outputs.get("tables", []):
            table = str(item.get("table") or "")
            if not table:
                continue
            try:
                rows[table] = int(item.get("rows") or 0)
            except (TypeError, ValueError):
                rows[table] = 0
        return rows

    @staticmethod
    def validation(package: dict) -> dict:
        return package.get("evidence_index", {}).get("validation_evidence", {}) if isinstance(package.get("evidence_index"), dict) else {}

    @staticmethod
    def scope_from_rows(left: dict, right: dict) -> str:
        if left.get("profile_id") != right.get("profile_id"):
            return "cross_profile"
        if left.get("generated_workspace_id") != right.get("generated_workspace_id"):
            return "cross_workspace_or_pilot"
        return "repeat_execution"

    def scope_from_packages(self, left: dict, right: dict) -> str:
        return self.scope_from_rows(
            {"profile_id": left.get("profile_id"), "generated_workspace_id": left.get("generated_workspace_id")},
            {"profile_id": right.get("profile_id"), "generated_workspace_id": right.get("generated_workspace_id")},
        )

    def diff_markdown(self, diff: dict) -> str:
        comparison = diff.get("comparison", {})
        lines = [
            "# Execution Result Diff",
            "",
            f"Diff: `{diff.get('diff_id')}`",
            f"Created: `{diff.get('created_at')}`",
            f"Readiness: `{diff.get('diff_readiness')}`",
            f"Classification: `{diff.get('diff_classification')}`",
            "",
            "Approved review wording:",
            "",
            f"> {self.review_wording}",
            "",
            "## Compared Packages",
            "",
            f"- Left package: `{diff.get('left_package_id')}`",
            f"- Right package: `{diff.get('right_package_id')}`",
            f"- Scope: `{diff.get('comparison_scope')}`",
            f"- Left workspace: `{diff.get('left_workspace_id')}`",
            f"- Right workspace: `{diff.get('right_workspace_id')}`",
            "",
            "## Lineage",
            "",
        ]
        for key, value in comparison.get("lineage", {}).items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "## Table Diffs", ""])
        for row in comparison.get("table_diffs", []):
            lines.append(f"- `{row.get('table')}`: left `{row.get('left_rows')}`, right `{row.get('right_rows')}`, delta `{row.get('delta_rows')}`, status `{row.get('status')}`")
        lines.extend(["", "## Output Set Diff", ""])
        output_diff = comparison.get("output_diff", {})
        for key in ["only_left", "only_right", "shared", "expected_only_left", "expected_only_right"]:
            lines.append(f"- `{key}`: `{', '.join(output_diff.get(key, []))}`")
        lines.extend(["", "## Quality Checks", ""])
        for check in diff.get("quality_checks", []):
            lines.append(f"- `{check.get('check_id')}`: `{check.get('status')}`")
        lines.extend(["", "## Boundaries", ""])
        for item in self.claim_boundaries():
            lines.append(f"- {item}")
        lines.extend(["", "Source GIS modified: `false`", "Config mutated: `false`", ""])
        return "\n".join(lines)

    def claim_boundaries(self) -> list[str]:
        return [
            "Execution result diffing compares generated evidence packages; it does not claim real-world safety outcomes.",
            "A reproducible match means package evidence is consistent, not that it proves real-world safety outcomes.",
            "Differences are review prompts for engineering and data-quality investigation.",
            "Source GIS files remain read-only; diffs write JSON/Markdown artifacts under analysis_output only.",
            self.review_wording,
        ]

    def diff_path(self, diff_id: str, suffix: str) -> Path:
        return self.diffs_dir / f"{safe_token(diff_id)}{suffix}"

    def safe_diff_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.diffs_dir.resolve())
            return True
        except ValueError:
            return False

    def next_diff_id(self, left: dict, right: dict) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"execution_result_diff_{safe_token(left.get('profile_id'))}_{safe_token(right.get('profile_id'))}_{safe_token(stamp)}"

    def error(self, error: str, detail: str) -> dict:
        return {"ok": False, "error": error, "detail": detail, "source_gis_modified": False, "mutates_config": False}
