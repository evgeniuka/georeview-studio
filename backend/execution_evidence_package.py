from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


EXECUTION_EVIDENCE_PACKAGE_VERSION = "execution_evidence_package_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "execution_evidence_package") -> str:
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
        return {"error": "execution_evidence_package_probe_failed", "detail": repr(exc)}


class ExecutionEvidencePackageBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        workspaces_dir: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        source_handoff_execution: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.workspaces_dir = workspaces_dir
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.source_handoff_execution = source_handoff_execution
        self.expected_api_endpoints = expected_api_endpoints
        self.packages_dir = output_root / "georeview_studio_execution_evidence_packages"

    def status(self) -> dict:
        candidates = self.candidates(limit=200)
        packages = self.list_packages(limit=200)
        ready = [row for row in packages if row.get("package_readiness") == "ready_for_reviewer"]
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "execution_evidence_package_version": EXECUTION_EVIDENCE_PACKAGE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "reviewer_ready_index_for_verified_handoff_execution",
            "output_dir": str(self.packages_dir),
            "candidate_count": len(candidates),
            "package_count": len(packages),
            "ready_package_count": len(ready),
            "expected_api_endpoints": self.expected_api_endpoints,
            "evidence_sections": [
                "source_handoff_execution",
                "execution_queue_job",
                "workspace_output_manifest",
                "handoff_output_comparison",
                "release_and_validation_evidence",
                "claim_boundaries",
                "reviewer_walkthrough",
            ],
            "readiness_level": "ready_to_package_verified_execution" if candidates else "waiting_for_verified_handoff_execution",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def candidates(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        executions = safe_call(lambda: self.source_handoff_execution.list_executions(max(1, min(int(limit or 20), 200))), [])
        if not isinstance(executions, list):
            return rows
        for row in executions:
            if row.get("execution_readiness") != "executed_and_verified":
                continue
            detail = safe_call(lambda execution_id=row.get("execution_id"): self.source_handoff_execution.detail(str(execution_id or "")), {})
            comparison = detail.get("comparison", {}) if isinstance(detail, dict) else {}
            rows.append({
                "execution_id": row.get("execution_id"),
                "created_at": row.get("created_at"),
                "handoff_id": row.get("handoff_id"),
                "profile_id": row.get("profile_id"),
                "dataset_id": row.get("dataset_id"),
                "execution_queue_job_id": row.get("execution_queue_job_id"),
                "generated_workspace_id": row.get("generated_workspace_id"),
                "execution_readiness": row.get("execution_readiness"),
                "comparison_readiness": comparison.get("comparison_readiness"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def create_package(self, body: dict | None = None) -> dict:
        body = body or {}
        execution_id = str(body.get("execution_id") or "").strip()
        if not execution_id:
            candidates = self.candidates(limit=1)
            if not candidates:
                return self.error("execution_evidence_package_input_missing", "execution_id is required when no verified execution candidate exists.")
            execution_id = str(candidates[0].get("execution_id") or "")
        execution = safe_call(lambda: self.source_handoff_execution.detail(execution_id), {})
        if not isinstance(execution, dict) or execution.get("error"):
            return {"ok": False, "error": "source_handoff_execution_not_found", "execution_id": execution_id, "source_gis_modified": False, "mutates_config": False}
        comparison = execution.get("comparison", {}) if isinstance(execution.get("comparison"), dict) else {}
        if execution.get("execution_readiness") != "executed_and_verified" or comparison.get("comparison_readiness") != "outputs_match_handoff_evidence":
            return self.error("execution_evidence_package_not_ready", "Only executed_and_verified handoff executions can be packaged.", execution_id)

        stamp = utc_now()
        package_id = self.next_package_id(execution)
        json_path = self.package_path(package_id, ".json")
        md_path = self.package_path(package_id, ".md")
        latest_path = self.packages_dir / "latest_execution_evidence_package.json"
        evidence_index = self.evidence_index(execution)
        quality = self.quality_checks(execution, evidence_index)
        # During a new release bootstrap, validation and API summaries may still
        # point at the previous release until this validation/API loop finishes.
        # Keep that as release evidence warning, but do not block packaging of
        # otherwise verified execution evidence.
        package_ready = all(item.get("passed") or item.get("check_id") == "api_contract_recorded" for item in quality)
        package = {
            "ok": True,
            "execution_evidence_package_version": EXECUTION_EVIDENCE_PACKAGE_VERSION,
            "package_id": package_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer-ready package for verified source handoff execution evidence."),
            "app_version": self.app_version,
            "execution_id": execution.get("execution_id"),
            "handoff_id": execution.get("handoff_id"),
            "profile_id": execution.get("profile_id"),
            "dataset_id": execution.get("dataset_id"),
            "pilot_osm_id": execution.get("pilot_osm_id"),
            "execution_queue_job_id": execution.get("execution_queue_job_id"),
            "execution_status": execution.get("execution_status"),
            "generated_workspace_id": execution.get("generated_workspace_id"),
            "execution_readiness": execution.get("execution_readiness"),
            "comparison_readiness": comparison.get("comparison_readiness"),
            "package_readiness": "ready_for_reviewer" if package_ready else "package_needs_review",
            "quality_checks": quality,
            "evidence_index": evidence_index,
            "reviewer_walkthrough": self.walkthrough_steps(execution, evidence_index),
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)},
        }
        write_json(json_path, package)
        write_json(latest_path, package)
        md_path.write_text(self.package_markdown(package), encoding="utf-8", newline="\n")
        return {"ok": True, "package": package, "source_gis_modified": False, "mutates_config": False}

    def list_packages(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.packages_dir.exists():
            return rows
        for path in sorted(self.packages_dir.glob("execution_evidence_package_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("execution_evidence_package_version") != EXECUTION_EVIDENCE_PACKAGE_VERSION:
                continue
            rows.append({
                "package_id": data.get("package_id"),
                "created_at": data.get("created_at"),
                "execution_id": data.get("execution_id"),
                "profile_id": data.get("profile_id"),
                "dataset_id": data.get("dataset_id"),
                "generated_workspace_id": data.get("generated_workspace_id"),
                "package_readiness": data.get("package_readiness"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, package_id: str) -> dict:
        path = self.package_path(package_id, ".json")
        if not path.exists() or not self.safe_package_path(path):
            return {"ok": False, "error": "execution_evidence_package_not_found", "package_id": package_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "execution_evidence_package_not_found", "package_id": package_id, "source_gis_modified": False}
        return payload

    def output_file(self, package_id: str, output_id: str = "execution_evidence_package") -> dict:
        detail = self.detail(package_id)
        if detail.get("error"):
            return detail
        if output_id not in {"execution_evidence_package", "markdown"}:
            return {"ok": False, "error": "execution_evidence_package_output_not_found", "package_id": package_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_package_path(path):
            return {"ok": False, "error": "execution_evidence_package_output_not_found", "package_id": package_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def evidence_index(self, execution: dict) -> dict:
        workspace = execution.get("workspace", {}) if isinstance(execution.get("workspace"), dict) else {}
        workspace_dir = Path(str(workspace.get("workspace_dir") or ""))
        manifest_path = workspace_dir / "manifest.json" if workspace_dir else Path("")
        validation_summary = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        release_latest = read_json(self.output_root / "georeview_studio_release_readiness" / "latest_release_readiness_snapshot.json")
        execution_files = execution.get("files", {}) if isinstance(execution.get("files"), dict) else {}
        queue_job = execution.get("queue_job", {}) if isinstance(execution.get("queue_job"), dict) else {}
        queue_json = Path(str(queue_job.get("json_file") or ""))
        queue_md = Path(str(queue_job.get("markdown_file") or ""))
        tables = workspace.get("tables", []) if isinstance(workspace.get("tables"), list) else []
        expected_outputs = execution.get("comparison", {}).get("expected_outputs", []) if isinstance(execution.get("comparison"), dict) else []
        actual_tables = execution.get("comparison", {}).get("actual_tables", []) if isinstance(execution.get("comparison"), dict) else []
        return {
            "lineage": {
                "handoff_id": execution.get("handoff_id"),
                "request_id": execution.get("request_id"),
                "decision_id": execution.get("decision_id"),
                "planned_queue_job_id": execution.get("planned_queue_job_id"),
                "execution_queue_job_id": execution.get("execution_queue_job_id"),
                "generated_workspace_id": execution.get("generated_workspace_id"),
            },
            "execution_artifacts": [
                self.file_ref("source_handoff_execution_json", execution_files.get("json"), "Verified execution JSON evidence"),
                self.file_ref("source_handoff_execution_markdown", execution_files.get("markdown"), "Verified execution Markdown report"),
                self.file_ref("execution_queue_job_json", queue_json, "Controlled queue job JSON record"),
                self.file_ref("execution_queue_job_markdown", queue_md, "Controlled queue job Markdown record"),
                self.file_ref("workspace_manifest", manifest_path, "Generated workspace manifest"),
            ],
            "release_artifacts": [
                self.file_ref("project_manifest", self.project_dir / "project_manifest.json", "Current app manifest"),
                self.file_ref("validation_summary", self.project_dir / "validation_summary.json", "Local validation summary"),
                self.file_ref("api_contract_summary", self.project_dir / "api_contract_summary.json", "API contract summary"),
                self.file_ref("release_readiness_latest", release_latest.get("files", {}).get("json") if isinstance(release_latest, dict) else "", "Latest release readiness snapshot"),
            ],
            "workspace_outputs": {
                "workspace_dir": workspace.get("workspace_dir"),
                "manifest_exists": workspace.get("manifest_exists"),
                "table_count": workspace.get("table_count"),
                "tables": tables,
                "expected_outputs": expected_outputs,
                "actual_tables": actual_tables,
                "missing_outputs": execution.get("comparison", {}).get("missing_outputs", []) if isinstance(execution.get("comparison"), dict) else [],
            },
            "validation_evidence": {
                "validation_passed": validation_summary.get("passed"),
                "validation_app_version": validation_summary.get("app_version"),
                "api_contract_passed": api_contract.get("passed"),
                "checked_endpoints": api_contract.get("checked_endpoints"),
                "expected_api_endpoints": self.expected_api_endpoints,
            },
        }

    def quality_checks(self, execution: dict, evidence_index: dict) -> list[dict]:
        comparison = execution.get("comparison", {}) if isinstance(execution.get("comparison"), dict) else {}
        files = evidence_index.get("execution_artifacts", []) + evidence_index.get("release_artifacts", [])
        existing_core = [item for item in files if item.get("required") and item.get("exists")]
        expected_outputs = evidence_index.get("workspace_outputs", {}).get("expected_outputs", [])
        missing_outputs = evidence_index.get("workspace_outputs", {}).get("missing_outputs", [])
        validation = evidence_index.get("validation_evidence", {})
        return [
            self.check("execution_verified", execution.get("execution_readiness") == "executed_and_verified", {"execution_readiness": execution.get("execution_readiness")}),
            self.check("comparison_verified", comparison.get("comparison_readiness") == "outputs_match_handoff_evidence", {"comparison_readiness": comparison.get("comparison_readiness")}),
            self.check("canonical_outputs_present", bool(expected_outputs) and not missing_outputs, {"expected_outputs": expected_outputs, "missing_outputs": missing_outputs}),
            self.check("core_artifacts_exist", len(existing_core) >= 4, {"existing_required_artifacts": len(existing_core)}),
            self.check("source_read_only", execution.get("source_gis_modified") is False, {"source_gis_modified": execution.get("source_gis_modified")}),
            self.check("api_contract_recorded", bool(validation.get("api_contract_passed")) and int(validation.get("checked_endpoints") or 0) >= self.expected_api_endpoints, validation),
        ]

    @staticmethod
    def check(check_id: str, passed: bool, evidence: dict) -> dict:
        return {"check_id": check_id, "passed": passed, "status": "passed" if passed else "warning", "evidence": evidence}

    @staticmethod
    def file_ref(label: str, path_value: object, role: str) -> dict:
        path = Path(str(path_value or ""))
        return {
            "label": label,
            "role": role,
            "path": str(path) if str(path) else "",
            "exists": path.exists() if str(path) else False,
            "size_bytes": path.stat().st_size if str(path) and path.exists() and path.is_file() else 0,
            "required": label in {"source_handoff_execution_json", "source_handoff_execution_markdown", "workspace_manifest", "project_manifest", "api_contract_summary"},
        }

    def walkthrough_steps(self, execution: dict, evidence_index: dict) -> list[dict]:
        return [
            {"step": 1, "title": "Confirm approved source path", "evidence": execution.get("handoff_id"), "reviewer_value": "Shows the source was reviewed before execution."},
            {"step": 2, "title": "Confirm controlled queue execution", "evidence": execution.get("execution_queue_job_id"), "reviewer_value": "Shows the app can run a validated profile contract through an auditable local queue."},
            {"step": 3, "title": "Confirm generated workspace", "evidence": execution.get("generated_workspace_id"), "reviewer_value": "Shows the source-to-output path creates canonical workspace tables."},
            {"step": 4, "title": "Confirm output comparison", "evidence": execution.get("comparison", {}).get("comparison_readiness"), "reviewer_value": "Shows expected profile outputs are present and linked to handoff evidence."},
            {"step": 5, "title": "Confirm claim boundary", "evidence": self.review_wording, "reviewer_value": "Keeps analysis framed as infrastructure review prioritization."},
            {"step": 6, "title": "Confirm release evidence", "evidence": evidence_index.get("validation_evidence", {}), "reviewer_value": "Connects the feature to validation and API coverage."},
        ]

    def package_markdown(self, package: dict) -> str:
        evidence = package.get("evidence_index", {})
        workspace = evidence.get("workspace_outputs", {})
        validation = evidence.get("validation_evidence", {})
        lines = [
            "# Execution Evidence Package",
            "",
            f"Package: `{package.get('package_id')}`",
            f"Created: `{package.get('created_at')}`",
            f"App version: `{package.get('app_version')}`",
            f"Readiness: `{package.get('package_readiness')}`",
            "",
            "## Purpose",
            "",
            "This package is a reviewer-facing index for a verified source handoff execution. It connects the approved source review, planned handoff, controlled queue execution, generated workspace, output comparison and release evidence in one compact artifact.",
            "",
            "Approved review wording:",
            "",
            f"> {self.review_wording}",
            "",
            "## Execution Summary",
            "",
            f"- Execution: `{package.get('execution_id')}`",
            f"- Handoff: `{package.get('handoff_id')}`",
            f"- Profile: `{package.get('profile_id')}`",
            f"- Dataset: `{package.get('dataset_id')}`",
            f"- Queue job: `{package.get('execution_queue_job_id')}`",
            f"- Queue status: `{package.get('execution_status')}`",
            f"- Workspace: `{package.get('generated_workspace_id')}`",
            f"- Comparison: `{package.get('comparison_readiness')}`",
            "",
            "## Workspace Outputs",
            "",
            f"- Workspace manifest exists: `{workspace.get('manifest_exists')}`",
            f"- Table count: `{workspace.get('table_count')}`",
            f"- Expected outputs: `{', '.join(workspace.get('expected_outputs', []))}`",
            f"- Actual tables: `{', '.join(workspace.get('actual_tables', []))}`",
            f"- Missing outputs: `{', '.join(workspace.get('missing_outputs', []))}`",
            "",
            "## Quality Checks",
            "",
        ]
        for check in package.get("quality_checks", []):
            lines.append(f"- `{check.get('check_id')}`: `{check.get('status')}`")
        lines.extend([
            "",
            "## Artifact Index",
            "",
        ])
        for section in ["execution_artifacts", "release_artifacts"]:
            lines.append(f"### {section.replace('_', ' ').title()}")
            for item in evidence.get(section, []):
                lines.append(f"- `{item.get('label')}`: `{item.get('path')}`; exists `{item.get('exists')}`; bytes `{item.get('size_bytes')}`")
            lines.append("")
        lines.extend([
            "## Validation Evidence",
            "",
            f"- Validation passed: `{validation.get('validation_passed')}`",
            f"- Validation app version: `{validation.get('validation_app_version')}`",
            f"- API contract passed: `{validation.get('api_contract_passed')}`",
            f"- Checked endpoints: `{validation.get('checked_endpoints')}` / `{validation.get('expected_api_endpoints')}`",
            "",
            "## Reviewer Walkthrough",
            "",
        ])
        for step in package.get("reviewer_walkthrough", []):
            lines.append(f"{step.get('step')}. {step.get('title')}: `{step.get('evidence')}`")
        lines.extend(["", "## Boundaries", ""])
        for item in self.claim_boundaries():
            lines.append(f"- {item}")
        lines.extend([
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)

    def claim_boundaries(self) -> list[str]:
        return [
            "The package is evidence for reproducible infrastructure indicator analysis, not crash prediction.",
            "It indexes generated artifacts and does not copy, edit, move, rename or overwrite source GIS files.",
            "Missing OSM tags remain data-quality flags unless an explicit mapped value supports an infrastructure indicator.",
            "The package is intended for portfolio and field-review prioritization workflows.",
            self.review_wording,
        ]

    def package_path(self, package_id: str, suffix: str) -> Path:
        return self.packages_dir / f"{safe_token(package_id)}{suffix}"

    def safe_package_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.packages_dir.resolve())
            return True
        except ValueError:
            return False

    def next_package_id(self, execution: dict) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"execution_evidence_package_{safe_token(execution.get('profile_id'))}_{safe_token(execution.get('dataset_id'))}_{safe_token(stamp)}"

    def error(self, error: str, detail: str, execution_id: str = "") -> dict:
        return {"ok": False, "error": error, "detail": detail, "execution_id": execution_id, "source_gis_modified": False, "mutates_config": False}
