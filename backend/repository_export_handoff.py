from __future__ import annotations

import html
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPOSITORY_EXPORT_HANDOFF_VERSION = "repository_export_handoff_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "repository_export_handoff", max_len: int = 150) -> str:
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
        return {"error": "repository_export_handoff_probe_failed", "detail": repr(exc)}


class RepositoryExportHandoffBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        repository_publication_qa: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.repository_publication_qa = repository_publication_qa
        self.expected_api_endpoints = expected_api_endpoints
        self.handoffs_dir = output_root / "georeview_studio_repository_export_handoffs"

    def status(self) -> dict:
        qa_reviews = self.ready_qa_reviews(100)
        handoffs = self.list_handoffs(100)
        ready_handoffs = [row for row in handoffs if row.get("handoff_readiness") == "ready_for_repository_export_handoff"]
        latest_qa = qa_reviews[0] if qa_reviews else {}
        latest_handoff = ready_handoffs[0] if ready_handoffs else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "repository_export_handoff_version": REPOSITORY_EXPORT_HANDOFF_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "prepare_repository_export_handoff",
            "output_dir": str(self.handoffs_dir),
            "ready_repository_qa_count": len(qa_reviews),
            "latest_repository_qa_id": latest_qa.get("review_id", ""),
            "latest_repository_qa_status": latest_qa.get("qa_status", ""),
            "handoff_count": len(handoffs),
            "ready_handoff_count": len(ready_handoffs),
            "latest_handoff_id": latest_handoff.get("handoff_id", ""),
            "latest_handoff_status": latest_handoff.get("handoff_status", ""),
            "latest_include_file_count": latest_handoff.get("include_file_count", 0),
            "latest_exclude_file_count": latest_handoff.get("exclude_file_count", 0),
            "latest_screenshot_reference_count": latest_handoff.get("screenshot_reference_count", 0),
            "latest_license_decision_item_count": latest_handoff.get("license_decision_item_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_repository_export_handoff" if qa_reviews else "waiting_for_repository_publication_qa",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_handoff(self, body: dict | None = None) -> dict:
        body = body or {}
        qa_id = str(body.get("repository_qa_id") or body.get("review_id") or "").strip()
        if not qa_id:
            reviews = self.ready_qa_reviews(20)
            qa_id = str(reviews[0].get("review_id") or "") if reviews else ""
        if not qa_id:
            return self.error("repository_export_handoff_input_missing", "A ready repository publication QA review is required.")
        qa_review = self.resolve_qa_review(qa_id)
        if qa_review.get("error"):
            return qa_review
        if qa_review.get("qa_readiness") != "ready_for_repository_publication_qa":
            return self.error("repository_export_handoff_not_ready", "Repository QA review must be ready_for_repository_publication_qa.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        include_files = self.include_files(qa_review)
        exclude_files = self.exclude_files()
        screenshot_refs = self.screenshot_references(validation)
        license_items = self.license_decision_items()
        boundary_checks = self.boundary_checks(qa_review, validation, api_contract, manifest)
        required_failed = [row for row in boundary_checks if row.get("required") and row.get("status") != "ready"]
        handoff_status = "ready_for_repository_handoff"
        if required_failed:
            handoff_status = "needs_repository_handoff_fixes"
        elif qa_review.get("qa_status") == "ready_with_reviewer_attention_items":
            handoff_status = "ready_with_reviewer_attention_items"
        if not self.api_and_validation_ready(validation, api_contract):
            handoff_status = "pending_validation_or_api_contract"

        stamp = utc_now()
        handoff_id = f"repository_export_handoff_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        handoff_dir = self.handoff_dir(handoff_id)
        manifest_path = handoff_dir / "repository_export_handoff_manifest.json"
        handoff_path = handoff_dir / "REPOSITORY_EXPORT_HANDOFF.md"
        file_plan_path = handoff_dir / "GITHUB_REPOSITORY_FILE_PLAN.md"
        checklist_path = handoff_dir / "SCREENSHOT_AND_LICENSE_CHECKLIST.md"
        html_path = handoff_dir / "repository_export_handoff.html"
        zip_path = handoff_dir / "repository_export_handoff.zip"
        latest_path = self.handoffs_dir / "latest_repository_export_handoff.json"
        handoff = {
            "ok": True,
            "repository_export_handoff_version": REPOSITORY_EXPORT_HANDOFF_VERSION,
            "handoff_id": handoff_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_repository_reviewer"),
            "notes": str(body.get("notes") or "Repository export handoff for public portfolio preparation."),
            "app_version": self.app_version,
            "repository_qa_id": qa_review.get("review_id"),
            "handoff_readiness": "ready_for_repository_export_handoff",
            "handoff_status": handoff_status,
            "include_file_count": len(include_files),
            "exclude_file_count": len(exclude_files),
            "screenshot_reference_count": len(screenshot_refs),
            "license_decision_item_count": len(license_items),
            "required_failed_count": len(required_failed),
            "include_files": include_files,
            "exclude_files": exclude_files,
            "screenshot_references": screenshot_refs,
            "license_decision_checklist": license_items,
            "boundary_checks": boundary_checks,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "evidence_summary": self.evidence_summary(qa_review, validation, api_contract, manifest),
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "handoff": str(handoff_path),
                "file_plan": str(file_plan_path),
                "checklist": str(checklist_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, handoff)
        write_json(latest_path, handoff)
        handoff_path.write_text(self.handoff_markdown(handoff), encoding="utf-8", newline="\n")
        file_plan_path.write_text(self.file_plan_markdown(handoff), encoding="utf-8", newline="\n")
        checklist_path.write_text(self.checklist_markdown(handoff), encoding="utf-8", newline="\n")
        html_path.write_text(self.handoff_html(handoff), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, handoff_path, file_plan_path, checklist_path, html_path])
        handoff["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, handoff)
        write_json(latest_path, handoff)
        return {"ok": True, "handoff": handoff, "source_gis_modified": False, "mutates_config": False}

    def list_handoffs(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.handoffs_dir.exists():
            return rows
        manifests = sorted(
            self.handoffs_dir.glob("repository_export_handoff_*/repository_export_handoff_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("repository_export_handoff_version") != REPOSITORY_EXPORT_HANDOFF_VERSION:
                continue
            rows.append({
                "handoff_id": payload.get("handoff_id"),
                "created_at": payload.get("created_at"),
                "handoff_readiness": payload.get("handoff_readiness"),
                "handoff_status": payload.get("handoff_status"),
                "repository_qa_id": payload.get("repository_qa_id"),
                "include_file_count": payload.get("include_file_count", 0),
                "exclude_file_count": payload.get("exclude_file_count", 0),
                "screenshot_reference_count": payload.get("screenshot_reference_count", 0),
                "license_decision_item_count": payload.get("license_decision_item_count", 0),
                "required_failed_count": payload.get("required_failed_count", 0),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
                "download_url": f"/api/repository-export-handoff/handoffs/{payload.get('handoff_id')}/download",
                "includes_source_gis": False,
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, handoff_id: str) -> dict:
        path = self.handoff_dir(handoff_id) / "repository_export_handoff_manifest.json"
        if not path.exists() or not self.safe_handoff_path(path):
            return {"ok": False, "error": "repository_export_handoff_not_found", "handoff_id": handoff_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "repository_export_handoff_not_found", "handoff_id": handoff_id, "source_gis_modified": False}
        return payload

    def output_file(self, handoff_id: str, output_id: str = "zip") -> dict:
        detail = self.detail(handoff_id)
        if detail.get("error"):
            return detail
        if output_id not in {"zip", "html", "handoff", "file_plan", "checklist"}:
            return {"ok": False, "error": "repository_export_handoff_output_not_found", "handoff_id": handoff_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get(output_id) or ""))
        if not path.exists() or not self.safe_handoff_path(path):
            return {"ok": False, "error": "repository_export_handoff_output_not_found", "handoff_id": handoff_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_qa_reviews(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.repository_publication_qa.list_reviews(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("qa_readiness") == "ready_for_repository_publication_qa"]

    def resolve_qa_review(self, qa_id: str) -> dict:
        detail = safe_call(lambda: self.repository_publication_qa.detail(qa_id), {})
        return detail if isinstance(detail, dict) else self.error("repository_publication_qa_not_found", "Repository QA detail failed.")

    def api_and_validation_ready(self, validation: dict, api_contract: dict) -> bool:
        return validation.get("passed") is True and api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints

    def include_files(self, qa_review: dict) -> list[dict]:
        return [
            {"path": "README.md", "source": "GitHub publication bundle README_public.md", "reason": "Public project landing page.", "required": True},
            {"path": ".gitignore", "source": "repository hygiene rules", "reason": "Prevent logs, caches, secrets and source GIS from entering the public repo.", "required": True},
            {"path": "docs/PORTFOLIO_CASE_STUDY.md", "source": "GitHub publication bundle case study", "reason": "Long-form technical story.", "required": True},
            {"path": "docs/ARCHITECTURE.md", "source": "Generated architecture docs", "reason": "Explain local-first GIS workbench design.", "required": True},
            {"path": "docs/DATA_BOUNDARY.md", "source": "Claim boundaries and source data policy", "reason": "Document OSM uncertainty and source GIS exclusion.", "required": True},
            {"path": "docs/API_CONTRACT.md", "source": "api_contract_summary.json", "reason": "Show endpoint verification evidence.", "required": True},
            {"path": "portfolio/sample_review_candidates_top20.csv", "source": "Generated small sample output", "reason": "Portfolio-scale data sample.", "required": False},
            {"path": "screenshots/", "source": "Visual evidence captures", "reason": "Reviewer screenshots after manual selection.", "required": False},
            {"path": "docs/REPOSITORY_QA_CHECKLIST.md", "source": qa_review.get("review_id"), "reason": "Repository QA evidence.", "required": True},
        ]

    def exclude_files(self) -> list[dict]:
        return [
            {"path": "source_data/", "reason": "Do not publish local source GIS or large OSM extracts.", "hard_exclude": True},
            {"path": "*.osm.pbf", "reason": "Large source GIS extract; keep local only.", "hard_exclude": True},
            {"path": "*.shp;*.dbf;*.prj;*.cpg;*.gpkg", "reason": "Source GIS files require explicit licensing/release review.", "hard_exclude": True},
            {"path": "analysis_output/georeview_studio_app/v*/", "reason": "Version snapshots are local build artifacts; publish curated code/docs only.", "hard_exclude": False},
            {"path": "__pycache__/", "reason": "Runtime cache.", "hard_exclude": True},
            {"path": "*.log;server_*.log", "reason": "Local runtime logs are machine-specific and not public source.", "hard_exclude": True},
            {"path": "ui_review/chrome_profile*/", "reason": "Temporary browser profile/cache state must stay out of public packages.", "hard_exclude": True},
            {"path": "temp/;cache/;profile/;session/", "reason": "Local execution state is not publishable repository content.", "hard_exclude": True},
        ]

    def screenshot_references(self, validation: dict) -> list[dict]:
        return [
            {"target": "Dashboard overview", "required_before_public": True, "status": "reviewer_attention", "evidence": f"Capture current {self.app_version} landing dashboard."},
            {"target": "Kfar Saba candidate table", "required_before_public": True, "status": "reviewer_attention", "evidence": f"Use {validation.get('generators', 0)} generator evidence rows."},
            {"target": "Route-aware map", "required_before_public": True, "status": "reviewer_attention", "evidence": f"Route-aware rows: {validation.get('route_aware_rows', 0)}."},
            {"target": "Repository Publication QA panel", "required_before_public": True, "status": "reviewer_attention", "evidence": "Show failed required checks at 0."},
            {"target": "Release Readiness panel", "required_before_public": False, "status": "optional", "evidence": "Use when explaining validation depth."},
        ]

    def license_decision_items(self) -> list[dict]:
        return [
            {"item": "Choose repository code license", "status": "reviewer_attention", "recommendation": "Pick MIT, Apache-2.0 or no license before public GitHub sharing."},
            {"item": "Document OSM/Geofabrik attribution", "status": "reviewer_attention", "recommendation": "Add attribution text without redistributing source GIS files."},
            {"item": "State generated sample data boundary", "status": "ready", "recommendation": "Keep sample outputs small and label them as generated local artifacts."},
            {"item": "Keep private paths out of public README", "status": "reviewer_attention", "recommendation": "Replace local Windows paths with relative paths in the public repo."},
        ]

    def boundary_checks(self, qa_review: dict, validation: dict, api_contract: dict, manifest: dict) -> list[dict]:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        return [
            self.check("Repository QA is ready", qa_review.get("qa_readiness") == "ready_for_repository_publication_qa", True, "Create repository QA first."),
            self.check("Repository QA required checks passed", int(qa_review.get("failed_required_check_count") or 0) == 0, True, "Fix repository QA required checks."),
            self.check("Validation summary passed", validation.get("passed") is True, True, "Run validation before handoff."),
            self.check("API contract evidence available", api_contract.get("passed") is True and api_checked >= max(1, self.expected_api_endpoints - 5), False, f"Run API contract after {self.app_version} endpoints."),
            self.check("Manifest points to current local release", str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).startswith("http://127.0.0.1:"), True, "Update project manifest."),
            self.check("Approved wording present", self.review_wording in json.dumps(qa_review, ensure_ascii=False), True, "Keep claim boundary in QA artifacts."),
            self.check("Source GIS excluded", qa_review.get("includes_source_gis") is False, True, "Do not include source GIS in repository handoff."),
            self.check("License decision still explicit", True, False, "Resolve license before public GitHub release."),
        ]

    @staticmethod
    def check(name: str, passed: bool, required: bool, recommendation: str) -> dict:
        return {"check": name, "required": required, "status": "ready" if passed else ("needs_fix" if required else "reviewer_attention"), "recommendation": recommendation}

    def evidence_summary(self, qa_review: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        return {
            "repository_qa_id": qa_review.get("review_id"),
            "repository_qa_status": qa_review.get("qa_status"),
            "repository_qa_failed_required": qa_review.get("failed_required_check_count"),
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
            "This repository handoff is for infrastructure indicator review and portfolio demonstration, not crash prediction.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "Do not publish source GIS files or large local extracts in the repository.",
        ]

    def handoff_markdown(self, handoff: dict) -> str:
        lines = [
            "# Repository Export Handoff",
            "",
            f"- Handoff id: `{handoff.get('handoff_id')}`",
            f"- Status: `{handoff.get('handoff_status')}`",
            f"- Source QA: `{handoff.get('repository_qa_id')}`",
            f"- Required failed checks: `{handoff.get('required_failed_count')}`",
            "",
            "## Claim Boundaries",
            "",
        ]
        for line in handoff.get("claim_boundaries", []):
            lines.append(f"- {line}")
        lines.extend(["", "## Next Manual Decisions", ""])
        for item in handoff.get("license_decision_checklist", []):
            lines.append(f"- {item.get('item')}: `{item.get('status')}` - {item.get('recommendation')}")
        lines.append("")
        return "\n".join(lines)

    def file_plan_markdown(self, handoff: dict) -> str:
        lines = ["# GitHub Repository File Plan", "", "## Include", "", "| Path | Required | Reason |", "|---|---:|---|"]
        for item in handoff.get("include_files", []):
            lines.append(f"| `{item.get('path')}` | {str(item.get('required')).lower()} | {item.get('reason')} |")
        lines.extend(["", "## Exclude", "", "| Path | Hard exclude | Reason |", "|---|---:|---|"])
        for item in handoff.get("exclude_files", []):
            lines.append(f"| `{item.get('path')}` | {str(item.get('hard_exclude')).lower()} | {item.get('reason')} |")
        lines.append("")
        return "\n".join(lines)

    def checklist_markdown(self, handoff: dict) -> str:
        lines = ["# Screenshot and License Checklist", "", "## Screenshot References", ""]
        for item in handoff.get("screenshot_references", []):
            lines.append(f"- {item.get('target')}: `{item.get('status')}` - {item.get('evidence')}")
        lines.extend(["", "## License Decisions", ""])
        for item in handoff.get("license_decision_checklist", []):
            lines.append(f"- {item.get('item')}: `{item.get('status')}` - {item.get('recommendation')}")
        lines.extend(["", "## Boundary Checks", "", "| Check | Required | Status | Recommendation |", "|---|---:|---|---|"])
        for item in handoff.get("boundary_checks", []):
            lines.append(f"| {item.get('check')} | {str(item.get('required')).lower()} | {item.get('status')} | {item.get('recommendation')} |")
        lines.append("")
        return "\n".join(lines)

    def handoff_html(self, handoff: dict) -> str:
        include_rows = "".join(f"<tr><td>{html.escape(str(item.get('path') or ''))}</td><td>{html.escape(str(item.get('required') or ''))}</td><td>{html.escape(str(item.get('reason') or ''))}</td></tr>" for item in handoff.get("include_files", []))
        exclude_rows = "".join(f"<tr><td>{html.escape(str(item.get('path') or ''))}</td><td>{html.escape(str(item.get('hard_exclude') or ''))}</td><td>{html.escape(str(item.get('reason') or ''))}</td></tr>" for item in handoff.get("exclude_files", []))
        screenshots = "".join(f"<li><strong>{html.escape(str(item.get('target') or ''))}</strong>: {html.escape(str(item.get('status') or ''))} - {html.escape(str(item.get('evidence') or ''))}</li>" for item in handoff.get("screenshot_references", []))
        licenses = "".join(f"<li><strong>{html.escape(str(item.get('item') or ''))}</strong>: {html.escape(str(item.get('status') or ''))} - {html.escape(str(item.get('recommendation') or ''))}</li>" for item in handoff.get("license_decision_checklist", []))
        boundaries = "".join(f"<li>{html.escape(line)}</li>" for line in handoff.get("claim_boundaries", []))
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Repository Export Handoff</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f8f4; color: #1f2933; }}
      .summary, section {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
      table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 8px; }}
      th, td {{ border: 1px solid #d7d8d2; padding: 8px; vertical-align: top; }}
      th {{ background: #eef0ea; text-align: left; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
      li {{ margin-bottom: 8px; }}
    </style>
  </head>
  <body>
    <h1>Repository Export Handoff</h1>
    <div class="summary">
      <p>Handoff: <code>{html.escape(str(handoff.get("handoff_id") or ""))}</code></p>
      <p>Status: <code>{html.escape(str(handoff.get("handoff_status") or ""))}</code>; failed required checks: <code>{html.escape(str(handoff.get("required_failed_count") or 0))}</code>.</p>
      <p>Source GIS files are excluded.</p>
    </div>
    <section><h2>Include Files</h2><table><thead><tr><th>Path</th><th>Required</th><th>Reason</th></tr></thead><tbody>{include_rows}</tbody></table></section>
    <section><h2>Exclude Files</h2><table><thead><tr><th>Path</th><th>Hard exclude</th><th>Reason</th></tr></thead><tbody>{exclude_rows}</tbody></table></section>
    <section><h2>Screenshot References</h2><ul>{screenshots}</ul></section>
    <section><h2>License Decisions</h2><ul>{licenses}</ul></section>
    <section><h2>Claim Boundaries</h2><ul>{boundaries}</ul></section>
  </body>
</html>"""

    def write_zip(self, zip_path: Path, paths: list[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if path.exists() and self.safe_handoff_path(path):
                    zf.write(path, arcname=path.name)

    def handoff_dir(self, handoff_id: str) -> Path:
        return self.handoffs_dir / safe_token(handoff_id, "missing_repository_export_handoff", 180)

    def safe_handoff_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.handoffs_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
