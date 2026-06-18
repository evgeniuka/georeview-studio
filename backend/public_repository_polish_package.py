from __future__ import annotations

import html
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PUBLIC_REPOSITORY_POLISH_PACKAGE_VERSION = "public_repository_polish_package_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
LOCAL_ABSOLUTE_PATH_PATTERN = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\"'<>|\r\n]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "public_repository_polish_package", max_len: int = 150) -> str:
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
        return {"error": "public_repository_polish_package_probe_failed", "detail": repr(exc)}


class PublicRepositoryPolishPackageBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        public_readme_cleanup_review: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.public_readme_cleanup_review = public_readme_cleanup_review
        self.expected_api_endpoints = expected_api_endpoints
        self.packages_dir = output_root / "georeview_studio_public_repository_polish_packages"

    def status(self) -> dict:
        cleanup_reviews = self.ready_cleanup_reviews(100)
        packages = self.list_packages(100)
        ready_packages = [row for row in packages if row.get("package_readiness") == "ready_for_public_repository_polish"]
        latest_cleanup = cleanup_reviews[0] if cleanup_reviews else {}
        latest_package = ready_packages[0] if ready_packages else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "public_repository_polish_package_version": PUBLIC_REPOSITORY_POLISH_PACKAGE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "final_public_repository_polish_and_manual_screenshot_capture_package",
            "output_dir": str(self.packages_dir),
            "ready_cleanup_review_count": len(cleanup_reviews),
            "latest_cleanup_review_id": latest_cleanup.get("review_id", ""),
            "latest_cleanup_review_status": latest_cleanup.get("review_status", ""),
            "package_count": len(packages),
            "ready_package_count": len(ready_packages),
            "latest_package_id": latest_package.get("package_id", ""),
            "latest_package_status": latest_package.get("package_status", ""),
            "latest_required_failed_count": latest_package.get("required_failed_count", 0),
            "latest_public_readme_issue_count": latest_package.get("public_readme_issue_count", 0),
            "latest_screenshot_target_count": latest_package.get("screenshot_target_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_public_repository_polish" if cleanup_reviews else "waiting_for_public_readme_cleanup_review",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_package(self, body: dict | None = None) -> dict:
        body = body or {}
        cleanup_review_id = str(body.get("cleanup_review_id") or body.get("public_readme_cleanup_review_id") or body.get("review_id") or "").strip()
        if not cleanup_review_id:
            cleanup_reviews = self.ready_cleanup_reviews(20)
            cleanup_review_id = str(cleanup_reviews[0].get("review_id") or "") if cleanup_reviews else ""
        if not cleanup_review_id:
            return self.error("public_repository_polish_package_input_missing", "A ready public README cleanup review is required.")
        cleanup_review = self.resolve_cleanup_review(cleanup_review_id)
        if cleanup_review.get("error"):
            return cleanup_review
        if cleanup_review.get("review_readiness") != "ready_for_public_readme_cleanup_review":
            return self.error("public_repository_polish_package_not_ready", "Public README cleanup review must be ready_for_public_readme_cleanup_review.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        final_readme = self.final_public_readme(cleanup_review, validation, manifest)
        file_plan = self.repository_file_plan(cleanup_review, validation, api_contract, manifest)
        screenshot_package = self.manual_screenshot_package(cleanup_review, manifest)
        sharing_checklist = self.public_sharing_checklist(cleanup_review, validation, api_contract, manifest, final_readme, screenshot_package)
        boundary_checks = self.boundary_checks(cleanup_review, validation, api_contract, manifest, final_readme, file_plan, screenshot_package, sharing_checklist)
        required_failed = [row for row in boundary_checks if row.get("required") and row.get("status") != "ready"]
        public_readme_issues = [row for row in boundary_checks if row.get("category") == "public_readme" and row.get("required") and row.get("status") != "ready"]
        package_status = "ready_with_manual_screenshot_tasks"
        if required_failed:
            package_status = "needs_public_repository_polish"
        if not self.api_and_validation_ready(validation, api_contract):
            package_status = "pending_validation_or_api_contract"

        stamp = utc_now()
        package_id = f"public_repository_polish_package_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        package_dir = self.package_dir(package_id)
        manifest_path = package_dir / "public_repository_polish_package_manifest.json"
        summary_path = package_dir / "FINAL_PUBLIC_REPOSITORY_POLISH.md"
        file_plan_path = package_dir / "PUBLIC_REPOSITORY_FILE_PLAN.md"
        screenshot_path = package_dir / "MANUAL_SCREENSHOT_CAPTURE_PACKAGE.md"
        checklist_path = package_dir / "PUBLIC_SHARING_CHECKLIST.md"
        readme_path = package_dir / "PUBLIC_REPOSITORY_READY_README.md"
        html_path = package_dir / "public_repository_polish_package.html"
        zip_path = package_dir / "public_repository_polish_package.zip"
        latest_path = self.packages_dir / "latest_public_repository_polish_package.json"
        package = {
            "ok": True,
            "public_repository_polish_package_version": PUBLIC_REPOSITORY_POLISH_PACKAGE_VERSION,
            "package_id": package_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_repository_reviewer"),
            "notes": str(body.get("notes") or "Final public repository polish package before manual sharing."),
            "app_version": self.app_version,
            "cleanup_review_id": cleanup_review.get("review_id"),
            "package_readiness": "ready_for_public_repository_polish",
            "package_status": package_status,
            "required_failed_count": len(required_failed),
            "public_readme_issue_count": len(public_readme_issues),
            "screenshot_target_count": len(screenshot_package),
            "file_plan_count": len(file_plan),
            "sharing_check_count": len(sharing_checklist),
            "public_readme_has_local_absolute_paths": bool(LOCAL_ABSOLUTE_PATH_PATTERN.search(final_readme)),
            "public_readme_has_analysis_output_paths": "analysis_output" in final_readme.lower(),
            "boundary_checks": boundary_checks,
            "repository_file_plan": file_plan,
            "manual_screenshot_capture_package": screenshot_package,
            "public_sharing_checklist": sharing_checklist,
            "final_public_readme": final_readme,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "evidence_summary": self.evidence_summary(cleanup_review, validation, api_contract, manifest),
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "summary": str(summary_path),
                "file_plan": str(file_plan_path),
                "manual_screenshot_capture_package": str(screenshot_path),
                "public_sharing_checklist": str(checklist_path),
                "public_repository_ready_readme": str(readme_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, package)
        write_json(latest_path, package)
        summary_path.write_text(self.summary_markdown(package), encoding="utf-8", newline="\n")
        file_plan_path.write_text(self.file_plan_markdown(package), encoding="utf-8", newline="\n")
        screenshot_path.write_text(self.screenshot_markdown(package), encoding="utf-8", newline="\n")
        checklist_path.write_text(self.checklist_markdown(package), encoding="utf-8", newline="\n")
        readme_path.write_text(final_readme, encoding="utf-8", newline="\n")
        html_path.write_text(self.package_html(package), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, summary_path, file_plan_path, screenshot_path, checklist_path, readme_path, html_path])
        package["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, package)
        write_json(latest_path, package)
        return {"ok": True, "package": package, "source_gis_modified": False, "mutates_config": False}

    def list_packages(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.packages_dir.exists():
            return rows
        manifests = sorted(
            self.packages_dir.glob("public_repository_polish_package_*/public_repository_polish_package_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("public_repository_polish_package_version") != PUBLIC_REPOSITORY_POLISH_PACKAGE_VERSION:
                continue
            rows.append({
                "package_id": payload.get("package_id"),
                "created_at": payload.get("created_at"),
                "package_readiness": payload.get("package_readiness"),
                "package_status": payload.get("package_status"),
                "cleanup_review_id": payload.get("cleanup_review_id"),
                "required_failed_count": payload.get("required_failed_count", 0),
                "public_readme_issue_count": payload.get("public_readme_issue_count", 0),
                "screenshot_target_count": payload.get("screenshot_target_count", 0),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, package_id: str) -> dict:
        token = safe_token(package_id)
        path = self.package_dir(token) / "public_repository_polish_package_manifest.json"
        payload = read_json(path)
        if not payload:
            return self.error("public_repository_polish_package_not_found", "Public repository polish package was not found.")
        return payload

    def output_file(self, package_id: str, file_key: str = "zip") -> dict:
        detail = self.detail(package_id)
        if detail.get("error"):
            return detail
        files = detail.get("files", {}) if isinstance(detail.get("files"), dict) else {}
        path = Path(str(files.get(file_key) or ""))
        if not path.exists():
            return self.error("public_repository_polish_package_output_not_found", "Requested public repository polish package output was not found.")
        return {"ok": True, "path": path, "package_id": detail.get("package_id"), "file_key": file_key}

    def ready_cleanup_reviews(self, limit: int = 20) -> list[dict]:
        rows = safe_call(lambda: self.public_readme_cleanup_review.list_reviews(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("review_readiness") == "ready_for_public_readme_cleanup_review"]

    def resolve_cleanup_review(self, review_id: str) -> dict:
        detail = safe_call(lambda: self.public_readme_cleanup_review.detail(review_id), {})
        return detail if isinstance(detail, dict) else self.error("public_readme_cleanup_review_not_found", "Public README cleanup review detail failed.")

    def api_and_validation_ready(self, validation: dict, api_contract: dict) -> bool:
        return validation.get("passed") is True and api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints

    def final_public_readme(self, cleanup_review: dict, validation: dict, manifest: dict) -> str:
        generators = validation.get("generators", 0)
        crossings = validation.get("crossings", 0)
        route_rows = validation.get("route_aware_rows", 0)
        local_url = manifest.get("local_url", "http://127.0.0.1:8847") if isinstance(manifest, dict) else "http://127.0.0.1:8847"
        return "\n".join([
            "# GeoReview Studio",
            "",
            "Local-first GIS review workbench for infrastructure risk indicators, OSM data-quality evidence, and portfolio-ready spatial analytics.",
            "",
            "## What This Project Shows",
            "",
            "- Reusable GIS/OSM ingestion and profile execution architecture.",
            "- Safe Access pedestrian infrastructure review as the first implemented analysis profile.",
            "- Route-aware Kfar Saba pilot outputs with transparent scoring rules.",
            "- Release-readiness, API contract, reproducibility, and repository publication evidence.",
            "",
            "## Current Evidence",
            "",
            "- Default pilot: `Kfar Saba`",
            f"- Pedestrian generators: `{generators}`",
            f"- Mapped crossings: `{crossings}`",
            f"- Route-aware review rows: `{route_rows}`",
            f"- Public README cleanup review: `{cleanup_review.get('review_id', '')}`",
            "",
            "Approved wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Repository Guide",
            "",
            "- `docs/ARCHITECTURE.md`",
            "- `docs/DATA_BOUNDARY.md`",
            "- `docs/API_CONTRACT.md`",
            "- `docs/PORTFOLIO_WALKTHROUGH.md`",
            "- `portfolio/case_study.md`",
            "- `docs/screenshots/dashboard-overview.png`",
            "- `docs/screenshots/release-readiness.png`",
            "- `docs/screenshots/public-repository-polish-package.png`",
            "",
            "## Run Locally",
            "",
            "```powershell",
            "python -B backend/app.py",
            "```",
            "",
            f"Open `{local_url}` after starting the local server.",
            "",
            "## Data Boundary",
            "",
            "- Source GIS files are not included in the public repository package.",
            "- Generated screenshots and small CSV/JSON/Markdown evidence can be shared after manual review.",
            "- Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "- This project is not a crash prediction model.",
            "",
        ])

    def repository_file_plan(self, cleanup_review: dict, validation: dict, api_contract: dict, manifest: dict) -> list[dict]:
        return [
            self.file_row("README.md", "include", "Final public project overview with claim boundary and local run command.", True),
            self.file_row(".gitignore", "include", "Public package hygiene rules for logs, caches, secrets and source GIS.", True),
            self.file_row("backend/", "include", "Local API and evidence builders.", True),
            self.file_row("frontend/static/", "include", "Local dashboard UI.", True),
            self.file_row("docs/", "include", "Architecture, API, data boundary, testing and publication evidence docs.", True),
            self.file_row("portfolio/", "include", "Case study and portfolio narrative artifacts.", True),
            self.file_row("config/", "include", "Non-secret scoring/profile/schema planning configs.", True),
            self.file_row("tests/", "include", "Validation and API contract tests.", True),
            self.file_row("docs/screenshots/*.png", "include_after_manual_capture", "Manual screenshot evidence referenced by README.", False),
            self.file_row("source GIS files", "exclude", "Original OSM/PBF/shapefile/GeoPackage data stays local-only.", True),
            self.file_row("local generated analysis folders", "exclude", "Large generated evidence remains local unless curated into small docs/screenshots.", True),
            self.file_row("server_*.log and *.log", "exclude", "Local runtime logs are noisy machine-specific evidence, not public source.", True),
            self.file_row("ui_review/chrome_profile*/", "exclude", "Browser profile/cache state is temporary and can contain machine-specific state.", True),
            self.file_row("__pycache__/ and *.pyc", "exclude", "Runtime bytecode cache is not public source.", True),
            self.file_row("temp/cache/profile/session files", "exclude", "Local execution state must not be packaged for GitHub.", True),
            self.file_row("secrets and environment files", "exclude", "No credentials or environment-specific auth material.", True),
        ]

    @staticmethod
    def file_row(path: str, action: str, reason: str, required: bool) -> dict:
        return {"path": path, "action": action, "reason": reason, "required": required}

    def manual_screenshot_package(self, cleanup_review: dict, manifest: dict) -> list[dict]:
        local_url = manifest.get("local_url", "http://127.0.0.1:8847") if isinstance(manifest, dict) else "http://127.0.0.1:8847"
        rows = cleanup_review.get("screenshot_evidence_checklist", [])
        if not isinstance(rows, list) or len(rows) < 8:
            rows = []
        normalized = []
        for row in rows[:12]:
            relative_path = str(row.get("relative_path") or "")
            if not relative_path.startswith("docs/screenshots/"):
                relative_path = f"docs/screenshots/{safe_token(row.get('target'), 'screenshot')}.png"
            route = str(row.get("route") or local_url)
            if route.startswith("http://127.0.0.1:8843"):
                route = route.replace("http://127.0.0.1:8843", local_url)
            normalized.append({
                "target": str(row.get("target") or safe_token(relative_path)),
                "route": route,
                "relative_path": relative_path,
                "capture_status": "manual_capture_required",
                "review_note": str(row.get("evidence") or "Capture after final local smoke review."),
            })
        if normalized:
            return normalized
        return [
            {"target": "dashboard_overview", "route": local_url, "relative_path": "docs/screenshots/dashboard-overview.png", "capture_status": "manual_capture_required", "review_note": "Main dashboard evidence."},
            {"target": "release_readiness", "route": f"{local_url}/api/release-readiness", "relative_path": "docs/screenshots/release-readiness.png", "capture_status": "manual_capture_required", "review_note": "Release gates evidence."},
            {"target": "api_contract", "route": "api_contract_summary.json", "relative_path": "docs/screenshots/api-contract-summary.png", "capture_status": "manual_capture_required", "review_note": "API coverage evidence."},
            {"target": "public_repository_polish_package", "route": "/api/public-repository-polish-package", "relative_path": "docs/screenshots/public-repository-polish-package.png", "capture_status": "manual_capture_required", "review_note": "Final repository package evidence."},
            {"target": "portfolio_case_study", "route": "portfolio/case_study.md", "relative_path": "docs/screenshots/portfolio-case-study.png", "capture_status": "manual_capture_required", "review_note": "Portfolio story evidence."},
            {"target": "source_onboarding", "route": f"{local_url}#source-onboarding", "relative_path": "docs/screenshots/source-onboarding.png", "capture_status": "manual_capture_required", "review_note": "Local source review evidence."},
            {"target": "route_aware_candidates", "route": f"{local_url}#route-aware-candidates", "relative_path": "docs/screenshots/route-aware-candidates.png", "capture_status": "manual_capture_required", "review_note": "Route-aware candidate table evidence."},
            {"target": "data_boundary", "route": "docs/DATA_BOUNDARY.md", "relative_path": "docs/screenshots/data-boundary.png", "capture_status": "manual_capture_required", "review_note": "Source GIS exclusion evidence."},
        ]

    def public_sharing_checklist(self, cleanup_review: dict, validation: dict, api_contract: dict, manifest: dict, final_readme: str, screenshots: list[dict]) -> list[dict]:
        return [
            self.check("README uses repository-relative paths", "docs/" in final_readme and "portfolio/" in final_readme, True, "public_readme", "Keep public docs and screenshot references relative."),
            self.check("README has no local absolute paths", not LOCAL_ABSOLUTE_PATH_PATTERN.search(final_readme), True, "public_readme", "Remove local machine paths from public README."),
            self.check("README has no analysis_output references", "analysis_output" not in final_readme.lower(), True, "public_readme", "Keep local generated folders out of public README."),
            self.check("Source GIS remains excluded", cleanup_review.get("includes_source_gis") is False, True, "data_boundary", "Do not include source GIS in public repository package."),
            self.check("Validation summary passed", validation.get("passed") is True, True, "validation", "Run validation before sharing."),
            self.check("API contract is current", api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints, False, "validation", "Run API contract after final package changes."),
            self.check("Manual screenshot targets are listed", len(screenshots) >= 8, True, "screenshots", "Capture all manual screenshots before public sharing."),
            self.check("Approved wording is present", self.review_wording in final_readme, True, "claims", "Keep infrastructure indicator wording visible."),
        ]

    def boundary_checks(self, cleanup_review: dict, validation: dict, api_contract: dict, manifest: dict, final_readme: str, file_plan: list[dict], screenshots: list[dict], checklist: list[dict]) -> list[dict]:
        checks = list(checklist)
        checks.extend([
            self.check("Cleanup review is ready", cleanup_review.get("review_readiness") == "ready_for_public_readme_cleanup_review", True, "dependency", "Create a ready public README cleanup review first."),
            self.check("Cleanup review required checks passed", int(cleanup_review.get("required_failed_count") or 0) == 0, True, "dependency", "Resolve cleanup required checks first."),
            self.check("Cleanup review README issues are zero", int(cleanup_review.get("public_readme_issue_count") or 0) == 0, True, "dependency", "Resolve public README cleanup issues first."),
            self.check("Repository file plan has explicit excludes", any(row.get("action") == "exclude" and "source gis" in str(row.get("path", "")).lower() for row in file_plan), True, "data_boundary", "Keep public file plan explicit about source GIS exclusion."),
            self.check("Manifest points to current local URL", str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).endswith("8847"), True, "release", f"Update manifest for {self.app_version}."),
            self.check("Manual screenshot package uses relative paths", all(str(row.get("relative_path", "")).startswith("docs/screenshots/") for row in screenshots), True, "screenshots", "Keep screenshot paths repository-relative."),
        ])
        return checks

    @staticmethod
    def check(name: str, passed: bool, required: bool, category: str, recommendation: str) -> dict:
        return {
            "check": name,
            "category": category,
            "required": required,
            "status": "ready" if passed else ("needs_fix" if required else "reviewer_attention"),
            "recommendation": recommendation,
        }

    def evidence_summary(self, cleanup_review: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        return {
            "cleanup_review_id": cleanup_review.get("review_id"),
            "cleanup_review_status": cleanup_review.get("review_status"),
            "cleanup_review_required_failed": cleanup_review.get("required_failed_count"),
            "cleanup_review_public_readme_issues": cleanup_review.get("public_readme_issue_count"),
            "validation_passed": validation.get("passed") is True,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "api_contract_passed": api_contract.get("passed") is True,
            "api_contract_checked_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
            "review_wording": self.review_wording,
        }

    def claim_boundaries(self) -> list[str]:
        return [
            self.review_wording,
            "The workflow prioritizes field review using infrastructure indicators and data-quality evidence.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "The public repository package is a curated software artifact and does not redistribute source GIS data.",
        ]

    def summary_markdown(self, package: dict) -> str:
        lines = [
            "# Final Public Repository Polish Package",
            "",
            f"- Package ID: `{package.get('package_id')}`",
            f"- App version: `{package.get('app_version')}`",
            f"- Package readiness: `{package.get('package_readiness')}`",
            f"- Package status: `{package.get('package_status')}`",
            f"- Required failed checks: `{package.get('required_failed_count')}`",
            f"- Public README issue count: `{package.get('public_readme_issue_count')}`",
            f"- Screenshot targets: `{package.get('screenshot_target_count')}`",
            f"- Cleanup review: `{package.get('cleanup_review_id')}`",
            "",
            "## Boundary Checks",
            "",
            "| Check | Category | Required | Status | Recommendation |",
            "|---|---|---:|---|---|",
        ]
        for row in package.get("boundary_checks", []):
            lines.append(f"| {row.get('check')} | `{row.get('category')}` | `{row.get('required')}` | `{row.get('status')}` | {row.get('recommendation')} |")
        lines.extend(["", "## Claim Boundary", "", self.review_wording, ""])
        return "\n".join(lines)

    def file_plan_markdown(self, package: dict) -> str:
        lines = [
            "# Public Repository File Plan",
            "",
            "| Path | Action | Required | Reason |",
            "|---|---|---:|---|",
        ]
        for row in package.get("repository_file_plan", []):
            lines.append(f"| `{row.get('path')}` | `{row.get('action')}` | `{row.get('required')}` | {row.get('reason')} |")
        lines.append("")
        return "\n".join(lines)

    def screenshot_markdown(self, package: dict) -> str:
        lines = [
            "# Manual Screenshot Capture Package",
            "",
            "Capture these screenshots manually after the local v083 server is running. Paths are repository-relative and source GIS data is not included.",
            "",
            "| Target | Route | Relative path | Status | Review note |",
            "|---|---|---|---|---|",
        ]
        for row in package.get("manual_screenshot_capture_package", []):
            lines.append(f"| `{row.get('target')}` | `{row.get('route')}` | `{row.get('relative_path')}` | `{row.get('capture_status')}` | {row.get('review_note')} |")
        lines.append("")
        return "\n".join(lines)

    def checklist_markdown(self, package: dict) -> str:
        lines = [
            "# Public Sharing Checklist",
            "",
            "| Check | Category | Required | Status | Recommendation |",
            "|---|---|---:|---|---|",
        ]
        for row in package.get("public_sharing_checklist", []):
            lines.append(f"| {row.get('check')} | `{row.get('category')}` | `{row.get('required')}` | `{row.get('status')}` | {row.get('recommendation')} |")
        lines.append("")
        return "\n".join(lines)

    def package_html(self, package: dict) -> str:
        checks = "".join(f"<tr><td>{html.escape(str(row.get('check') or ''))}</td><td>{html.escape(str(row.get('status') or ''))}</td><td>{html.escape(str(row.get('recommendation') or ''))}</td></tr>" for row in package.get("boundary_checks", []))
        files = "".join(f"<tr><td>{html.escape(str(row.get('path') or ''))}</td><td>{html.escape(str(row.get('action') or ''))}</td><td>{html.escape(str(row.get('reason') or ''))}</td></tr>" for row in package.get("repository_file_plan", []))
        screenshots = "".join(f"<tr><td>{html.escape(str(row.get('target') or ''))}</td><td>{html.escape(str(row.get('relative_path') or ''))}</td><td>{html.escape(str(row.get('capture_status') or ''))}</td></tr>" for row in package.get("manual_screenshot_capture_package", []))
        return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\" /><title>Final Public Repository Polish Package</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;line-height:1.45;color:#1f2933}}table{{border-collapse:collapse;width:100%;margin:16px 0}}td,th{{border:1px solid #c8d0d9;padding:8px;text-align:left}}code{{background:#eef2f6;padding:2px 4px}}</style></head>
<body>
<h1>Final Public Repository Polish Package</h1>
<p><b>Package:</b> <code>{html.escape(str(package.get("package_id") or ""))}</code></p>
<p><b>Status:</b> {html.escape(str(package.get("package_status") or ""))}; <b>required failed:</b> <code>{html.escape(str(package.get("required_failed_count") or 0))}</code>; <b>screenshots:</b> <code>{html.escape(str(package.get("screenshot_target_count") or 0))}</code>.</p>
<h2>Boundary Checks</h2><table><thead><tr><th>Check</th><th>Status</th><th>Recommendation</th></tr></thead><tbody>{checks}</tbody></table>
<h2>Repository File Plan</h2><table><thead><tr><th>Path</th><th>Action</th><th>Reason</th></tr></thead><tbody>{files}</tbody></table>
<h2>Manual Screenshot Capture</h2><table><thead><tr><th>Target</th><th>Relative path</th><th>Status</th></tr></thead><tbody>{screenshots}</tbody></table>
<p>{html.escape(self.review_wording)}</p>
</body></html>"""

    def write_zip(self, zip_path: Path, files: list[Path]) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                if path.exists():
                    zf.write(path, arcname=path.name)

    def package_dir(self, package_id: str) -> Path:
        return self.packages_dir / safe_token(package_id)

    @staticmethod
    def error(code: str, detail: str) -> dict:
        return {"ok": False, "error": code, "detail": detail, "source_gis_modified": False, "mutates_config": False}

