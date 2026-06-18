from __future__ import annotations

import html
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPOSITORY_DRY_RUN_REVIEW_VERSION = "repository_dry_run_review_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "repository_dry_run_review", max_len: int = 150) -> str:
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
        return {"error": "repository_dry_run_review_probe_failed", "detail": repr(exc)}


class RepositoryDryRunReviewBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        repository_export_handoff: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.repository_export_handoff = repository_export_handoff
        self.expected_api_endpoints = expected_api_endpoints
        self.reviews_dir = output_root / "georeview_studio_repository_dry_run_reviews"

    def status(self) -> dict:
        handoffs = self.ready_handoffs(100)
        reviews = self.list_reviews(100)
        ready_reviews = [row for row in reviews if row.get("review_readiness") == "ready_for_repository_dry_run_review"]
        latest_handoff = handoffs[0] if handoffs else {}
        latest_review = ready_reviews[0] if ready_reviews else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "repository_dry_run_review_version": REPOSITORY_DRY_RUN_REVIEW_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "simulate_repository_archive_before_public_sharing",
            "output_dir": str(self.reviews_dir),
            "ready_handoff_count": len(handoffs),
            "latest_handoff_id": latest_handoff.get("handoff_id", ""),
            "latest_handoff_status": latest_handoff.get("handoff_status", ""),
            "review_count": len(reviews),
            "ready_review_count": len(ready_reviews),
            "latest_review_id": latest_review.get("review_id", ""),
            "latest_review_status": latest_review.get("review_status", ""),
            "latest_required_failed_count": latest_review.get("required_failed_count", 0),
            "latest_archive_file_count": latest_review.get("archive_file_count", 0),
            "latest_final_checklist_item_count": latest_review.get("final_checklist_item_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_repository_dry_run_review" if handoffs else "waiting_for_repository_export_handoff",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_review(self, body: dict | None = None) -> dict:
        body = body or {}
        handoff_id = str(body.get("handoff_id") or body.get("repository_handoff_id") or "").strip()
        if not handoff_id:
            handoffs = self.ready_handoffs(20)
            handoff_id = str(handoffs[0].get("handoff_id") or "") if handoffs else ""
        if not handoff_id:
            return self.error("repository_dry_run_review_input_missing", "A ready repository export handoff is required.")
        handoff = self.resolve_handoff(handoff_id)
        if handoff.get("error"):
            return handoff
        if handoff.get("handoff_readiness") != "ready_for_repository_export_handoff":
            return self.error("repository_dry_run_review_not_ready", "Repository export handoff must be ready_for_repository_export_handoff.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        archive_files = self.archive_file_plan(handoff)
        exclude_rules = self.exclude_rules(handoff)
        final_checklist = self.final_public_sharing_checklist(handoff, validation)
        evidence_refs = self.evidence_references(handoff, validation, api_contract)
        boundary_checks = self.boundary_checks(handoff, validation, api_contract, manifest, archive_files, exclude_rules)
        required_failed = [row for row in boundary_checks if row.get("required") and row.get("status") != "ready"]
        review_status = "ready_with_reviewer_attention_items"
        if required_failed:
            review_status = "needs_repository_dry_run_fixes"
        if not self.api_and_validation_ready(validation, api_contract):
            review_status = "pending_validation_or_api_contract"

        stamp = utc_now()
        review_id = f"repository_dry_run_review_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        review_dir = self.review_dir(review_id)
        manifest_path = review_dir / "repository_dry_run_review_manifest.json"
        review_path = review_dir / "REPOSITORY_DRY_RUN_REVIEW.md"
        archive_path = review_dir / "ARCHIVE_STRUCTURE_PREVIEW.md"
        checklist_path = review_dir / "FINAL_PUBLIC_SHARING_CHECKLIST.md"
        html_path = review_dir / "repository_dry_run_review.html"
        zip_path = review_dir / "repository_dry_run_review.zip"
        latest_path = self.reviews_dir / "latest_repository_dry_run_review.json"
        review = {
            "ok": True,
            "repository_dry_run_review_version": REPOSITORY_DRY_RUN_REVIEW_VERSION,
            "review_id": review_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_repository_reviewer"),
            "notes": str(body.get("notes") or "Repository dry-run archive review before public sharing."),
            "app_version": self.app_version,
            "handoff_id": handoff.get("handoff_id"),
            "review_readiness": "ready_for_repository_dry_run_review",
            "review_status": review_status,
            "archive_file_count": len(archive_files),
            "exclude_rule_count": len(exclude_rules),
            "final_checklist_item_count": len(final_checklist),
            "evidence_reference_count": len(evidence_refs),
            "required_failed_count": len(required_failed),
            "archive_files": archive_files,
            "exclude_rules": exclude_rules,
            "final_public_sharing_checklist": final_checklist,
            "evidence_references": evidence_refs,
            "boundary_checks": boundary_checks,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "evidence_summary": self.evidence_summary(handoff, validation, api_contract, manifest),
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "review": str(review_path),
                "archive_preview": str(archive_path),
                "final_checklist": str(checklist_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, review)
        write_json(latest_path, review)
        review_path.write_text(self.review_markdown(review), encoding="utf-8", newline="\n")
        archive_path.write_text(self.archive_markdown(review), encoding="utf-8", newline="\n")
        checklist_path.write_text(self.checklist_markdown(review), encoding="utf-8", newline="\n")
        html_path.write_text(self.review_html(review), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, review_path, archive_path, checklist_path, html_path])
        review["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, review)
        write_json(latest_path, review)
        return {"ok": True, "review": review, "source_gis_modified": False, "mutates_config": False}

    def list_reviews(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.reviews_dir.exists():
            return rows
        manifests = sorted(
            self.reviews_dir.glob("repository_dry_run_review_*/repository_dry_run_review_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("repository_dry_run_review_version") != REPOSITORY_DRY_RUN_REVIEW_VERSION:
                continue
            rows.append({
                "review_id": payload.get("review_id"),
                "created_at": payload.get("created_at"),
                "review_readiness": payload.get("review_readiness"),
                "review_status": payload.get("review_status"),
                "handoff_id": payload.get("handoff_id"),
                "archive_file_count": payload.get("archive_file_count", 0),
                "final_checklist_item_count": payload.get("final_checklist_item_count", 0),
                "required_failed_count": payload.get("required_failed_count", 0),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
                "includes_source_gis": payload.get("includes_source_gis", False),
            })
            if len(rows) >= max(1, int(limit or 20)):
                break
        return rows

    def detail(self, review_id: str) -> dict:
        path = self.review_dir(review_id) / "repository_dry_run_review_manifest.json"
        if not self.safe_review_path(path):
            return {"ok": False, "error": "repository_dry_run_review_not_found", "review_id": review_id, "source_gis_modified": False}
        payload = read_json(path)
        if payload.get("repository_dry_run_review_version") != REPOSITORY_DRY_RUN_REVIEW_VERSION:
            return {"ok": False, "error": "repository_dry_run_review_not_found", "review_id": review_id, "source_gis_modified": False}
        return payload

    def output_file(self, review_id: str, output_id: str = "zip") -> dict:
        detail = self.detail(review_id)
        if detail.get("error"):
            return detail
        path = Path(str(detail.get("files", {}).get(output_id) or ""))
        if not path.exists() or not self.safe_review_path(path):
            return {"ok": False, "error": "repository_dry_run_review_output_not_found", "review_id": review_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_handoffs(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.repository_export_handoff.list_handoffs(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("handoff_readiness") == "ready_for_repository_export_handoff"]

    def resolve_handoff(self, handoff_id: str) -> dict:
        detail = safe_call(lambda: self.repository_export_handoff.detail(handoff_id), {})
        return detail if isinstance(detail, dict) else self.error("repository_export_handoff_not_found", "Repository export handoff detail failed.")

    def api_and_validation_ready(self, validation: dict, api_contract: dict) -> bool:
        return validation.get("passed") is True and api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints

    def archive_file_plan(self, handoff: dict) -> list[dict]:
        base = [
            {"path": "README.md", "source": "repository handoff include plan", "purpose": "public landing page", "required": True},
            {"path": ".gitignore", "source": "repository handoff include plan", "purpose": "public package hygiene guardrails", "required": True},
            {"path": "docs/PORTFOLIO_CASE_STUDY.md", "source": "repository handoff include plan", "purpose": "technical case study", "required": True},
            {"path": "docs/ARCHITECTURE.md", "source": "repository handoff include plan", "purpose": "system architecture", "required": True},
            {"path": "docs/DATA_BOUNDARY.md", "source": "repository handoff include plan", "purpose": "OSM/data-quality boundary", "required": True},
            {"path": "docs/API_CONTRACT.md", "source": "api_contract_summary.json", "purpose": "endpoint verification evidence", "required": True},
            {"path": "docs/REPOSITORY_QA_CHECKLIST.md", "source": handoff.get("repository_qa_id"), "purpose": "publication QA evidence", "required": True},
            {"path": "docs/FINAL_PUBLIC_SHARING_CHECKLIST.md", "source": "dry-run review", "purpose": "manual sharing checklist", "required": True},
            {"path": "portfolio/sample_review_candidates_top20.csv", "source": "small generated sample", "purpose": "portfolio-scale sample output", "required": False},
            {"path": "screenshots/README_dashboard.png", "source": "manual capture", "purpose": "visual evidence reference", "required": False},
        ]
        return base

    def exclude_rules(self, handoff: dict) -> list[dict]:
        rules = handoff.get("exclude_files", []) if isinstance(handoff.get("exclude_files"), list) else []
        defaults = [
            {"path": "source_data/", "reason": "Keep source GIS local.", "hard_exclude": True},
            {"path": "*.osm.pbf", "reason": "Do not include large OSM extracts.", "hard_exclude": True},
            {"path": "*.shp;*.dbf;*.prj;*.cpg;*.gpkg", "reason": "Do not include source GIS files in public archive.", "hard_exclude": True},
            {"path": "__pycache__/", "reason": "Runtime cache.", "hard_exclude": True},
            {"path": "*.log;server_*.log", "reason": "Local runtime logs are machine-specific and not public source.", "hard_exclude": True},
            {"path": "ui_review/chrome_profile*/", "reason": "Temporary browser profile/cache state must stay out of public packages.", "hard_exclude": True},
            {"path": "temp/;cache/;profile/;session/", "reason": "Local execution state is not publishable repository content.", "hard_exclude": True},
        ]
        combined = rules or defaults
        seen: set[str] = set()
        result: list[dict] = []
        for item in combined + defaults:
            path = str(item.get("path") or "")
            if not path or path in seen:
                continue
            seen.add(path)
            result.append({"path": path, "reason": item.get("reason", ""), "hard_exclude": bool(item.get("hard_exclude"))})
        return result

    def final_public_sharing_checklist(self, handoff: dict, validation: dict) -> list[dict]:
        return [
            {"item": "Confirm repository license choice", "status": "reviewer_attention", "required_before_public": True, "evidence": "MIT, Apache-2.0, private repo, or no license decision is explicit."},
            {"item": "Add OSM/Geofabrik attribution text", "status": "reviewer_attention", "required_before_public": True, "evidence": "Attribution is referenced without redistributing source GIS."},
            {"item": "Verify source GIS is excluded", "status": "ready", "required_before_public": True, "evidence": f"{len(self.exclude_rules(handoff))} exclude rules in dry-run archive."},
            {"item": "Replace local absolute Windows paths in public docs", "status": "reviewer_attention", "required_before_public": True, "evidence": "Use relative paths for public README and docs."},
            {"item": "Capture dashboard screenshot", "status": "reviewer_attention", "required_before_public": True, "evidence": f"Use {validation.get('generators', 0)} generator rows as data context."},
            {"item": "Capture release readiness screenshot", "status": "reviewer_attention", "required_before_public": False, "evidence": "Show release gates and API endpoint count."},
            {"item": "Keep approved claim wording", "status": "ready", "required_before_public": True, "evidence": self.review_wording},
            {"item": "Label sample outputs clearly", "status": "ready", "required_before_public": True, "evidence": "Small sample CSVs are generated artifacts, not official datasets."},
        ]

    def evidence_references(self, handoff: dict, validation: dict, api_contract: dict) -> list[dict]:
        return [
            {"evidence": "repository_export_handoff", "id": handoff.get("handoff_id"), "status": handoff.get("handoff_status")},
            {"evidence": "validation_summary", "id": validation.get("release_readiness_snapshot_id", ""), "status": validation.get("release_readiness_level", "")},
            {"evidence": "api_contract_summary", "id": "api_contract_summary.json", "status": f"{api_contract.get('checked_endpoints', 0)} checked endpoints"},
            {"evidence": "route_aware_workspace", "id": validation.get("route_aware_workspace_id", ""), "status": f"{validation.get('route_aware_rows', 0)} rows"},
        ]

    def boundary_checks(self, handoff: dict, validation: dict, api_contract: dict, manifest: dict, archive_files: list[dict], exclude_rules: list[dict]) -> list[dict]:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        source_patterns = ("*.osm.pbf", "*.shp", "*.gpkg", "source_data/")
        hard_exclude_text = json.dumps(exclude_rules, ensure_ascii=False)
        archive_text = json.dumps(archive_files, ensure_ascii=False)
        return [
            self.check("Repository export handoff is ready", handoff.get("handoff_readiness") == "ready_for_repository_export_handoff", True, "Create repository export handoff first."),
            self.check("Repository handoff required checks passed", int(handoff.get("required_failed_count") or 0) == 0, True, "Resolve handoff required checks."),
            self.check("Validation summary passed", validation.get("passed") is True, True, "Run validation before dry-run review."),
            self.check("API contract evidence available", api_contract.get("passed") is True and api_checked >= max(1, self.expected_api_endpoints - 5), False, f"Run API contract after adding {self.app_version} endpoints."),
            self.check("Manifest points to current local release", str(manifest.get("version", "")).startswith(self.app_version) and str(manifest.get("local_url", "")).endswith("8847"), True, f"Update manifest for {self.app_version}."),
            self.check("Archive preview excludes source GIS", not any(token in archive_text for token in source_patterns), True, "Do not list source GIS in archive include plan."),
            self.check("Hard exclude rules cover source GIS", all(token in hard_exclude_text for token in ("*.osm.pbf", "*.shp", "*.gpkg", "source_data/")), True, "Keep source GIS hard-exclude rules."),
            self.check("Approved wording present", self.review_wording in json.dumps(handoff, ensure_ascii=False), True, "Keep claim boundary in handoff and dry-run artifacts."),
            self.check("Manual screenshot and license tasks remain explicit", True, False, "Resolve reviewer attention items before public sharing."),
        ]

    @staticmethod
    def check(name: str, passed: bool, required: bool, recommendation: str) -> dict:
        return {"check": name, "required": required, "status": "ready" if passed else ("needs_fix" if required else "reviewer_attention"), "recommendation": recommendation}

    def evidence_summary(self, handoff: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        return {
            "handoff_id": handoff.get("handoff_id"),
            "handoff_status": handoff.get("handoff_status"),
            "handoff_required_failed": handoff.get("required_failed_count"),
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
            "The dry-run review simulates repository archive contents; it does not publish anything.",
            "Source GIS files and large OSM extracts stay local unless a separate licensing decision allows otherwise.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
        ]

    def review_markdown(self, review: dict) -> str:
        lines = [
            "# Repository Dry-Run Review",
            "",
            f"- Review id: `{review.get('review_id')}`",
            f"- Status: `{review.get('review_status')}`",
            f"- Source handoff: `{review.get('handoff_id')}`",
            f"- Required failed checks: `{review.get('required_failed_count')}`",
            "",
            "## Claim Boundaries",
            "",
        ]
        for line in review.get("claim_boundaries", []):
            lines.append(f"- {line}")
        lines.extend(["", "## Evidence References", ""])
        for item in review.get("evidence_references", []):
            lines.append(f"- {item.get('evidence')}: `{item.get('id')}` - {item.get('status')}")
        lines.append("")
        return "\n".join(lines)

    def archive_markdown(self, review: dict) -> str:
        lines = ["# Archive Structure Preview", "", "## Include", "", "| Path | Required | Purpose |", "|---|---:|---|"]
        for item in review.get("archive_files", []):
            lines.append(f"| `{item.get('path')}` | {str(item.get('required')).lower()} | {item.get('purpose')} |")
        lines.extend(["", "## Exclude", "", "| Path | Hard exclude | Reason |", "|---|---:|---|"])
        for item in review.get("exclude_rules", []):
            lines.append(f"| `{item.get('path')}` | {str(item.get('hard_exclude')).lower()} | {item.get('reason')} |")
        lines.append("")
        return "\n".join(lines)

    def checklist_markdown(self, review: dict) -> str:
        lines = ["# Final Public Sharing Checklist", "", "| Item | Required before public | Status | Evidence |", "|---|---:|---|---|"]
        for item in review.get("final_public_sharing_checklist", []):
            lines.append(f"| {item.get('item')} | {str(item.get('required_before_public')).lower()} | {item.get('status')} | {item.get('evidence')} |")
        lines.extend(["", "## Boundary Checks", "", "| Check | Required | Status | Recommendation |", "|---|---:|---|---|"])
        for item in review.get("boundary_checks", []):
            lines.append(f"| {item.get('check')} | {str(item.get('required')).lower()} | {item.get('status')} | {item.get('recommendation')} |")
        lines.append("")
        return "\n".join(lines)

    def review_html(self, review: dict) -> str:
        archive_rows = "".join(f"<tr><td>{html.escape(str(item.get('path') or ''))}</td><td>{html.escape(str(item.get('required') or ''))}</td><td>{html.escape(str(item.get('purpose') or ''))}</td></tr>" for item in review.get("archive_files", []))
        exclude_rows = "".join(f"<tr><td>{html.escape(str(item.get('path') or ''))}</td><td>{html.escape(str(item.get('hard_exclude') or ''))}</td><td>{html.escape(str(item.get('reason') or ''))}</td></tr>" for item in review.get("exclude_rules", []))
        checklist = "".join(f"<li><strong>{html.escape(str(item.get('item') or ''))}</strong>: {html.escape(str(item.get('status') or ''))} - {html.escape(str(item.get('evidence') or ''))}</li>" for item in review.get("final_public_sharing_checklist", []))
        checks = "".join(f"<li><strong>{html.escape(str(item.get('check') or ''))}</strong>: {html.escape(str(item.get('status') or ''))}</li>" for item in review.get("boundary_checks", []))
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Repository Dry-Run Review</title>
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
    <h1>Repository Dry-Run Review</h1>
    <div class="summary">
      <p>Review: <code>{html.escape(str(review.get("review_id") or ""))}</code></p>
      <p>Status: <code>{html.escape(str(review.get("review_status") or ""))}</code>; failed required checks: <code>{html.escape(str(review.get("required_failed_count") or 0))}</code>.</p>
      <p>This is a local dry-run only. Source GIS files are excluded.</p>
    </div>
    <section><h2>Archive Include Preview</h2><table><thead><tr><th>Path</th><th>Required</th><th>Purpose</th></tr></thead><tbody>{archive_rows}</tbody></table></section>
    <section><h2>Exclude Rules</h2><table><thead><tr><th>Path</th><th>Hard exclude</th><th>Reason</th></tr></thead><tbody>{exclude_rows}</tbody></table></section>
    <section><h2>Final Checklist</h2><ul>{checklist}</ul></section>
    <section><h2>Boundary Checks</h2><ul>{checks}</ul></section>
  </body>
</html>"""

    def write_zip(self, zip_path: Path, paths: list[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if path.exists() and self.safe_review_path(path):
                    zf.write(path, arcname=path.name)

    def review_dir(self, review_id: str) -> Path:
        return self.reviews_dir / safe_token(review_id, "missing_repository_dry_run_review", 180)

    def safe_review_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.reviews_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}

