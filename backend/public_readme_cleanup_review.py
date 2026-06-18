from __future__ import annotations

import html
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PUBLIC_README_CLEANUP_REVIEW_VERSION = "public_readme_cleanup_review_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
LOCAL_ABSOLUTE_PATH_PATTERN = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\"'<>|\r\n]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "public_readme_cleanup_review", max_len: int = 150) -> str:
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
        return {"error": "public_readme_cleanup_review_probe_failed", "detail": repr(exc)}


class PublicReadmeCleanupReviewBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        repository_final_package_review: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.repository_final_package_review = repository_final_package_review
        self.expected_api_endpoints = expected_api_endpoints
        self.reviews_dir = output_root / "georeview_studio_public_readme_cleanup_reviews"

    def status(self) -> dict:
        final_reviews = self.ready_final_package_reviews(100)
        reviews = self.list_reviews(100)
        ready_reviews = [row for row in reviews if row.get("review_readiness") == "ready_for_public_readme_cleanup_review"]
        latest_final = final_reviews[0] if final_reviews else {}
        latest_review = ready_reviews[0] if ready_reviews else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "public_readme_cleanup_review_version": PUBLIC_README_CLEANUP_REVIEW_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "public_readme_path_cleanup_and_screenshot_evidence",
            "output_dir": str(self.reviews_dir),
            "ready_final_package_review_count": len(final_reviews),
            "latest_final_package_review_id": latest_final.get("review_id", ""),
            "latest_final_package_review_status": latest_final.get("review_status", ""),
            "review_count": len(reviews),
            "ready_review_count": len(ready_reviews),
            "latest_review_id": latest_review.get("review_id", ""),
            "latest_review_status": latest_review.get("review_status", ""),
            "latest_required_failed_count": latest_review.get("required_failed_count", 0),
            "latest_public_readme_issue_count": latest_review.get("public_readme_issue_count", 0),
            "latest_screenshot_evidence_count": latest_review.get("screenshot_evidence_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_public_readme_cleanup_review" if final_reviews else "waiting_for_repository_final_package_review",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_review(self, body: dict | None = None) -> dict:
        body = body or {}
        final_review_id = str(body.get("final_package_review_id") or body.get("repository_final_package_review_id") or body.get("review_id") or "").strip()
        if not final_review_id:
            final_reviews = self.ready_final_package_reviews(20)
            final_review_id = str(final_reviews[0].get("review_id") or "") if final_reviews else ""
        if not final_review_id:
            return self.error("public_readme_cleanup_review_input_missing", "A ready repository final package review is required.")
        final_review = self.resolve_final_package_review(final_review_id)
        if final_review.get("error"):
            return final_review
        if final_review.get("review_readiness") != "ready_for_repository_final_package_review":
            return self.error("public_readme_cleanup_review_not_ready", "Repository final package review must be ready_for_repository_final_package_review.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        readme_draft = self.public_readme_draft(final_review, validation, manifest)
        path_cleanup = self.path_cleanup_checks(readme_draft, final_review)
        screenshot_evidence = self.screenshot_evidence_checklist(validation, manifest, final_review)
        boundary_checks = self.boundary_checks(final_review, validation, api_contract, manifest, path_cleanup, screenshot_evidence, readme_draft)
        required_failed = [row for row in boundary_checks if row.get("required") and row.get("status") != "ready"]
        public_readme_issues = [row for row in path_cleanup if row.get("required") and row.get("status") != "ready"]
        review_status = "ready_with_reviewer_attention_items"
        if required_failed:
            review_status = "needs_public_readme_cleanup"
        if not self.api_and_validation_ready(validation, api_contract):
            review_status = "pending_validation_or_api_contract"

        stamp = utc_now()
        review_id = f"public_readme_cleanup_review_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        review_dir = self.review_dir(review_id)
        manifest_path = review_dir / "public_readme_cleanup_review_manifest.json"
        review_path = review_dir / "PUBLIC_README_CLEANUP_REVIEW.md"
        readme_path = review_dir / "PUBLIC_README_DRAFT.md"
        screenshot_path = review_dir / "SCREENSHOT_EVIDENCE_CHECKLIST.md"
        html_path = review_dir / "public_readme_cleanup_review.html"
        zip_path = review_dir / "public_readme_cleanup_review.zip"
        latest_path = self.reviews_dir / "latest_public_readme_cleanup_review.json"
        review = {
            "ok": True,
            "public_readme_cleanup_review_version": PUBLIC_README_CLEANUP_REVIEW_VERSION,
            "review_id": review_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_repository_reviewer"),
            "notes": str(body.get("notes") or "Public README cleanup and screenshot evidence review before sharing."),
            "app_version": self.app_version,
            "final_package_review_id": final_review.get("review_id"),
            "review_readiness": "ready_for_public_readme_cleanup_review",
            "review_status": review_status,
            "path_cleanup_check_count": len(path_cleanup),
            "screenshot_evidence_count": len(screenshot_evidence),
            "boundary_check_count": len(boundary_checks),
            "required_failed_count": len(required_failed),
            "public_readme_issue_count": len(public_readme_issues),
            "public_readme_has_local_absolute_paths": bool(LOCAL_ABSOLUTE_PATH_PATTERN.search(readme_draft)),
            "public_readme_has_analysis_output_paths": "analysis_output" in readme_draft.lower(),
            "path_cleanup_checks": path_cleanup,
            "screenshot_evidence_checklist": screenshot_evidence,
            "boundary_checks": boundary_checks,
            "public_readme_draft": readme_draft,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "evidence_summary": self.evidence_summary(final_review, validation, api_contract, manifest),
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "review": str(review_path),
                "public_readme_draft": str(readme_path),
                "screenshot_evidence_checklist": str(screenshot_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, review)
        write_json(latest_path, review)
        review_path.write_text(self.review_markdown(review), encoding="utf-8", newline="\n")
        readme_path.write_text(readme_draft, encoding="utf-8", newline="\n")
        screenshot_path.write_text(self.screenshot_markdown(review), encoding="utf-8", newline="\n")
        html_path.write_text(self.review_html(review), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, review_path, readme_path, screenshot_path, html_path])
        review["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, review)
        write_json(latest_path, review)
        return {"ok": True, "review": review, "source_gis_modified": False, "mutates_config": False}

    def list_reviews(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.reviews_dir.exists():
            return rows
        manifests = sorted(
            self.reviews_dir.glob("public_readme_cleanup_review_*/public_readme_cleanup_review_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("public_readme_cleanup_review_version") != PUBLIC_README_CLEANUP_REVIEW_VERSION:
                continue
            rows.append({
                "review_id": payload.get("review_id"),
                "created_at": payload.get("created_at"),
                "review_readiness": payload.get("review_readiness"),
                "review_status": payload.get("review_status"),
                "final_package_review_id": payload.get("final_package_review_id"),
                "required_failed_count": payload.get("required_failed_count", 0),
                "public_readme_issue_count": payload.get("public_readme_issue_count", 0),
                "screenshot_evidence_count": payload.get("screenshot_evidence_count", 0),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, review_id: str) -> dict:
        token = safe_token(review_id)
        path = self.review_dir(token) / "public_readme_cleanup_review_manifest.json"
        payload = read_json(path)
        if not payload:
            return self.error("public_readme_cleanup_review_not_found", "Public README cleanup review was not found.")
        return payload

    def output_file(self, review_id: str, file_key: str = "zip") -> dict:
        detail = self.detail(review_id)
        if detail.get("error"):
            return detail
        files = detail.get("files", {}) if isinstance(detail.get("files"), dict) else {}
        path = Path(str(files.get(file_key) or ""))
        if not path.exists():
            return self.error("public_readme_cleanup_review_output_not_found", "Requested public README cleanup review output was not found.")
        return {"ok": True, "path": path, "review_id": detail.get("review_id"), "file_key": file_key}

    def ready_final_package_reviews(self, limit: int = 20) -> list[dict]:
        rows = safe_call(lambda: self.repository_final_package_review.list_reviews(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("review_readiness") == "ready_for_repository_final_package_review"]

    def resolve_final_package_review(self, review_id: str) -> dict:
        detail = safe_call(lambda: self.repository_final_package_review.detail(review_id), {})
        return detail if isinstance(detail, dict) else self.error("repository_final_package_review_not_found", "Repository final package review detail failed.")

    def api_and_validation_ready(self, validation: dict, api_contract: dict) -> bool:
        return validation.get("passed") is True and api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints

    def public_readme_draft(self, final_review: dict, validation: dict, manifest: dict) -> str:
        generators = validation.get("generators", 0)
        crossings = validation.get("crossings", 0)
        route_rows = validation.get("route_aware_rows", 0)
        return "\n".join([
            "# GeoReview Studio",
            "",
            "GeoReview Studio is a local-first GIS review workbench for infrastructure risk indicators and data-quality evidence.",
            "",
            "## Portfolio Scope",
            "",
            "- Default pilot: Kfar Saba",
            f"- Pedestrian generators: `{generators}`",
            f"- Mapped crossings: `{crossings}`",
            f"- Route-aware review rows: `{route_rows}`",
            "- Source GIS files are not included in this public repository package.",
            "- Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "",
            "Approved wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Repository Evidence",
            "",
            "- `docs/ARCHITECTURE.md`",
            "- `docs/DATA_BOUNDARY.md`",
            "- `docs/API_CONTRACT.md`",
            "- `portfolio/case_study.md`",
            "- `docs/screenshots/dashboard-overview.png`",
            "- `docs/screenshots/release-readiness.png`",
            "- `docs/screenshots/repository-final-package-review.png`",
            "- `docs/screenshots/public-readme-cleanup-review.png`",
            "",
            "## Run Locally",
            "",
            "```powershell",
            "python -B backend/app.py",
            "```",
            "",
            f"Open `{manifest.get('local_url', 'http://127.0.0.1:8847')}` after starting the local server.",
            "",
            "## Publication Boundary",
            "",
            f"- Final package review: `{final_review.get('review_id', '')}`",
            "- Public repository paths should stay relative to the repository root.",
            "- Private local paths belong only in internal evidence files or redacted examples.",
            "- This project is not a crash prediction model.",
            "",
        ])

    def path_cleanup_checks(self, readme_draft: str, final_review: dict) -> list[dict]:
        lower = readme_draft.lower()
        source_tokens = (".osm.pbf", ".shp.zip", ".gpkg", ".dbf", ".prj", "source_data/")
        return [
            self.check("No local absolute paths in public README draft", not LOCAL_ABSOLUTE_PATH_PATTERN.search(readme_draft), True, "Replace local Windows paths with repository-relative paths or redacted placeholders."),
            self.check("No analysis_output paths in public README draft", "analysis_output" not in lower, True, "Keep generated local evidence paths out of public README text."),
            self.check("No source GIS filenames in public README draft", not any(token in lower for token in source_tokens), True, "Do not advertise source GIS files as repository contents."),
            self.check("Repository-relative docs references are present", "docs/" in readme_draft and "portfolio/" in readme_draft, True, "Use repository-relative docs and portfolio paths."),
            self.check("Screenshot references are repository-relative", "docs/screenshots/" in readme_draft, True, "Store screenshots under a relative docs/screenshots path after manual capture."),
            self.check("Final package review had clean public paths", int(final_review.get("public_path_issue_count") or 0) == 0, True, "Resolve final package public path issues first."),
            self.check("Redacted path evidence remains available", int(final_review.get("redacted_path_count") or 0) >= 1, True, "Keep redacted local path evidence for reviewer context."),
        ]

    def screenshot_evidence_checklist(self, validation: dict, manifest: dict, final_review: dict) -> list[dict]:
        local_url = manifest.get("local_url", "http://127.0.0.1:8847") if isinstance(manifest, dict) else "http://127.0.0.1:8847"
        return [
            {"target": "dashboard_overview", "route": local_url, "relative_path": "docs/screenshots/dashboard-overview.png", "status": "manual_capture_required", "evidence": f"{validation.get('generators', 0)} generator rows and {validation.get('crossings', 0)} crossings."},
            {"target": "route_aware_candidates", "route": f"{local_url}#route-aware-candidates", "relative_path": "docs/screenshots/route-aware-candidates.png", "status": "manual_capture_required", "evidence": f"{validation.get('route_aware_rows', 0)} route-aware rows."},
            {"target": "source_onboarding", "route": f"{local_url}#source-onboarding", "relative_path": "docs/screenshots/source-onboarding.png", "status": "manual_capture_required", "evidence": "Source scan evidence without source GIS redistribution."},
            {"target": "release_readiness", "route": f"{local_url}/api/release-readiness", "relative_path": "docs/screenshots/release-readiness.png", "status": "manual_capture_required", "evidence": "Release gates and validation evidence."},
            {"target": "api_contract", "route": "api_contract_summary.json", "relative_path": "docs/screenshots/api-contract-summary.png", "status": "manual_capture_required", "evidence": f"Expected endpoints: {self.expected_api_endpoints}."},
            {"target": "repository_final_package_review", "route": f"/api/repository-final-package-review/reviews/{final_review.get('review_id', '')}", "relative_path": "docs/screenshots/repository-final-package-review.png", "status": "manual_capture_required", "evidence": "Final package review and redacted path evidence."},
            {"target": "public_readme_cleanup_review", "route": "/api/public-readme-cleanup-review", "relative_path": "docs/screenshots/public-readme-cleanup-review.png", "status": "manual_capture_required", "evidence": "Public README cleanup and screenshot checklist evidence."},
            {"target": "portfolio_case_study", "route": "portfolio/case_study.md", "relative_path": "docs/screenshots/portfolio-case-study.png", "status": "manual_capture_required", "evidence": "Portfolio story and claim boundary."},
        ]

    def boundary_checks(self, final_review: dict, validation: dict, api_contract: dict, manifest: dict, path_cleanup: list[dict], screenshot_evidence: list[dict], readme_draft: str) -> list[dict]:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        failed_cleanup = [row for row in path_cleanup if row.get("required") and row.get("status") != "ready"]
        return [
            self.check("Repository final package review is ready", final_review.get("review_readiness") == "ready_for_repository_final_package_review", True, "Create repository final package review first."),
            self.check("Final package required checks passed", int(final_review.get("required_failed_count") or 0) == 0, True, "Resolve final package required checks."),
            self.check("Validation summary passed", validation.get("passed") is True, True, "Run validation before public README cleanup."),
            self.check("API contract evidence available", api_contract.get("passed") is True and api_checked >= max(1, self.expected_api_endpoints - 5), False, f"Run API contract after adding {self.app_version} endpoints."),
            self.check("Manifest points to current local release", str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).endswith("8847"), True, f"Update manifest for {self.app_version}."),
            self.check("Public README draft is clean", len(failed_cleanup) == 0, True, "Resolve public README path cleanup checks."),
            self.check("Screenshot evidence checklist is complete", len(screenshot_evidence) >= 8 and all(str(row.get("relative_path", "")).startswith("docs/screenshots/") for row in screenshot_evidence), True, "Keep screenshot targets repository-relative."),
            self.check("Approved wording present", self.review_wording in readme_draft, True, "Keep claim boundary visible in the public README draft."),
            self.check("Source GIS remains excluded", final_review.get("includes_source_gis") is False, True, "Do not include source GIS files in public package plans."),
            self.check("Manual screenshot capture remains explicit", True, False, "Capture screenshots manually before external sharing."),
        ]

    @staticmethod
    def check(name: str, passed: bool, required: bool, recommendation: str) -> dict:
        return {"check": name, "required": required, "status": "ready" if passed else ("needs_fix" if required else "reviewer_attention"), "recommendation": recommendation}

    def evidence_summary(self, final_review: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        return {
            "final_package_review_id": final_review.get("review_id"),
            "final_package_review_status": final_review.get("review_status"),
            "final_package_required_failed": final_review.get("required_failed_count"),
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
            "Public README and screenshot references are packaging evidence, not new GIS source data.",
        ]

    def review_markdown(self, review: dict) -> str:
        lines = [
            "# Public README Cleanup Review",
            "",
            f"- Review ID: `{review.get('review_id')}`",
            f"- App version: `{review.get('app_version')}`",
            f"- Review readiness: `{review.get('review_readiness')}`",
            f"- Review status: `{review.get('review_status')}`",
            f"- Required failed checks: `{review.get('required_failed_count')}`",
            f"- Public README issue count: `{review.get('public_readme_issue_count')}`",
            f"- Screenshot evidence targets: `{review.get('screenshot_evidence_count')}`",
            f"- Final package review: `{review.get('final_package_review_id')}`",
            "",
            "## Boundary Checks",
            "",
            "| Check | Required | Status | Recommendation |",
            "|---|---:|---|---|",
        ]
        for row in review.get("boundary_checks", []):
            lines.append(f"| {row.get('check')} | `{row.get('required')}` | `{row.get('status')}` | {row.get('recommendation')} |")
        lines.extend(["", "## Public README Path Cleanup", "", "| Check | Required | Status | Recommendation |", "|---|---:|---|---|"])
        for row in review.get("path_cleanup_checks", []):
            lines.append(f"| {row.get('check')} | `{row.get('required')}` | `{row.get('status')}` | {row.get('recommendation')} |")
        lines.extend(["", "## Claim Boundary", "", self.review_wording, ""])
        return "\n".join(lines)

    def screenshot_markdown(self, review: dict) -> str:
        lines = [
            "# Screenshot Evidence Checklist",
            "",
            "These targets are repository-relative screenshot references for reviewer evidence. They are not source GIS data.",
            "",
            "| Target | Route | Relative path | Status | Evidence |",
            "|---|---|---|---|---|",
        ]
        for row in review.get("screenshot_evidence_checklist", []):
            lines.append(f"| `{row.get('target')}` | `{row.get('route')}` | `{row.get('relative_path')}` | `{row.get('status')}` | {row.get('evidence')} |")
        lines.append("")
        return "\n".join(lines)

    def review_html(self, review: dict) -> str:
        checks = "".join(f"<tr><td>{html.escape(str(row.get('check') or ''))}</td><td>{html.escape(str(row.get('status') or ''))}</td><td>{html.escape(str(row.get('recommendation') or ''))}</td></tr>" for row in review.get("boundary_checks", []))
        cleanup = "".join(f"<tr><td>{html.escape(str(row.get('check') or ''))}</td><td>{html.escape(str(row.get('status') or ''))}</td><td>{html.escape(str(row.get('recommendation') or ''))}</td></tr>" for row in review.get("path_cleanup_checks", []))
        screenshots = "".join(f"<tr><td>{html.escape(str(row.get('target') or ''))}</td><td>{html.escape(str(row.get('relative_path') or ''))}</td><td>{html.escape(str(row.get('status') or ''))}</td></tr>" for row in review.get("screenshot_evidence_checklist", []))
        return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\" /><title>Public README Cleanup Review</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;line-height:1.45;color:#1f2933}}table{{border-collapse:collapse;width:100%;margin:16px 0}}td,th{{border:1px solid #c8d0d9;padding:8px;text-align:left}}code{{background:#eef2f6;padding:2px 4px}}</style></head>
<body>
<h1>Public README Cleanup Review</h1>
<p><b>Review:</b> <code>{html.escape(str(review.get("review_id") or ""))}</code></p>
<p><b>Status:</b> {html.escape(str(review.get("review_status") or ""))}; <b>public README issues:</b> <code>{html.escape(str(review.get("public_readme_issue_count") or 0))}</code>; <b>screenshots:</b> <code>{html.escape(str(review.get("screenshot_evidence_count") or 0))}</code>.</p>
<h2>Boundary Checks</h2><table><thead><tr><th>Check</th><th>Status</th><th>Recommendation</th></tr></thead><tbody>{checks}</tbody></table>
<h2>Path Cleanup</h2><table><thead><tr><th>Check</th><th>Status</th><th>Recommendation</th></tr></thead><tbody>{cleanup}</tbody></table>
<h2>Screenshot Evidence</h2><table><thead><tr><th>Target</th><th>Relative path</th><th>Status</th></tr></thead><tbody>{screenshots}</tbody></table>
<p>{html.escape(self.review_wording)}</p>
</body></html>"""

    def write_zip(self, zip_path: Path, files: list[Path]) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                if path.exists():
                    zf.write(path, arcname=path.name)

    def review_dir(self, review_id: str) -> Path:
        return self.reviews_dir / safe_token(review_id)

    @staticmethod
    def error(code: str, detail: str) -> dict:
        return {"ok": False, "error": code, "detail": detail, "source_gis_modified": False, "mutates_config": False}

