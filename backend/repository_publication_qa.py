from __future__ import annotations

import html
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPOSITORY_PUBLICATION_QA_VERSION = "repository_publication_qa_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "repository_publication_qa", max_len: int = 150) -> str:
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
        return {"error": "repository_publication_qa_probe_failed", "detail": repr(exc)}


class RepositoryPublicationQABuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        github_publication_bundle: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.github_publication_bundle = github_publication_bundle
        self.expected_api_endpoints = expected_api_endpoints
        self.reviews_dir = output_root / "georeview_studio_repository_publication_qa"

    def status(self) -> dict:
        bundles = self.ready_publication_bundles(100)
        reviews = self.list_reviews(100)
        ready_reviews = [row for row in reviews if row.get("qa_readiness") == "ready_for_repository_publication_qa"]
        latest_bundle = bundles[0] if bundles else {}
        latest_review = ready_reviews[0] if ready_reviews else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "repository_publication_qa_version": REPOSITORY_PUBLICATION_QA_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "verify_repository_publication_readiness",
            "output_dir": str(self.reviews_dir),
            "ready_github_publication_bundle_count": len(bundles),
            "latest_github_publication_bundle_id": latest_bundle.get("bundle_id", ""),
            "latest_github_publication_bundle_status": latest_bundle.get("bundle_status", ""),
            "review_count": len(reviews),
            "ready_review_count": len(ready_reviews),
            "latest_review_id": latest_review.get("review_id", ""),
            "latest_review_status": latest_review.get("qa_status", ""),
            "latest_required_check_count": latest_review.get("required_check_count", 0),
            "latest_failed_required_check_count": latest_review.get("failed_required_check_count", 0),
            "latest_walkthrough_step_count": latest_review.get("walkthrough_step_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_repository_publication_qa" if bundles else "waiting_for_github_publication_bundle",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_review(self, body: dict | None = None) -> dict:
        body = body or {}
        bundle_id = str(body.get("bundle_id") or "").strip()
        if not bundle_id:
            bundles = self.ready_publication_bundles(20)
            bundle_id = str(bundles[0].get("bundle_id") or "") if bundles else ""
        if not bundle_id:
            return self.error("repository_publication_qa_input_missing", "A ready GitHub publication bundle is required.")
        bundle = self.resolve_bundle(bundle_id)
        if bundle.get("error"):
            return bundle
        if bundle.get("bundle_readiness") != "ready_for_github_publication_bundle":
            return self.error("repository_publication_qa_not_ready", "GitHub publication bundle must be ready_for_github_publication_bundle.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        checks = self.repository_checks(bundle, validation, api_contract, manifest)
        walkthrough = self.public_sharing_walkthrough(bundle, checks, validation, api_contract, manifest)
        required_checks = [row for row in checks if row.get("required")]
        failed_required = [row for row in required_checks if row.get("status") != "ready"]
        qa_status = "ready_for_public_repository_review"
        if failed_required:
            qa_status = "needs_repository_publication_fixes"
        if bundle.get("bundle_status") == "ready_with_reviewer_attention_items" and not failed_required:
            qa_status = "ready_with_reviewer_attention_items"
        if not self.api_and_validation_ready(validation, api_contract):
            qa_status = "pending_validation_or_api_contract"

        stamp = utc_now()
        review_id = f"repository_publication_qa_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        review_dir = self.review_dir(review_id)
        manifest_path = review_dir / "repository_publication_qa_manifest.json"
        checklist_path = review_dir / "REPOSITORY_QA_CHECKLIST.md"
        walkthrough_path = review_dir / "PUBLIC_SHARING_WALKTHROUGH.md"
        html_path = review_dir / "repository_publication_qa.html"
        zip_path = review_dir / "repository_publication_qa.zip"
        latest_path = self.reviews_dir / "latest_repository_publication_qa.json"
        review = {
            "ok": True,
            "repository_publication_qa_version": REPOSITORY_PUBLICATION_QA_VERSION,
            "review_id": review_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_repository_reviewer"),
            "notes": str(body.get("notes") or "Repository publication QA and public sharing walkthrough."),
            "app_version": self.app_version,
            "github_publication_bundle_id": bundle.get("bundle_id"),
            "qa_readiness": "ready_for_repository_publication_qa",
            "qa_status": qa_status,
            "required_check_count": len(required_checks),
            "failed_required_check_count": len(failed_required),
            "walkthrough_step_count": len(walkthrough),
            "repository_checks": checks,
            "public_sharing_walkthrough": walkthrough,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "evidence_summary": self.evidence_summary(bundle, validation, api_contract, manifest),
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "checklist": str(checklist_path),
                "walkthrough": str(walkthrough_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, review)
        write_json(latest_path, review)
        checklist_path.write_text(self.checklist_markdown(review), encoding="utf-8", newline="\n")
        walkthrough_path.write_text(self.walkthrough_markdown(review), encoding="utf-8", newline="\n")
        html_path.write_text(self.review_html(review), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, checklist_path, walkthrough_path, html_path])
        review["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, review)
        write_json(latest_path, review)
        return {"ok": True, "review": review, "source_gis_modified": False, "mutates_config": False}

    def list_reviews(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.reviews_dir.exists():
            return rows
        manifests = sorted(
            self.reviews_dir.glob("repository_publication_qa_*/repository_publication_qa_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("repository_publication_qa_version") != REPOSITORY_PUBLICATION_QA_VERSION:
                continue
            rows.append({
                "review_id": payload.get("review_id"),
                "created_at": payload.get("created_at"),
                "qa_readiness": payload.get("qa_readiness"),
                "qa_status": payload.get("qa_status"),
                "github_publication_bundle_id": payload.get("github_publication_bundle_id"),
                "required_check_count": payload.get("required_check_count", 0),
                "failed_required_check_count": payload.get("failed_required_check_count", 0),
                "walkthrough_step_count": payload.get("walkthrough_step_count", 0),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
                "download_url": f"/api/repository-publication-qa/reviews/{payload.get('review_id')}/download",
                "includes_source_gis": False,
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, review_id: str) -> dict:
        path = self.review_dir(review_id) / "repository_publication_qa_manifest.json"
        if not path.exists() or not self.safe_review_path(path):
            return {"ok": False, "error": "repository_publication_qa_not_found", "review_id": review_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "repository_publication_qa_not_found", "review_id": review_id, "source_gis_modified": False}
        return payload

    def output_file(self, review_id: str, output_id: str = "zip") -> dict:
        detail = self.detail(review_id)
        if detail.get("error"):
            return detail
        if output_id not in {"zip", "html", "checklist", "walkthrough"}:
            return {"ok": False, "error": "repository_publication_qa_output_not_found", "review_id": review_id, "output_id": output_id}
        key = output_id
        path = Path(str(detail.get("files", {}).get(key) or ""))
        if not path.exists() or not self.safe_review_path(path):
            return {"ok": False, "error": "repository_publication_qa_output_not_found", "review_id": review_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_publication_bundles(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.github_publication_bundle.list_bundles(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("bundle_readiness") == "ready_for_github_publication_bundle"]

    def resolve_bundle(self, bundle_id: str) -> dict:
        detail = safe_call(lambda: self.github_publication_bundle.detail(bundle_id), {})
        return detail if isinstance(detail, dict) else self.error("github_publication_bundle_not_found", "GitHub publication bundle detail failed.")

    def api_and_validation_ready(self, validation: dict, api_contract: dict) -> bool:
        return validation.get("passed") is True and api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints

    def repository_checks(self, bundle: dict, validation: dict, api_contract: dict, manifest: dict) -> list[dict]:
        files = bundle.get("files", {}) if isinstance(bundle.get("files"), dict) else {}
        readme = self.safe_read_text(Path(str(files.get("readme_export") or "")))
        case_study = self.safe_read_text(Path(str(files.get("case_study") or "")))
        repo_manifest = self.safe_read_text(Path(str(files.get("repo_manifest") or "")))
        zip_path = Path(str(files.get("zip") or ""))
        zip_names = self.zip_names(zip_path)
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        return [
            self.check("README_public.md generated", bool(readme) and "GeoReview Studio" in readme, True, "README export must exist for repository landing page."),
            self.check("Portfolio case study generated", bool(case_study) and "Portfolio Case Study" in case_study, True, "Case study must exist for reviewer context."),
            self.check("Repository file manifest generated", bool(repo_manifest) and "Repository File Manifest" in repo_manifest, True, "Repository manifest must explain what to include and exclude."),
            self.check("Approved review wording present", self.review_wording in readme and self.review_wording in case_study, True, "Claim boundary wording must be visible in public materials."),
            self.check("Source GIS excluded from publication ZIP", bundle.get("includes_source_gis") is False and not any("source_data/" in name for name in zip_names), True, "Public ZIP must not include local source GIS files."),
            self.check("Validation summary passed", validation.get("passed") is True, True, "Run validation before public sharing."),
            self.check("API contract summary available", api_contract.get("passed") is True and api_checked > 0, True, f"Run API contract after adding {self.app_version} endpoints."),
            self.check("Manifest points to current local release", str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).startswith("http://127.0.0.1:"), True, f"Manifest should match the promoted {self.app_version} app."),
            self.check("Repository license decision recorded", False, False, "Choose a license before public GitHub publication."),
            self.check("Fresh screenshots reviewed", False, False, "Use visual evidence artifacts or manual screenshots before sharing."),
        ]

    @staticmethod
    def check(name: str, passed: bool, required: bool, recommendation: str) -> dict:
        return {
            "check": name,
            "required": required,
            "status": "ready" if passed else ("needs_fix" if required else "reviewer_attention"),
            "recommendation": recommendation,
        }

    def public_sharing_walkthrough(self, bundle: dict, checks: list[dict], validation: dict, api_contract: dict, manifest: dict) -> list[dict]:
        return [
            {"step": 1, "title": "Open the local app", "action": f"Start {self.app_version} and open {manifest.get('local_url', 'http://127.0.0.1')}.", "evidence": "Health, manifest and release readiness endpoints respond."},
            {"step": 2, "title": "Show the claim boundary", "action": "Point to the approved wording and explain that this is an infrastructure indicator workflow.", "evidence": self.review_wording},
            {"step": 3, "title": "Show Kfar Saba analytics", "action": "Open route-aware dashboard candidates and explain generator/crossing/road context.", "evidence": f"{validation.get('generators', 0)} generators and {validation.get('crossings', 0)} crossings in validation summary."},
            {"step": 4, "title": "Show reproducibility evidence", "action": "Open release readiness and API contract summary.", "evidence": f"{api_contract.get('checked_endpoints', 0)} checked endpoints."},
            {"step": 5, "title": "Open GitHub publication bundle", "action": "Download the publication ZIP and inspect README/case-study/manifest.", "evidence": str(bundle.get("bundle_id") or "")},
            {"step": 6, "title": "Run repository QA", "action": "Create this QA review and confirm required checks are ready.", "evidence": f"{len([row for row in checks if row.get('required')])} required checks."},
            {"step": 7, "title": "Handle reviewer attention items", "action": "Add license decision and fresh screenshots before public posting.", "evidence": "Optional checks remain reviewer attention items."},
            {"step": 8, "title": "Publish deliberately", "action": "Move only curated generated docs/code to GitHub; keep source GIS out of the repository.", "evidence": "Publication ZIP excludes source GIS data."},
        ]

    def evidence_summary(self, bundle: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        return {
            "github_publication_bundle_id": bundle.get("bundle_id"),
            "github_publication_bundle_status": bundle.get("bundle_status"),
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
            "The workflow prioritizes field review using infrastructure indicators and data-quality evidence.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "The repository publication QA package excludes source GIS data.",
        ]

    def checklist_markdown(self, review: dict) -> str:
        lines = [
            "# Repository QA Checklist",
            "",
            f"- Review id: `{review.get('review_id')}`",
            f"- Status: `{review.get('qa_status')}`",
            f"- Source bundle: `{review.get('github_publication_bundle_id')}`",
            "",
            "| Check | Required | Status | Recommendation |",
            "|---|---:|---|---|",
        ]
        for item in review.get("repository_checks", []):
            lines.append(f"| {item.get('check')} | {str(item.get('required')).lower()} | {item.get('status')} | {item.get('recommendation')} |")
        lines.extend(["", "## Claim Boundaries", ""])
        for line in review.get("claim_boundaries", []):
            lines.append(f"- {line}")
        lines.append("")
        return "\n".join(lines)

    def walkthrough_markdown(self, review: dict) -> str:
        lines = [
            "# Public Sharing Walkthrough",
            "",
            "Use this sequence when presenting the project locally or preparing a GitHub repository.",
            "",
        ]
        for item in review.get("public_sharing_walkthrough", []):
            lines.append(f"## {item.get('step')}. {item.get('title')}")
            lines.append("")
            lines.append(f"Action: {item.get('action')}")
            lines.append("")
            lines.append(f"Evidence: {item.get('evidence')}")
            lines.append("")
        return "\n".join(lines)

    def review_html(self, review: dict) -> str:
        checks = "".join(
            f"<tr><td>{html.escape(str(item.get('check') or ''))}</td><td>{html.escape(str(item.get('required') or ''))}</td><td>{html.escape(str(item.get('status') or ''))}</td><td>{html.escape(str(item.get('recommendation') or ''))}</td></tr>"
            for item in review.get("repository_checks", [])
        )
        steps = "".join(
            f"<li><strong>{html.escape(str(item.get('title') or ''))}</strong><br>{html.escape(str(item.get('action') or ''))}<br><em>{html.escape(str(item.get('evidence') or ''))}</em></li>"
            for item in review.get("public_sharing_walkthrough", [])
        )
        boundaries = "".join(f"<li>{html.escape(line)}</li>" for line in review.get("claim_boundaries", []))
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Repository Publication QA</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f8f4; color: #1f2933; }}
      .summary, section {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
      table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 8px; }}
      th, td {{ border: 1px solid #d7d8d2; padding: 8px; vertical-align: top; }}
      th {{ background: #eef0ea; text-align: left; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
      li {{ margin-bottom: 10px; }}
    </style>
  </head>
  <body>
    <h1>Repository Publication QA</h1>
    <div class="summary">
      <p>Review: <code>{html.escape(str(review.get("review_id") or ""))}</code></p>
      <p>Status: <code>{html.escape(str(review.get("qa_status") or ""))}</code>; failed required checks: <code>{html.escape(str(review.get("failed_required_check_count") or 0))}</code>.</p>
      <p>Source GIS files are not included.</p>
    </div>
    <section><h2>Repository Checks</h2><table><thead><tr><th>Check</th><th>Required</th><th>Status</th><th>Recommendation</th></tr></thead><tbody>{checks}</tbody></table></section>
    <section><h2>Public Sharing Walkthrough</h2><ol>{steps}</ol></section>
    <section><h2>Claim Boundaries</h2><ul>{boundaries}</ul></section>
  </body>
</html>"""

    def write_zip(self, zip_path: Path, paths: list[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if path.exists() and self.safe_review_path(path):
                    zf.write(path, arcname=path.name)

    def zip_names(self, path: Path) -> set[str]:
        try:
            if not path.exists():
                return set()
            with zipfile.ZipFile(path) as zf:
                return set(zf.namelist())
        except (OSError, zipfile.BadZipFile):
            return set()

    def safe_read_text(self, path: Path) -> str:
        try:
            if not path.exists():
                return ""
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def review_dir(self, review_id: str) -> Path:
        return self.reviews_dir / safe_token(review_id, "missing_repository_publication_qa", 180)

    def safe_review_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.reviews_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
