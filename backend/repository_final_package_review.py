from __future__ import annotations

import html
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPOSITORY_FINAL_PACKAGE_REVIEW_VERSION = "repository_final_package_review_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
LOCAL_PATH_PATTERN = re.compile(r"\b[A-Za-z]:[\\/][^\\n\"'<>|]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "repository_final_package_review", max_len: int = 150) -> str:
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
        return {"error": "repository_final_package_review_probe_failed", "detail": repr(exc)}


class RepositoryFinalPackageReviewBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        repository_dry_run_review: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.repository_dry_run_review = repository_dry_run_review
        self.expected_api_endpoints = expected_api_endpoints
        self.reviews_dir = output_root / "georeview_studio_repository_final_package_reviews"

    def status(self) -> dict:
        dry_runs = self.ready_dry_runs(100)
        reviews = self.list_reviews(100)
        ready_reviews = [row for row in reviews if row.get("review_readiness") == "ready_for_repository_final_package_review"]
        latest_dry_run = dry_runs[0] if dry_runs else {}
        latest_review = ready_reviews[0] if ready_reviews else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "repository_final_package_review_version": REPOSITORY_FINAL_PACKAGE_REVIEW_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "final_repository_package_review_before_public_sharing",
            "output_dir": str(self.reviews_dir),
            "ready_dry_run_review_count": len(dry_runs),
            "latest_dry_run_review_id": latest_dry_run.get("review_id", ""),
            "latest_dry_run_review_status": latest_dry_run.get("review_status", ""),
            "review_count": len(reviews),
            "ready_review_count": len(ready_reviews),
            "latest_review_id": latest_review.get("review_id", ""),
            "latest_review_status": latest_review.get("review_status", ""),
            "latest_required_failed_count": latest_review.get("required_failed_count", 0),
            "latest_public_path_issue_count": latest_review.get("public_path_issue_count", 0),
            "latest_redacted_path_count": latest_review.get("redacted_path_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_repository_final_package_review" if dry_runs else "waiting_for_repository_dry_run_review",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_review(self, body: dict | None = None) -> dict:
        body = body or {}
        dry_run_id = str(body.get("dry_run_review_id") or body.get("repository_dry_run_review_id") or body.get("review_id") or "").strip()
        if not dry_run_id:
            dry_runs = self.ready_dry_runs(20)
            dry_run_id = str(dry_runs[0].get("review_id") or "") if dry_runs else ""
        if not dry_run_id:
            return self.error("repository_final_package_review_input_missing", "A ready repository dry-run review is required.")
        dry_run = self.resolve_dry_run(dry_run_id)
        if dry_run.get("error"):
            return dry_run
        if dry_run.get("review_readiness") != "ready_for_repository_dry_run_review":
            return self.error("repository_final_package_review_not_ready", "Repository dry-run review must be ready_for_repository_dry_run_review.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        archive_files = dry_run.get("archive_files", []) if isinstance(dry_run.get("archive_files"), list) else []
        exclude_rules = dry_run.get("exclude_rules", []) if isinstance(dry_run.get("exclude_rules"), list) else []
        path_evidence = self.redacted_path_evidence(dry_run)
        publication_checklist = self.publication_decision_checklist(dry_run, validation)
        final_instructions = self.final_package_instructions(dry_run)
        boundary_checks = self.boundary_checks(dry_run, validation, api_contract, manifest, archive_files, exclude_rules, path_evidence)
        required_failed = [row for row in boundary_checks if row.get("required") and row.get("status") != "ready"]
        review_status = "ready_with_reviewer_attention_items"
        if required_failed:
            review_status = "needs_repository_final_package_fixes"
        if not self.api_and_validation_ready(validation, api_contract):
            review_status = "pending_validation_or_api_contract"

        stamp = utc_now()
        review_id = f"repository_final_package_review_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        review_dir = self.review_dir(review_id)
        manifest_path = review_dir / "repository_final_package_review_manifest.json"
        review_path = review_dir / "FINAL_REPOSITORY_PACKAGE_REVIEW.md"
        path_evidence_path = review_dir / "REDACTED_PATH_EVIDENCE.md"
        checklist_path = review_dir / "PUBLICATION_DECISION_CHECKLIST.md"
        html_path = review_dir / "repository_final_package_review.html"
        zip_path = review_dir / "repository_final_package_review.zip"
        latest_path = self.reviews_dir / "latest_repository_final_package_review.json"
        review = {
            "ok": True,
            "repository_final_package_review_version": REPOSITORY_FINAL_PACKAGE_REVIEW_VERSION,
            "review_id": review_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_repository_reviewer"),
            "notes": str(body.get("notes") or "Final local repository package review before public sharing."),
            "app_version": self.app_version,
            "dry_run_review_id": dry_run.get("review_id"),
            "review_readiness": "ready_for_repository_final_package_review",
            "review_status": review_status,
            "archive_file_count": len(archive_files),
            "exclude_rule_count": len(exclude_rules),
            "publication_checklist_item_count": len(publication_checklist),
            "final_instruction_count": len(final_instructions),
            "boundary_check_count": len(boundary_checks),
            "required_failed_count": len(required_failed),
            "public_path_issue_count": path_evidence.get("public_path_issue_count", 0),
            "internal_local_path_count": path_evidence.get("internal_local_path_count", 0),
            "redacted_path_count": path_evidence.get("redacted_path_count", 0),
            "archive_files": archive_files,
            "exclude_rules": exclude_rules,
            "publication_decision_checklist": publication_checklist,
            "final_package_instructions": final_instructions,
            "redacted_path_evidence": path_evidence,
            "boundary_checks": boundary_checks,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "evidence_summary": self.evidence_summary(dry_run, validation, api_contract, manifest),
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "review": str(review_path),
                "redacted_path_evidence": str(path_evidence_path),
                "publication_checklist": str(checklist_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, review)
        write_json(latest_path, review)
        review_path.write_text(self.review_markdown(review), encoding="utf-8", newline="\n")
        path_evidence_path.write_text(self.path_evidence_markdown(review), encoding="utf-8", newline="\n")
        checklist_path.write_text(self.checklist_markdown(review), encoding="utf-8", newline="\n")
        html_path.write_text(self.review_html(review), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, review_path, path_evidence_path, checklist_path, html_path])
        review["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, review)
        write_json(latest_path, review)
        return {"ok": True, "review": review, "source_gis_modified": False, "mutates_config": False}

    def list_reviews(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.reviews_dir.exists():
            return rows
        manifests = sorted(
            self.reviews_dir.glob("repository_final_package_review_*/repository_final_package_review_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("repository_final_package_review_version") != REPOSITORY_FINAL_PACKAGE_REVIEW_VERSION:
                continue
            rows.append({
                "review_id": payload.get("review_id"),
                "created_at": payload.get("created_at"),
                "review_readiness": payload.get("review_readiness"),
                "review_status": payload.get("review_status"),
                "dry_run_review_id": payload.get("dry_run_review_id"),
                "archive_file_count": payload.get("archive_file_count", 0),
                "publication_checklist_item_count": payload.get("publication_checklist_item_count", 0),
                "required_failed_count": payload.get("required_failed_count", 0),
                "public_path_issue_count": payload.get("public_path_issue_count", 0),
                "redacted_path_count": payload.get("redacted_path_count", 0),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
                "includes_source_gis": payload.get("includes_source_gis", False),
            })
            if len(rows) >= max(1, int(limit or 20)):
                break
        return rows

    def detail(self, review_id: str) -> dict:
        path = self.review_dir(review_id) / "repository_final_package_review_manifest.json"
        if not self.safe_review_path(path):
            return {"ok": False, "error": "repository_final_package_review_not_found", "review_id": review_id, "source_gis_modified": False}
        payload = read_json(path)
        if payload.get("repository_final_package_review_version") != REPOSITORY_FINAL_PACKAGE_REVIEW_VERSION:
            return {"ok": False, "error": "repository_final_package_review_not_found", "review_id": review_id, "source_gis_modified": False}
        return payload

    def output_file(self, review_id: str, output_id: str = "zip") -> dict:
        detail = self.detail(review_id)
        if detail.get("error"):
            return detail
        path = Path(str(detail.get("files", {}).get(output_id) or ""))
        if not path.exists() or not self.safe_review_path(path):
            return {"ok": False, "error": "repository_final_package_review_output_not_found", "review_id": review_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_dry_runs(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.repository_dry_run_review.list_reviews(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("review_readiness") == "ready_for_repository_dry_run_review" and int(row.get("required_failed_count") or 0) == 0]

    def resolve_dry_run(self, dry_run_id: str) -> dict:
        detail = safe_call(lambda: self.repository_dry_run_review.detail(dry_run_id), {})
        return detail if isinstance(detail, dict) else self.error("repository_dry_run_review_not_found", "Repository dry-run review detail failed.")

    def api_and_validation_ready(self, validation: dict, api_contract: dict) -> bool:
        return validation.get("passed") is True and api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints

    def collect_local_paths(self, value: object) -> list[str]:
        if isinstance(value, str):
            return [match.group(0) for match in LOCAL_PATH_PATTERN.finditer(value)]
        if isinstance(value, dict):
            paths: list[str] = []
            for item in value.values():
                paths.extend(self.collect_local_paths(item))
            return paths
        if isinstance(value, list):
            paths: list[str] = []
            for item in value:
                paths.extend(self.collect_local_paths(item))
            return paths
        return []

    def redacted_path_evidence(self, dry_run: dict) -> dict:
        local_paths = sorted(set(self.collect_local_paths(dry_run)))
        archive_files = dry_run.get("archive_files", []) if isinstance(dry_run.get("archive_files"), list) else []
        public_issues = []
        for item in archive_files:
            path = str(item.get("path") or "")
            if LOCAL_PATH_PATTERN.search(path) or path.startswith("/") or path.startswith("\\"):
                public_issues.append(path)
        redacted_examples = []
        for path in local_paths[:12]:
            redacted_examples.append({
                "original_class": self.path_class(path),
                "redacted_value": self.redact_path(path),
                "public_policy": "internal_evidence_only_not_public_repository_path",
            })
        return {
            "public_path_issue_count": len(public_issues),
            "public_path_issues": public_issues,
            "internal_local_path_count": len(local_paths),
            "redacted_path_count": len(redacted_examples),
            "redacted_examples": redacted_examples,
            "public_archive_path_policy": "All public archive include paths should be repository-relative paths.",
            "internal_evidence_path_policy": "Generated local evidence may keep absolute paths in private manifests; public README/docs should use relative paths or redacted placeholders.",
        }

    def path_class(self, path: str) -> str:
        lower = path.replace("\\", "/").lower()
        if "/analysis_output/" in lower:
            return "local_generated_analysis_output"
        if lower.endswith((".osm.pbf", ".shp", ".dbf", ".prj", ".cpg", ".gpkg", ".zip")):
            return "local_source_or_gis_file"
        if "/georeview_studio_app/" in lower:
            return "local_app_release_path"
        return "local_absolute_path"

    def redact_path(self, path: str) -> str:
        lower = path.replace("\\", "/").lower()
        name = Path(path).name
        if "/analysis_output/" in lower:
            return f"<LOCAL_ANALYSIS_OUTPUT>/{name}"
        if "/georeview_studio_app/" in lower:
            return f"<LOCAL_APP_RELEASE>/{name}"
        if lower.endswith((".osm.pbf", ".shp", ".dbf", ".prj", ".cpg", ".gpkg", ".zip")):
            return f"<LOCAL_SOURCE_GIS>/{name}"
        return f"<LOCAL_PATH>/{name}"

    def publication_decision_checklist(self, dry_run: dict, validation: dict) -> list[dict]:
        return [
            {"item": "Repository license decision", "status": "reviewer_attention", "required_before_public": True, "evidence": "Choose MIT, Apache-2.0, private repo, or no-license intentionally."},
            {"item": "OSM and Geofabrik attribution", "status": "reviewer_attention", "required_before_public": True, "evidence": "Add attribution text without redistributing source GIS."},
            {"item": "Source GIS excluded from public archive", "status": "ready", "required_before_public": True, "evidence": f"{len(dry_run.get('exclude_rules', []) if isinstance(dry_run.get('exclude_rules'), list) else [])} exclude rules inherited from dry-run review."},
            {"item": "Public paths are repository-relative", "status": "ready", "required_before_public": True, "evidence": "Archive include plan uses paths such as README.md and docs/*.md."},
            {"item": "Local absolute paths are redacted in public docs", "status": "reviewer_attention", "required_before_public": True, "evidence": "Use REDACTED_PATH_EVIDENCE.md before publishing."},
            {"item": "Dashboard screenshot exists", "status": "reviewer_attention", "required_before_public": True, "evidence": f"Use {validation.get('generators', 0)} generator rows as the demo context."},
            {"item": "Approved claim wording kept", "status": "ready", "required_before_public": True, "evidence": self.review_wording},
            {"item": "Sample outputs labelled as generated samples", "status": "ready", "required_before_public": True, "evidence": "Do not present sample CSVs as official municipal data."},
        ]

    def final_package_instructions(self, dry_run: dict) -> list[dict]:
        return [
            {"step": 1, "action": "Use the archive include plan as the public repository skeleton.", "evidence": f"{len(dry_run.get('archive_files', []) if isinstance(dry_run.get('archive_files'), list) else [])} planned include files."},
            {"step": 2, "action": "Keep source GIS files out of the repository.", "evidence": "Hard exclude rules cover OSM PBF, shapefile sidecars, GPKG and source_data/."},
            {"step": 3, "action": "Replace private absolute Windows paths with relative paths or redacted placeholders.", "evidence": "See REDACTED_PATH_EVIDENCE.md."},
            {"step": 4, "action": "Add attribution and license decision text before making the repository public.", "evidence": "Publication decision checklist marks these as reviewer attention."},
            {"step": 5, "action": "Use the approved infrastructure-indicator wording in README and case study.", "evidence": self.review_wording},
            {"step": 6, "action": "Attach screenshots as manually captured reviewer evidence, not as source data.", "evidence": "Screenshot tasks remain explicit."},
            {"step": 7, "action": "Run validation and API contract again after curating the public repository.", "evidence": f"Expected API endpoints for this local release: {self.expected_api_endpoints}."},
            {"step": 8, "action": "Keep public claims scoped to field-review prioritization.", "evidence": "No crash prediction or absolute safety claim is made."},
        ]

    def boundary_checks(self, dry_run: dict, validation: dict, api_contract: dict, manifest: dict, archive_files: list[dict], exclude_rules: list[dict], path_evidence: dict) -> list[dict]:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        exclude_text = json.dumps(exclude_rules, ensure_ascii=False)
        return [
            self.check("Repository dry-run review is ready", dry_run.get("review_readiness") == "ready_for_repository_dry_run_review", True, "Create repository dry-run review first."),
            self.check("Dry-run required checks passed", int(dry_run.get("required_failed_count") or 0) == 0, True, "Resolve dry-run required checks first."),
            self.check("Validation summary passed", validation.get("passed") is True, True, "Run validation before final package review."),
            self.check("API contract evidence available", api_contract.get("passed") is True and api_checked >= max(1, self.expected_api_endpoints - 5), False, f"Run API contract after adding {self.app_version} endpoints."),
            self.check("Manifest points to current local release", str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).endswith("8847"), True, f"Update manifest for {self.app_version}."),
            self.check("Public archive paths are repository-relative", int(path_evidence.get("public_path_issue_count") or 0) == 0, True, "Replace public archive paths with repository-relative paths."),
            self.check("Source GIS remains excluded", all(token in exclude_text for token in ("*.osm.pbf", "*.shp", "*.gpkg", "source_data/")), True, "Keep source GIS hard-exclude rules."),
            self.check("Redacted path evidence generated", int(path_evidence.get("redacted_path_count") or 0) >= 1 or int(path_evidence.get("internal_local_path_count") or 0) == 0, True, "Document redaction policy for local absolute paths."),
            self.check("Approved wording present", self.review_wording in json.dumps(dry_run, ensure_ascii=False), True, "Keep claim boundary in public docs."),
            self.check("License, attribution and screenshot tasks remain explicit", True, False, "Resolve reviewer attention items before public sharing."),
        ]

    @staticmethod
    def check(name: str, passed: bool, required: bool, recommendation: str) -> dict:
        return {"check": name, "required": required, "status": "ready" if passed else ("needs_fix" if required else "reviewer_attention"), "recommendation": recommendation}

    def evidence_summary(self, dry_run: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        return {
            "dry_run_review_id": dry_run.get("review_id"),
            "dry_run_review_status": dry_run.get("review_status"),
            "dry_run_required_failed": dry_run.get("required_failed_count"),
            "validation_passed": validation.get("passed") is True,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "api_contract_passed": api_contract.get("passed") is True,
            "api_contract_checked_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
            "generators": validation.get("generators", 0),
            "crossings": validation.get("crossings", 0),
            "route_aware_rows": validation.get("route_aware_rows", 0),
            "review_wording": self.review_wording,
        }

    def claim_boundaries(self) -> list[str]:
        return [
            self.review_wording,
            "The final package review is a local readiness artifact; it does not publish anything.",
            "Source GIS files and large OSM extracts stay local unless a separate licensing decision allows otherwise.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "Public repository paths should be relative; private absolute paths belong only in local evidence or redacted examples.",
        ]

    def review_markdown(self, review: dict) -> str:
        lines = [
            "# Final Repository Package Review",
            "",
            f"- Review id: `{review.get('review_id')}`",
            f"- Status: `{review.get('review_status')}`",
            f"- Source dry-run review: `{review.get('dry_run_review_id')}`",
            f"- Required failed checks: `{review.get('required_failed_count')}`",
            f"- Public path issues: `{review.get('public_path_issue_count')}`",
            f"- Redacted path examples: `{review.get('redacted_path_count')}`",
            "",
            "## Final Package Instructions",
            "",
        ]
        for item in review.get("final_package_instructions", []):
            lines.append(f"{item.get('step')}. {item.get('action')} Evidence: {item.get('evidence')}")
        lines.extend(["", "## Claim Boundaries", ""])
        for line in review.get("claim_boundaries", []):
            lines.append(f"- {line}")
        lines.extend(["", "## Boundary Checks", ""])
        for item in review.get("boundary_checks", []):
            lines.append(f"- {item.get('check')}: `{item.get('status')}`")
        lines.append("")
        return "\n".join(lines)

    def path_evidence_markdown(self, review: dict) -> str:
        evidence = review.get("redacted_path_evidence", {})
        lines = [
            "# Redacted Path Evidence",
            "",
            f"- Public archive path issues: `{evidence.get('public_path_issue_count', 0)}`",
            f"- Internal local absolute paths found in private evidence: `{evidence.get('internal_local_path_count', 0)}`",
            f"- Redacted examples: `{evidence.get('redacted_path_count', 0)}`",
            "",
            "## Policy",
            "",
            f"- {evidence.get('public_archive_path_policy')}",
            f"- {evidence.get('internal_evidence_path_policy')}",
            "",
            "## Examples",
            "",
            "| Class | Redacted value | Public policy |",
            "|---|---|---|",
        ]
        for item in evidence.get("redacted_examples", []):
            lines.append(f"| `{item.get('original_class')}` | `{item.get('redacted_value')}` | {item.get('public_policy')} |")
        lines.append("")
        return "\n".join(lines)

    def checklist_markdown(self, review: dict) -> str:
        lines = ["# Publication Decision Checklist", "", "| Item | Required before public | Status | Evidence |", "|---|---:|---|---|"]
        for item in review.get("publication_decision_checklist", []):
            lines.append(f"| {item.get('item')} | {str(item.get('required_before_public')).lower()} | {item.get('status')} | {item.get('evidence')} |")
        lines.append("")
        return "\n".join(lines)

    def review_html(self, review: dict) -> str:
        instruction_rows = "".join(f"<li><strong>{html.escape(str(item.get('step') or ''))}</strong>. {html.escape(str(item.get('action') or ''))}<br /><span>{html.escape(str(item.get('evidence') or ''))}</span></li>" for item in review.get("final_package_instructions", []))
        check_rows = "".join(f"<tr><td>{html.escape(str(item.get('check') or ''))}</td><td>{html.escape(str(item.get('required') or ''))}</td><td>{html.escape(str(item.get('status') or ''))}</td><td>{html.escape(str(item.get('recommendation') or ''))}</td></tr>" for item in review.get("boundary_checks", []))
        redacted_rows = "".join(f"<tr><td>{html.escape(str(item.get('original_class') or ''))}</td><td>{html.escape(str(item.get('redacted_value') or ''))}</td><td>{html.escape(str(item.get('public_policy') or ''))}</td></tr>" for item in review.get("redacted_path_evidence", {}).get("redacted_examples", []))
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Final Repository Package Review</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7f5; color: #1f2933; }}
      .summary, section {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
      table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 8px; }}
      th, td {{ border: 1px solid #d7d8d2; padding: 8px; vertical-align: top; }}
      th {{ background: #eef0ea; text-align: left; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
      li {{ margin-bottom: 8px; }}
    </style>
  </head>
  <body>
    <h1>Final Repository Package Review</h1>
    <div class="summary">
      <p>Review: <code>{html.escape(str(review.get("review_id") or ""))}</code></p>
      <p>Status: <code>{html.escape(str(review.get("review_status") or ""))}</code>; failed required checks: <code>{html.escape(str(review.get("required_failed_count") or 0))}</code>.</p>
      <p>Public path issues: <code>{html.escape(str(review.get("public_path_issue_count") or 0))}</code>; redacted path examples: <code>{html.escape(str(review.get("redacted_path_count") or 0))}</code>.</p>
    </div>
    <section><h2>Final Package Instructions</h2><ol>{instruction_rows}</ol></section>
    <section><h2>Redacted Path Evidence</h2><table><thead><tr><th>Class</th><th>Redacted value</th><th>Policy</th></tr></thead><tbody>{redacted_rows}</tbody></table></section>
    <section><h2>Boundary Checks</h2><table><thead><tr><th>Check</th><th>Required</th><th>Status</th><th>Recommendation</th></tr></thead><tbody>{check_rows}</tbody></table></section>
  </body>
</html>"""

    def write_zip(self, zip_path: Path, paths: list[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if path.exists() and self.safe_review_path(path):
                    zf.write(path, arcname=path.name)

    def review_dir(self, review_id: str) -> Path:
        return self.reviews_dir / safe_token(review_id, "missing_repository_final_package_review", 180)

    def safe_review_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.reviews_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}

