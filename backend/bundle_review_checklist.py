from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


BUNDLE_REVIEW_CHECKLIST_VERSION = "bundle_review_checklist_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "bundle_review_checklist") -> str:
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
        return {"error": "bundle_review_probe_failed", "detail": repr(exc)}


class BundleReviewChecklist:
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
        self.checklists_dir = output_root / "georeview_studio_bundle_review_checklists"
        self.bundles_dir = output_root / "georeview_studio_portfolio_evidence_bundles"

    def status(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        latest_bundle = self.latest_bundle()
        checks = self.evaluate_bundle(latest_bundle) if latest_bundle else []
        return {
            "ok": True,
            "bundle_review_checklist_version": BUNDLE_REVIEW_CHECKLIST_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "expected_api_endpoints": self.expected_api_endpoints,
            "checklist_count": len(self.list_checklists(500)),
            "latest_bundle_id": latest_bundle.get("bundle_id") if latest_bundle else "",
            "latest_bundle_readiness": latest_bundle.get("readiness_level") if latest_bundle else "",
            "latest_bundle_app_version": latest_bundle.get("app_version") if latest_bundle else "",
            "summary": self.summary(checks) if checks else self.empty_summary(),
            "guided_review_steps": self.guided_review_steps(),
            "default_action": "create_guided_bundle_review_checklist",
            "output_dir": str(self.checklists_dir),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_checklist(self, body: dict | None = None) -> dict:
        body = body or {}
        bundle = self.resolve_bundle(body)
        if not bundle:
            return {"ok": False, "error": "portfolio_evidence_bundle_not_found", "source_gis_modified": False, "mutates_config": False}
        checks = self.evaluate_bundle(bundle)
        summary = self.summary(checks)
        stamp = utc_now()
        checklist_id = f"bundle_review_checklist_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        checklist = {
            "ok": True,
            "checklist_id": checklist_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Guided review checklist for a portfolio evidence bundle."),
            "bundle_review_checklist_version": BUNDLE_REVIEW_CHECKLIST_VERSION,
            "app_version": self.app_version,
            "bundle_id": bundle.get("bundle_id"),
            "bundle_app_version": bundle.get("app_version"),
            "bundle_readiness_level": bundle.get("readiness_level"),
            "expected_api_endpoints": self.expected_api_endpoints,
            "summary": summary,
            "checks": checks,
            "guided_review_steps": self.guided_review_steps(),
            "remediation_actions": [check.get("remediation_action") for check in checks if check.get("status") != "passed"],
            "approved_review_wording": self.review_wording,
            "claim_boundary": "Checklist verifies evidence completeness for infrastructure indicators and data-quality flags; it is not a crash prediction artifact.",
            "source_gis_modified": False,
            "mutates_config": False,
        }
        json_path = self.checklists_dir / f"{checklist_id}.json"
        md_path = self.checklists_dir / f"{checklist_id}.md"
        latest_path = self.checklists_dir / "latest_bundle_review_checklist.json"
        checklist["files"] = {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)}
        write_json(json_path, checklist)
        write_json(latest_path, checklist)
        md_path.write_text(self.checklist_markdown(checklist), encoding="utf-8", newline="\n")
        return {"ok": True, "checklist": checklist, "source_gis_modified": False, "mutates_config": False}

    def resolve_bundle(self, body: dict) -> dict:
        bundle_id = str(body.get("bundle_id") or "")
        portfolio_bundle = self.dependencies.get("portfolio_evidence_bundle")
        if bundle_id and portfolio_bundle:
            detail = safe_call(lambda: portfolio_bundle.detail(bundle_id), {})
            return detail if isinstance(detail, dict) and not detail.get("error") else {}
        if body.get("create_bundle", True) and portfolio_bundle:
            result = safe_call(
                lambda: portfolio_bundle.create_bundle({
                    "created_by": str(body.get("created_by") or "bundle_review_checklist"),
                    "notes": "Checklist-created portfolio evidence bundle.",
                    "reuse_latest": body.get("reuse_latest", True),
                }),
                {},
            )
            if isinstance(result, dict) and result.get("ok"):
                bundle = result.get("bundle", {})
                return bundle if isinstance(bundle, dict) else {}
        return self.latest_bundle()

    def latest_bundle(self) -> dict:
        latest = read_json(self.bundles_dir / "latest_portfolio_evidence_bundle.json")
        if latest:
            return latest
        portfolio_bundle = self.dependencies.get("portfolio_evidence_bundle")
        if portfolio_bundle:
            rows = safe_call(lambda: portfolio_bundle.list_bundles(1), [])
            if isinstance(rows, list) and rows:
                detail = safe_call(lambda: portfolio_bundle.detail(str(rows[0].get("bundle_id") or "")), {})
                return detail if isinstance(detail, dict) else {}
        return {}

    def evaluate_bundle(self, bundle: dict) -> list[dict]:
        copied_files = bundle.get("copied_files", []) if isinstance(bundle, dict) else []
        labels = {str(item.get("label") or "") for item in copied_files}
        validation = self.read_copied_json(copied_files, "validation_summary")
        api_contract = self.read_copied_json(copied_files, "api_contract_summary")
        manifest = self.read_copied_json(copied_files, "project_manifest")
        total_bytes = 0
        missing_file_paths = []
        for item in copied_files:
            path = Path(str(item.get("bundle_path") or ""))
            size = self.safe_size(path)
            total_bytes += size
            if not path.exists() or size <= 0:
                missing_file_paths.append(str(path))

        required_labels = [
            "project_manifest",
            "validation_summary",
            "api_contract_summary",
            "portfolio_case_study",
            "portfolio_pitch",
            "sample_review_candidates",
            "portfolio_manifest",
            "static_map",
            "release_readiness_snapshot_json",
            "release_readiness_snapshot_markdown",
            "portfolio_demo_snapshot_json",
            "portfolio_demo_snapshot_markdown",
        ]
        missing_labels = [label for label in required_labels if label not in labels]
        markdown_path = Path(str(bundle.get("files", {}).get("markdown") or ""))

        checks = [
            self.check(
                "bundle_exists",
                "Portfolio evidence bundle is available",
                "passed" if bundle.get("bundle_id") else "failed",
                {"bundle_id": bundle.get("bundle_id")},
                "Create a portfolio evidence bundle before review.",
            ),
            self.check(
                "bundle_version_current",
                "Bundle was created by the current app version",
                "passed" if bundle.get("app_version") == self.app_version else "warning",
                {"bundle_app_version": bundle.get("app_version"), "current_app_version": self.app_version},
                "Create a fresh evidence bundle from the current release.",
            ),
            self.check(
                "project_manifest_current",
                "Copied project manifest matches the current local release",
                "passed" if str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).endswith(str(self.manifest_reader().get("local_url", "")).rsplit(":", 1)[-1]) else "warning",
                {"manifest_version": manifest.get("version"), "local_url": manifest.get("local_url")},
                "Regenerate the bundle after updating project_manifest.json.",
            ),
            self.check(
                "release_readiness_ready",
                "Release readiness snapshot is demo-ready",
                "passed" if bundle.get("readiness_level") == "ready_for_local_portfolio_demo" else "warning",
                {"readiness_level": bundle.get("readiness_level"), "failed_gates": bundle.get("readiness_failed_gate_count")},
                "Run validation, API contract, then create a fresh readiness snapshot and bundle.",
            ),
            self.check(
                "validation_summary_passed",
                "Validation summary is present and passed",
                "passed" if validation.get("passed") is True and validation.get("app_version") == self.app_version else "warning",
                {"passed": validation.get("passed"), "app_version": validation.get("app_version")},
                "Run scripts/validate.ps1 and recreate the evidence bundle.",
            ),
            self.check(
                "api_contract_summary_current",
                "API contract summary covers the current public endpoints",
                "passed" if api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints else "warning",
                {"passed": api_contract.get("passed"), "checked_endpoints": api_contract.get("checked_endpoints"), "expected_api_endpoints": self.expected_api_endpoints},
                "Run scripts/test_api_contract.ps1 and recreate the evidence bundle.",
            ),
            self.check(
                "required_evidence_labels",
                "Required evidence files were copied into the bundle",
                "passed" if not missing_labels else "failed",
                {"required_label_count": len(required_labels), "missing_labels": missing_labels, "copied_label_count": len(labels)},
                "Regenerate portfolio artifacts, readiness/demo snapshots, then create a fresh bundle.",
            ),
            self.check(
                "copied_file_integrity",
                "Copied evidence files exist and are non-empty",
                "passed" if copied_files and not missing_file_paths else "failed",
                {"copied_file_count": len(copied_files), "missing_or_empty": missing_file_paths[:8]},
                "Recreate the evidence bundle so every copied file has a valid local path.",
            ),
            self.check(
                "portfolio_story_artifacts",
                "Portfolio story artifacts are included",
                "passed" if {"portfolio_case_study", "portfolio_pitch", "sample_review_candidates", "static_map"}.issubset(labels) else "failed",
                {"present_labels": sorted(label for label in labels if label in {"portfolio_case_study", "portfolio_pitch", "sample_review_candidates", "static_map"})},
                "Regenerate portfolio artifacts before packaging the bundle.",
            ),
            self.check(
                "snapshot_pair_artifacts",
                "Readiness and guided demo snapshots include JSON and Markdown",
                "passed" if {"release_readiness_snapshot_json", "release_readiness_snapshot_markdown", "portfolio_demo_snapshot_json", "portfolio_demo_snapshot_markdown"}.issubset(labels) else "warning",
                {"snapshot_labels": sorted(label for label in labels if "snapshot" in label)},
                "Create fresh readiness and portfolio demo snapshots before bundling.",
            ),
            self.check(
                "review_wording_and_claim_boundary",
                "Approved wording and claim boundary are present",
                "passed" if bundle.get("approved_review_wording") == self.review_wording and "crash prediction" in str(bundle.get("claim_boundary", "")).lower() else "failed",
                {"approved_review_wording": bundle.get("approved_review_wording"), "claim_boundary": bundle.get("claim_boundary")},
                "Keep the field-review wording and crash-prediction boundary in every bundle.",
            ),
            self.check(
                "source_and_config_read_only",
                "Bundle review does not mutate source GIS or profile config",
                "passed" if bundle.get("source_gis_modified") is False and bundle.get("mutates_config") is False else "failed",
                {"source_gis_modified": bundle.get("source_gis_modified"), "mutates_config": bundle.get("mutates_config")},
                "Generated review evidence must stay under analysis_output and must not apply mapper config changes.",
            ),
            self.check(
                "markdown_download_available",
                "Checklist can point to a shareable Markdown bundle report",
                "passed" if markdown_path.exists() and self.safe_size(markdown_path) > 500 else "failed",
                {"markdown_path": str(markdown_path), "size_bytes": self.safe_size(markdown_path)},
                "Create a bundle with a Markdown report before sharing.",
            ),
            self.check(
                "shareable_size_budget",
                "Bundle remains small enough for manual portfolio review",
                "passed" if total_bytes <= 25_000_000 else "warning",
                {"total_copied_bytes": total_bytes, "size_budget_bytes": 25_000_000},
                "Reduce copied generated artifacts or share the Markdown/JSON summary first.",
            ),
        ]
        summary = self.summary(checks)
        checks.append(self.check(
            "reviewer_ready",
            "Bundle is ready for a reviewer walkthrough",
            "passed" if summary.get("failed_count") == 0 and summary.get("warning_count") == 0 else "warning",
            {"failed_count": summary.get("failed_count"), "warning_count": summary.get("warning_count")},
            "Resolve warnings before using the bundle as the final portfolio handoff.",
        ))
        return checks

    def read_copied_json(self, copied_files: list[dict], label: str) -> dict:
        for item in copied_files:
            if item.get("label") == label:
                return read_json(Path(str(item.get("bundle_path") or "")))
        return {}

    def safe_size(self, path: Path) -> int:
        try:
            return path.stat().st_size if path.exists() else 0
        except OSError:
            return 0

    def check(self, check_id: str, label: str, status: str, evidence: dict, remediation_action: str) -> dict:
        return {
            "check_id": check_id,
            "label": label,
            "status": status,
            "passed": status == "passed",
            "evidence": evidence,
            "remediation_action": remediation_action,
        }

    def summary(self, checks: list[dict]) -> dict:
        counts = {"passed": 0, "warning": 0, "failed": 0}
        for check in checks:
            status = str(check.get("status") or "warning")
            counts[status] = counts.get(status, 0) + 1
        if counts.get("failed", 0) > 0:
            readiness = "not_ready_to_share"
        elif counts.get("warning", 0) > 0:
            readiness = "ready_with_review_warnings"
        else:
            readiness = "ready_to_share"
        return {
            "check_count": len(checks),
            "passed_count": counts.get("passed", 0),
            "warning_count": counts.get("warning", 0),
            "failed_count": counts.get("failed", 0),
            "review_readiness": readiness,
        }

    def empty_summary(self) -> dict:
        return {"check_count": 0, "passed_count": 0, "warning_count": 0, "failed_count": 0, "review_readiness": "no_bundle_available"}

    def guided_review_steps(self) -> list[dict]:
        return [
            {"step_id": "open_bundle_manifest", "label": "Open the bundle manifest and confirm app, release and bundle ids."},
            {"step_id": "check_readiness", "label": "Verify readiness, validation and API contract evidence."},
            {"step_id": "inspect_story", "label": "Review case study, pitch, sample CSV and static map."},
            {"step_id": "confirm_claim_boundary", "label": "Confirm the wording stays on infrastructure indicators and field review."},
            {"step_id": "resolve_warnings", "label": "Use remediation actions before sharing the final portfolio handoff."},
        ]

    def list_checklists(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.checklists_dir.exists():
            return rows
        for path in sorted(self.checklists_dir.glob("bundle_review_checklist_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            summary = payload.get("summary", {})
            rows.append({
                "checklist_id": payload.get("checklist_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "bundle_id": payload.get("bundle_id"),
                "review_readiness": summary.get("review_readiness"),
                "failed_count": summary.get("failed_count"),
                "warning_count": summary.get("warning_count"),
                "json_file": str(path),
                "markdown_file": payload.get("files", {}).get("markdown"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, checklist_id: str) -> dict:
        token = safe_token(checklist_id, "missing")
        path = self.checklists_dir / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "bundle_review_checklist_not_found", "checklist_id": checklist_id, "source_gis_modified": False}
        return payload

    def output_file(self, checklist_id: str, output_id: str = "bundle_review_checklist_report") -> dict:
        detail = self.detail(checklist_id)
        if detail.get("error"):
            return detail
        if output_id not in {"bundle_review_checklist_report", "markdown"}:
            return {"ok": False, "error": "bundle_review_checklist_output_not_found", "checklist_id": checklist_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists():
            return {"ok": False, "error": "bundle_review_checklist_output_not_found", "checklist_id": checklist_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False}

    def checklist_markdown(self, checklist: dict) -> str:
        summary = checklist.get("summary", {})
        lines = [
            "# GeoReview Studio Bundle Review Checklist",
            "",
            f"Checklist: `{checklist.get('checklist_id')}`",
            f"Bundle: `{checklist.get('bundle_id')}`",
            f"Created: `{checklist.get('created_at')}`",
            f"Review readiness: `{summary.get('review_readiness')}`",
            "",
            "Approved review wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Summary",
            "",
            f"- Checks: `{summary.get('check_count')}`",
            f"- Passed: `{summary.get('passed_count')}`",
            f"- Warnings: `{summary.get('warning_count')}`",
            f"- Failed: `{summary.get('failed_count')}`",
            "",
            "## Checks",
            "",
        ]
        for check in checklist.get("checks", []):
            lines.append(f"- `{check.get('check_id')}`: `{check.get('status')}` - {check.get('label')}")
        actions = checklist.get("remediation_actions", [])
        if actions:
            lines.extend(["", "## Remediation Actions", ""])
            for action in actions:
                lines.append(f"- {action}")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            "This checklist validates evidence completeness for infrastructure review indicators and data-quality flags.",
            "It does not label a location and does not predict crashes.",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)
