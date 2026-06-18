from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


DEMO_ARTIFACT_COMPLETENESS_VERSION = "demo_artifact_completeness_validator_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "demo_artifact_completeness", max_len: int = 150) -> str:
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
        return {"error": "demo_artifact_completeness_probe_failed", "detail": repr(exc)}


class DemoArtifactCompletenessValidator:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        dependencies: dict[str, object],
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.dependencies = dependencies
        self.expected_api_endpoints = expected_api_endpoints
        self.checks_dir = output_root / "georeview_studio_demo_artifact_completeness"

    def status(self) -> dict:
        checks = self.current_artifact_checks()
        summary = self.summary(checks)
        existing = self.list_checks(100)
        ready = [row for row in existing if row.get("check_readiness") == "ready_for_demo_artifact_review"]
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "demo_artifact_completeness_version": DEMO_ARTIFACT_COMPLETENESS_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "verify_demo_portfolio_artifacts_before_sharing",
            "output_dir": str(self.checks_dir),
            "artifact_count": summary.get("artifact_count"),
            "required_artifact_count": summary.get("required_artifact_count"),
            "complete_required_artifacts": summary.get("complete_required_artifacts"),
            "missing_required_artifacts": summary.get("missing_required_artifacts"),
            "invalid_required_artifacts": summary.get("invalid_required_artifacts"),
            "check_count": len(existing),
            "ready_check_count": len(ready),
            "latest_check_id": ready[0].get("check_id") if ready else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_demo_artifact_validation" if self.is_complete(summary) else "waiting_for_complete_demo_artifacts",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_check(self, body: dict | None = None) -> dict:
        body = body or {}
        checks = self.current_artifact_checks()
        summary = self.summary(checks)
        if summary.get("required_artifact_count", 0) < 10:
            return self.error("demo_artifact_completeness_input_missing", "Demo artifact validator requires portfolio, release and QA artifacts.")

        stamp = utc_now()
        check_id = f"demo_artifact_completeness_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        check_dir = self.check_dir(check_id)
        manifest_path = check_dir / "demo_artifact_completeness_manifest.json"
        report_path = check_dir / "demo_artifact_completeness_report.md"
        latest_path = self.checks_dir / "latest_demo_artifact_completeness.json"
        readiness = "ready_for_demo_artifact_review" if self.is_complete(summary) else "needs_demo_artifact_follow_up"
        check = {
            "ok": True,
            "demo_artifact_completeness_version": DEMO_ARTIFACT_COMPLETENESS_VERSION,
            "check_id": check_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Demo artifact completeness check before portfolio sharing."),
            "app_version": self.app_version,
            "check_readiness": readiness,
            "summary": summary,
            "artifact_checks": checks,
            "recommended_actions": self.recommended_actions(checks),
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "markdown": str(report_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, check)
        write_json(latest_path, check)
        report_path.write_text(self.report_markdown(check), encoding="utf-8", newline="\n")
        return {"ok": True, "check": check, "source_gis_modified": False, "mutates_config": False}

    def list_checks(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.checks_dir.exists():
            return rows
        manifests = sorted(
            self.checks_dir.glob("demo_artifact_completeness_*/demo_artifact_completeness_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("demo_artifact_completeness_version") != DEMO_ARTIFACT_COMPLETENESS_VERSION:
                continue
            summary = payload.get("summary", {})
            rows.append({
                "check_id": payload.get("check_id"),
                "created_at": payload.get("created_at"),
                "check_readiness": payload.get("check_readiness"),
                "artifact_count": summary.get("artifact_count"),
                "required_artifact_count": summary.get("required_artifact_count"),
                "missing_required_artifacts": summary.get("missing_required_artifacts"),
                "invalid_required_artifacts": summary.get("invalid_required_artifacts"),
                "download_url": f"/api/demo-artifact-completeness/checks/{payload.get('check_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, check_id: str) -> dict:
        path = self.check_dir(check_id) / "demo_artifact_completeness_manifest.json"
        if not path.exists() or not self.safe_check_path(path):
            return {"ok": False, "error": "demo_artifact_completeness_check_not_found", "check_id": check_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "demo_artifact_completeness_check_not_found", "check_id": check_id, "source_gis_modified": False}
        return payload

    def output_file(self, check_id: str, output_id: str = "markdown") -> dict:
        detail = self.detail(check_id)
        if detail.get("error"):
            return detail
        if output_id not in {"markdown", "report"}:
            return {"ok": False, "error": "demo_artifact_completeness_output_not_found", "check_id": check_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_check_path(path):
            return {"ok": False, "error": "demo_artifact_completeness_output_not_found", "check_id": check_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def current_artifact_checks(self) -> list[dict]:
        checks: list[dict] = []
        self.add_file_check(checks, "release_manifest", "project_manifest", self.project_dir / "project_manifest.json", True, self.app_version)
        self.add_file_check(checks, "release_summary", "validation_summary", self.project_dir / "validation_summary.json", True, None)
        self.add_file_check(checks, "release_summary", "api_contract_summary", self.project_dir / "api_contract_summary.json", True, None)
        self.add_file_check(checks, "portfolio", "portfolio_index", self.project_dir / "portfolio" / "index.html", True, "GeoReview")
        self.add_file_check(checks, "portfolio", "portfolio_static_map", self.project_dir / "portfolio" / "assets" / "kfar_saba_static_map.svg", True, "<svg")
        self.add_file_check(checks, "portfolio", "portfolio_top20_csv", self.project_dir / "portfolio" / "sample_review_candidates_top20.csv", True, "review_wording")

        specs = [
            ("portfolio_evidence_bundle", "list_bundles", "bundle_id", "portfolio_evidence_bundle"),
            ("bundle_review_checklist", "list_checklists", "checklist_id", "bundle_review_checklist"),
            ("portfolio_narrative_export", "list_narratives", "narrative_id", "portfolio_narrative"),
            ("portfolio_handoff_page", "list_pages", "page_id", "portfolio_handoff_page"),
            ("portfolio_evidence_gallery", "list_galleries", "gallery_id", "portfolio_evidence_gallery"),
            ("portable_release_package", "list_packages", "package_id", "portable_release_package"),
            ("demo_script_pack", "list_packs", "pack_id", "demo_script_pack"),
            ("visual_qa_ledger", "list_ledgers", "ledger_id", "visual_qa_ledger"),
            ("visual_baseline_comparison", "list_comparisons", "comparison_id", "visual_baseline_comparison"),
        ]
        for dep_name, list_method, id_field, artifact_type in specs:
            self.add_dependency_check(checks, dep_name, list_method, id_field, artifact_type)
        return checks

    def add_dependency_check(self, checks: list[dict], dep_name: str, list_method: str, id_field: str, artifact_type: str) -> None:
        dep = self.dependencies.get(dep_name)
        if dep is None or not hasattr(dep, list_method):
            checks.append(self.missing_check(artifact_type, dep_name, "dependency_not_available", True))
            return
        rows = safe_call(lambda: getattr(dep, list_method)(5), [])
        if not isinstance(rows, list) or not rows:
            checks.append(self.missing_check(artifact_type, dep_name, "no_generated_artifact", True))
            return
        row = rows[0]
        artifact_id = str(row.get(id_field) or "")
        if not artifact_id:
            checks.append(self.missing_check(artifact_type, dep_name, "latest_row_missing_id", True))
            return
        detail = safe_call(lambda: dep.detail(artifact_id), {}) if hasattr(dep, "detail") else {}
        output = safe_call(lambda: dep.output_file(artifact_id), {}) if hasattr(dep, "output_file") else {}
        path = Path(str(output.get("path") or "")) if isinstance(output, dict) and output.get("ok") else self.first_file_path(detail)
        self.add_file_check(
            checks,
            artifact_type,
            artifact_id,
            path,
            True,
            None,
            download_url=str(row.get("download_url") or ""),
            metadata={
                "dependency": dep_name,
                "readiness": self.readiness_value(detail),
                "app_version": detail.get("app_version") if isinstance(detail, dict) else "",
            },
        )

    def add_file_check(
        self,
        checks: list[dict],
        artifact_type: str,
        artifact_id: str,
        path: Path,
        required: bool,
        expected_text: str | None,
        download_url: str = "",
        metadata: dict | None = None,
    ) -> None:
        metadata = metadata or {}
        path = Path(path)
        status = "present"
        reason = ""
        size = 0
        if not path or str(path) == ".":
            status = "missing"
            reason = "path_missing"
        elif not path.exists():
            status = "missing"
            reason = "file_not_found"
        elif not self.safe_artifact_path(path):
            status = "invalid"
            reason = "path_outside_allowed_artifact_roots"
        else:
            try:
                size = path.stat().st_size
            except OSError:
                status = "invalid"
                reason = "stat_failed"
            if status == "present" and size <= 0:
                status = "invalid"
                reason = "empty_file"
            if status == "present" and expected_text:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    if expected_text not in text:
                        status = "invalid"
                        reason = "expected_text_missing"
                except OSError:
                    status = "invalid"
                    reason = "text_probe_failed"
        checks.append({
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "required": required,
            "status": status,
            "reason": reason,
            "path": str(path),
            "size_bytes": size,
            "download_url": download_url,
            "metadata": metadata,
            "source_gis_modified": False,
            "mutates_config": False,
        })

    def missing_check(self, artifact_type: str, artifact_id: str, reason: str, required: bool) -> dict:
        return {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "required": required,
            "status": "missing",
            "reason": reason,
            "path": "",
            "size_bytes": 0,
            "download_url": "",
            "metadata": {},
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def first_file_path(self, detail: object) -> Path:
        if not isinstance(detail, dict):
            return Path("")
        files = detail.get("files")
        if not isinstance(files, dict):
            return Path("")
        for value in files.values():
            path = Path(str(value or ""))
            if path.exists():
                return path
        return Path(str(next(iter(files.values()), "")))

    def readiness_value(self, detail: object) -> str:
        if not isinstance(detail, dict):
            return ""
        for key in ["bundle_readiness", "checklist_readiness", "narrative_readiness", "page_readiness", "gallery_readiness", "package_readiness", "pack_readiness", "ledger_readiness", "comparison_readiness"]:
            if detail.get(key):
                return str(detail.get(key))
        return ""

    def summary(self, checks: list[dict]) -> dict:
        required = [row for row in checks if row.get("required")]
        complete_required = [row for row in required if row.get("status") == "present"]
        missing_required = [row for row in required if row.get("status") == "missing"]
        invalid_required = [row for row in required if row.get("status") == "invalid"]
        return {
            "artifact_count": len(checks),
            "required_artifact_count": len(required),
            "complete_required_artifacts": len(complete_required),
            "missing_required_artifacts": len(missing_required),
            "invalid_required_artifacts": len(invalid_required),
            "optional_artifact_count": len([row for row in checks if not row.get("required")]),
            "total_size_bytes": sum(int(row.get("size_bytes") or 0) for row in checks),
        }

    def is_complete(self, summary: dict) -> bool:
        return (
            int(summary.get("required_artifact_count") or 0) >= 12
            and int(summary.get("missing_required_artifacts") or 0) == 0
            and int(summary.get("invalid_required_artifacts") or 0) == 0
        )

    def recommended_actions(self, checks: list[dict]) -> list[str]:
        actions = []
        for row in checks:
            if row.get("required") and row.get("status") != "present":
                actions.append(f"{row.get('artifact_type')}::{row.get('artifact_id')}: regenerate or inspect artifact ({row.get('reason')}).")
        if not actions:
            actions.append("All required demo artifacts are present. Use this check as the final pre-sharing evidence manifest.")
        return actions[:10]

    def report_markdown(self, check: dict) -> str:
        summary = check.get("summary", {})
        lines = [
            "# Demo Artifact Completeness Validator",
            "",
            f"- Check id: `{check.get('check_id')}`",
            f"- App version: `{check.get('app_version')}`",
            f"- Readiness: `{check.get('check_readiness')}`",
            f"- Required artifacts: `{summary.get('complete_required_artifacts')}` / `{summary.get('required_artifact_count')}`",
            f"- Missing required artifacts: `{summary.get('missing_required_artifacts')}`",
            f"- Invalid required artifacts: `{summary.get('invalid_required_artifacts')}`",
            f"- Total checked size bytes: `{summary.get('total_size_bytes')}`",
            "",
            "## Artifact Checks",
            "",
            "| Type | Artifact | Required | Status | Size |",
            "|---|---:|---:|---:|---:|",
        ]
        for row in check.get("artifact_checks", []):
            lines.append(f"| {row.get('artifact_type')} | `{row.get('artifact_id')}` | {row.get('required')} | `{row.get('status')}` | {row.get('size_bytes')} |")
        lines.extend([
            "",
            "## Recommended Actions",
            "",
        ])
        for item in check.get("recommended_actions", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- This validator checks generated demo files and metadata only. It is not field verification, crash prediction, or an absolute site condition claim.",
            "- Source GIS files remain read-only.",
            "",
        ])
        return "\n".join(lines)

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["demo artifact completeness", "file presence checks", "portfolio sharing readiness", "metadata evidence"],
            "not_allowed": ["field verification", "crash prediction", "absolute site judgement"],
            "source_data_rule": "This feature validates generated artifacts only; it does not read or mutate source GIS files.",
        }

    def safe_artifact_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            roots = [self.project_dir.resolve(), self.output_root.resolve()]
            return any(str(resolved).startswith(str(root)) for root in roots)
        except OSError:
            return False

    def check_dir(self, check_id: str) -> Path:
        return self.checks_dir / safe_token(check_id, "missing_demo_artifact_check", 180)

    def safe_check_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.checks_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
