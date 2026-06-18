from __future__ import annotations

import html
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


GITHUB_PUBLICATION_BUNDLE_VERSION = "github_publication_bundle_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "github_publication_bundle", max_len: int = 150) -> str:
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
        return {"error": "github_publication_bundle_probe_failed", "detail": repr(exc)}


class GitHubPublicationBundleBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        demo_review_playbook: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.demo_review_playbook = demo_review_playbook
        self.expected_api_endpoints = expected_api_endpoints
        self.bundles_dir = output_root / "georeview_studio_github_publication_bundles"

    def status(self) -> dict:
        playbooks = self.ready_demo_playbooks(100)
        bundles = self.list_bundles(100)
        ready_bundles = [row for row in bundles if row.get("bundle_readiness") == "ready_for_github_publication_bundle"]
        latest_playbook = playbooks[0] if playbooks else {}
        latest_bundle = ready_bundles[0] if ready_bundles else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "github_publication_bundle_version": GITHUB_PUBLICATION_BUNDLE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "package_github_ready_publication_material",
            "output_dir": str(self.bundles_dir),
            "ready_demo_review_playbook_count": len(playbooks),
            "latest_demo_review_playbook_id": latest_playbook.get("playbook_id", ""),
            "latest_demo_review_playbook_status": latest_playbook.get("playbook_status", ""),
            "bundle_count": len(bundles),
            "ready_bundle_count": len(ready_bundles),
            "latest_bundle_id": latest_bundle.get("bundle_id", ""),
            "latest_bundle_status": latest_bundle.get("bundle_status", ""),
            "latest_readme_section_count": latest_bundle.get("readme_section_count", 0),
            "latest_repo_file_count": latest_bundle.get("repo_file_count", 0),
            "latest_publication_checklist_item_count": latest_bundle.get("publication_checklist_item_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_github_publication_bundle" if playbooks else "waiting_for_demo_review_playbook",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_bundle(self, body: dict | None = None) -> dict:
        body = body or {}
        playbook_id = str(body.get("playbook_id") or "").strip()
        if not playbook_id:
            playbooks = self.ready_demo_playbooks(20)
            playbook_id = str(playbooks[0].get("playbook_id") or "") if playbooks else ""
        if not playbook_id:
            return self.error("github_publication_bundle_input_missing", "A ready demo review playbook is required.")
        playbook = self.resolve_playbook(playbook_id)
        if playbook.get("error"):
            return playbook
        if playbook.get("playbook_readiness") != "ready_for_demo_review_playbook":
            return self.error("github_publication_bundle_not_ready", "Demo review playbook must be ready_for_demo_review_playbook.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        evidence = self.evidence_summary(playbook, validation, api_contract, manifest)
        readme_sections = self.readme_sections(playbook, evidence)
        repo_files = self.repo_files(playbook, evidence)
        checklist = self.publication_checklist(playbook, evidence)
        story_highlights = self.story_highlights(playbook, evidence)
        stamp = utc_now()
        bundle_id = f"github_publication_bundle_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        bundle_dir = self.bundle_dir(bundle_id)
        manifest_path = bundle_dir / "github_publication_bundle_manifest.json"
        readme_path = bundle_dir / "README_public.md"
        case_study_path = bundle_dir / "PORTFOLIO_CASE_STUDY.md"
        repo_manifest_path = bundle_dir / "REPOSITORY_FILE_MANIFEST.md"
        html_path = bundle_dir / "github_publication_bundle.html"
        zip_path = bundle_dir / "github_publication_bundle.zip"
        latest_path = self.bundles_dir / "latest_github_publication_bundle.json"
        bundle = {
            "ok": True,
            "github_publication_bundle_version": GITHUB_PUBLICATION_BUNDLE_VERSION,
            "bundle_id": bundle_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_portfolio_reviewer"),
            "notes": str(body.get("notes") or "GitHub-ready README export and portfolio publication bundle for GeoReview Studio."),
            "app_version": self.app_version,
            "demo_review_playbook_id": playbook.get("playbook_id"),
            "bundle_readiness": "ready_for_github_publication_bundle",
            "bundle_status": evidence.get("bundle_status"),
            "headline": "GeoReview Studio: GIS infrastructure indicator workbench",
            "readme_section_count": len(readme_sections),
            "repo_file_count": len(repo_files),
            "publication_checklist_item_count": len(checklist),
            "story_highlight_count": len(story_highlights),
            "readme_sections": readme_sections,
            "repo_files": repo_files,
            "publication_checklist": checklist,
            "story_highlights": story_highlights,
            "claim_boundaries": self.claim_boundaries(),
            "evidence_summary": evidence,
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "readme_export": str(readme_path),
                "case_study": str(case_study_path),
                "repo_manifest": str(repo_manifest_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, bundle)
        write_json(latest_path, bundle)
        readme_path.write_text(self.readme_markdown(bundle), encoding="utf-8", newline="\n")
        case_study_path.write_text(self.case_study_markdown(bundle), encoding="utf-8", newline="\n")
        repo_manifest_path.write_text(self.repo_manifest_markdown(bundle), encoding="utf-8", newline="\n")
        html_path.write_text(self.bundle_html(bundle), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, readme_path, case_study_path, repo_manifest_path, html_path])
        bundle["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, bundle)
        write_json(latest_path, bundle)
        return {"ok": True, "bundle": bundle, "source_gis_modified": False, "mutates_config": False}

    def list_bundles(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.bundles_dir.exists():
            return rows
        manifests = sorted(
            self.bundles_dir.glob("github_publication_bundle_*/github_publication_bundle_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("github_publication_bundle_version") != GITHUB_PUBLICATION_BUNDLE_VERSION:
                continue
            rows.append({
                "bundle_id": payload.get("bundle_id"),
                "created_at": payload.get("created_at"),
                "bundle_readiness": payload.get("bundle_readiness"),
                "bundle_status": payload.get("bundle_status"),
                "demo_review_playbook_id": payload.get("demo_review_playbook_id"),
                "readme_section_count": payload.get("readme_section_count"),
                "repo_file_count": payload.get("repo_file_count"),
                "publication_checklist_item_count": payload.get("publication_checklist_item_count"),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
                "download_url": f"/api/github-publication-bundle/bundles/{payload.get('bundle_id')}/download",
                "includes_source_gis": False,
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, bundle_id: str) -> dict:
        path = self.bundle_dir(bundle_id) / "github_publication_bundle_manifest.json"
        if not path.exists() or not self.safe_bundle_path(path):
            return {"ok": False, "error": "github_publication_bundle_not_found", "bundle_id": bundle_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "github_publication_bundle_not_found", "bundle_id": bundle_id, "source_gis_modified": False}
        return payload

    def output_file(self, bundle_id: str, output_id: str = "zip") -> dict:
        detail = self.detail(bundle_id)
        if detail.get("error"):
            return detail
        if output_id not in {"zip", "html", "readme"}:
            return {"ok": False, "error": "github_publication_bundle_output_not_found", "bundle_id": bundle_id, "output_id": output_id}
        key = "zip" if output_id == "zip" else ("html" if output_id == "html" else "readme_export")
        path = Path(str(detail.get("files", {}).get(key) or ""))
        if not path.exists() or not self.safe_bundle_path(path):
            return {"ok": False, "error": "github_publication_bundle_output_not_found", "bundle_id": bundle_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_demo_playbooks(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.demo_review_playbook.list_playbooks(limit), [])
        if not isinstance(rows, list):
            return []
        return [row for row in rows if row.get("playbook_readiness") == "ready_for_demo_review_playbook"]

    def resolve_playbook(self, playbook_id: str) -> dict:
        detail = safe_call(lambda: self.demo_review_playbook.detail(playbook_id), {})
        return detail if isinstance(detail, dict) else self.error("demo_review_playbook_not_found", "Demo review playbook detail failed.")

    def evidence_summary(self, playbook: dict, validation: dict, api_contract: dict, manifest: dict) -> dict:
        api_checked = int(api_contract.get("checked_endpoints") or 0)
        validation_passed = validation.get("passed") is True
        api_passed = api_contract.get("passed") is True and api_checked >= self.expected_api_endpoints
        playbook_status = str(playbook.get("playbook_status") or "")
        bundle_status = "ready_for_public_repository_review"
        if playbook_status == "ready_with_reviewer_attention_items":
            bundle_status = "ready_with_reviewer_attention_items"
        if not validation_passed or not api_passed:
            bundle_status = "pending_validation_or_api_contract"
        return {
            "bundle_status": bundle_status,
            "playbook_status": playbook_status,
            "demo_review_playbook_id": playbook.get("playbook_id"),
            "validation_passed": validation_passed,
            "validation_release_readiness": validation.get("release_readiness_level", ""),
            "validation_failed_gates": validation.get("release_readiness_failed_gates", ""),
            "api_contract_passed": api_passed,
            "api_contract_checked_endpoints": api_checked,
            "expected_api_endpoints": self.expected_api_endpoints,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "local_url": manifest.get("local_url") if isinstance(manifest, dict) else "",
            "current_release_focus": manifest.get("current_release_focus") if isinstance(manifest, dict) else "",
            "generators": validation.get("generators", 0),
            "crossings": validation.get("crossings", 0),
            "route_aware_rows": validation.get("route_aware_rows", 0),
            "route_aware_median_crossing_m": validation.get("route_aware_median_crossing_m", ""),
            "review_wording": self.review_wording,
        }

    def readme_sections(self, playbook: dict, evidence: dict) -> list[dict]:
        return [
            {"title": "What this is", "body": "GeoReview Studio is a local-first GIS review workbench for infrastructure risk indicators and data-quality evidence."},
            {"title": "Implemented proof", "body": "Safe Access Israel / Kfar Saba is the first implemented profile, using OSM/Geofabrik evidence for pedestrian-access review prioritization."},
            {"title": "Why it matters", "body": "The project shows GIS data engineering, road-safety domain judgment, transparent scoring, reusable profile contracts and portfolio-grade validation."},
            {"title": "Current evidence", "body": f"Validation references {evidence.get('generators')} generators, {evidence.get('crossings')} crossings and {evidence.get('route_aware_rows')} route-aware rows."},
            {"title": "Core analytics", "body": "Nearest crossing distance, crossing buffers, major-road proximity, traffic signal context, route-aware proxy metrics and explicit missing-tag flags."},
            {"title": "Architecture", "body": "Source onboarding, profile contracts, controlled execution, evidence packaging, dashboard API, UI panels, release readiness and publication artifacts."},
            {"title": "Run locally", "body": f"Python 3 standard library only — no external dependencies. From the repository root run `python -B backend/app.py`, then open {evidence.get('local_url') or 'http://127.0.0.1:8847'} in a browser."},
            {"title": "Screenshots", "body": "![GeoReview Studio dashboard](screenshots/dashboard_desktop.png)"},
            {"title": "Validation", "body": f"Release readiness is {evidence.get('validation_release_readiness')}; API evidence covers {evidence.get('api_contract_checked_endpoints')} checked endpoints."},
            {"title": "Claim boundary", "body": self.review_wording},
            {"title": "Next engineering path", "body": "Move publication materials into a real repository, add repository QA, then decide whether to add PostGIS-backed larger-region execution."},
        ]

    def repo_files(self, playbook: dict, evidence: dict) -> list[dict]:
        return [
            {"path": "README.md", "purpose": "Public project overview, value proposition, demo path and claim boundaries.", "include_now": True},
            {"path": "LICENSE", "purpose": "MIT license for the project source (source GIS data is licensed separately under ODbL).", "include_now": True},
            {"path": "portfolio/case_study.md", "purpose": "Long-form technical story for reviewers.", "include_now": True},
            {"path": "docs/demo_review_playbook.md", "purpose": "Demo agenda and likely reviewer questions.", "include_now": True},
            {"path": "docs/osm_tag_quality.md", "purpose": "Source GIS read-only policy and OSM evidence/data-quality limitations.", "include_now": True},
            {"path": "docs/api.md", "purpose": "Endpoint coverage and validation summary.", "include_now": True},
            {"path": "docs/architecture.md", "purpose": "Reusable GIS workbench architecture and roadmap.", "include_now": True},
            {"path": "portfolio/sample_review_candidates_top20.csv", "purpose": "Small generated sample output for inspection.", "include_now": True},
            {"path": "screenshots/", "purpose": "Dashboard screenshots (desktop + mobile) referenced by the README.", "include_now": True},
            {"path": "source_data/", "purpose": "Do not include source GIS data in the public repository.", "include_now": False},
        ]

    def publication_checklist(self, playbook: dict, evidence: dict) -> list[dict]:
        return [
            {"item": "Export public README", "status": "ready", "required": True},
            {"item": "Export portfolio case study", "status": "ready", "required": True},
            {"item": "Include demo review playbook", "status": "ready", "required": True},
            {"item": "Include validation and API evidence summary", "status": "ready" if evidence.get("validation_passed") and evidence.get("api_contract_passed") else "needs_update", "required": True},
            {"item": "Keep source GIS data out of ZIP", "status": "ready", "required": True},
            {"item": "Document OSM tag uncertainty", "status": "ready", "required": True},
            {"item": "Use approved review wording", "status": "ready", "required": True},
            {"item": "Add screenshots before public sharing", "status": "ready", "required": False},
            {"item": "Add repository license decision", "status": "ready", "required": False},
            {"item": "Review all generated links after moving into GitHub", "status": "reviewer_attention", "required": False},
        ]

    def story_highlights(self, playbook: dict, evidence: dict) -> list[str]:
        return [
            "A concrete Kfar Saba pilot proves the domain workflow.",
            "The architecture is broader than one city and can support additional OSM/GIS sources.",
            "Risk score and data-quality flags are separated.",
            "Source GIS files remain read-only.",
            "Validation, API contract and release-readiness gates are visible.",
            "Generated artifacts are small enough for portfolio review.",
        ]

    def claim_boundaries(self) -> list[str]:
        return [
            self.review_wording,
            "This is an infrastructure indicator and field-review prioritization tool, not a crash prediction model.",
            "Missing OSM tags are data-quality flags, not proof of real-world absence.",
            "The publication ZIP excludes source GIS data.",
        ]

    def readme_markdown(self, bundle: dict) -> str:
        lines = [
            "# GeoReview Studio",
            "",
            "Local-first GIS review workbench for infrastructure risk indicators and portfolio-grade evidence.",
            "",
            f"- Bundle id: `{bundle.get('bundle_id')}`",
            f"- App version: `{bundle.get('app_version')}`",
            f"- Readiness: `{bundle.get('bundle_readiness')}`",
            f"- Status: `{bundle.get('bundle_status')}`",
            "",
            "## Overview",
            "",
        ]
        for section in bundle.get("readme_sections", []):
            lines.append(f"### {section.get('title')}")
            lines.append(section.get("body", ""))
            lines.append("")
        lines.extend(["## Repository Contents", ""])
        for item in bundle.get("repo_files", []):
            marker = "include" if item.get("include_now") else "exclude or optional"
            lines.append(f"- `{item.get('path')}` - {marker}: {item.get('purpose')}")
        lines.extend(["", "## Claim Boundaries", ""])
        for line in bundle.get("claim_boundaries", []):
            lines.append(f"- {line}")
        lines.extend(["", "Source GIS files remain read-only and are not included in this publication bundle.", ""])
        return "\n".join(lines)

    def case_study_markdown(self, bundle: dict) -> str:
        evidence = bundle.get("evidence_summary", {})
        lines = [
            "# Portfolio Case Study",
            "",
            "## Problem",
            "",
            "Road-safety and GIS review work often starts with heterogeneous local data. GeoReview Studio turns that evidence into reviewable infrastructure indicators while keeping claim boundaries explicit.",
            "",
            "## Implemented Pilot",
            "",
            f"The Kfar Saba pilot currently references `{evidence.get('generators')}` pedestrian generators, `{evidence.get('crossings')}` crossings and `{evidence.get('route_aware_rows')}` route-aware rows.",
            "",
            "## Engineering Highlights",
            "",
        ]
        for item in bundle.get("story_highlights", []):
            lines.append(f"- {item}")
        lines.extend(["", "## Review Wording", "", f"`{self.review_wording}`", ""])
        return "\n".join(lines)

    def repo_manifest_markdown(self, bundle: dict) -> str:
        lines = [
            "# Repository File Manifest",
            "",
            "| Path | Include now | Purpose |",
            "|---|---:|---|",
        ]
        for item in bundle.get("repo_files", []):
            lines.append(f"| `{item.get('path')}` | {str(item.get('include_now')).lower()} | {item.get('purpose')} |")
        lines.extend(["", "## Publication Checklist", "", "| Item | Required | Status |", "|---|---:|---|"])
        for item in bundle.get("publication_checklist", []):
            lines.append(f"| {item.get('item')} | {str(item.get('required')).lower()} | {item.get('status')} |")
        lines.append("")
        return "\n".join(lines)

    def bundle_html(self, bundle: dict) -> str:
        sections = "".join(
            f"<section><h2>{html.escape(str(section.get('title') or ''))}</h2><p>{html.escape(str(section.get('body') or ''))}</p></section>"
            for section in bundle.get("readme_sections", [])
        )
        repo_files = "".join(
            f"<tr><td>{html.escape(str(item.get('path') or ''))}</td><td>{html.escape(str(item.get('include_now') or ''))}</td><td>{html.escape(str(item.get('purpose') or ''))}</td></tr>"
            for item in bundle.get("repo_files", [])
        )
        checklist = "".join(
            f"<tr><td>{html.escape(str(item.get('item') or ''))}</td><td>{html.escape(str(item.get('required') or ''))}</td><td>{html.escape(str(item.get('status') or ''))}</td></tr>"
            for item in bundle.get("publication_checklist", [])
        )
        boundaries = "".join(f"<li>{html.escape(line)}</li>" for line in bundle.get("claim_boundaries", []))
        evidence = bundle.get("evidence_summary", {})
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>GitHub-ready Publication Bundle</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f8f4; color: #1f2933; }}
      .summary, section {{ background: white; border: 1px solid #d7d8d2; border-radius: 8px; padding: 14px; margin-bottom: 12px; }}
      table {{ width: 100%; border-collapse: collapse; background: white; margin-top: 8px; }}
      th, td {{ border: 1px solid #d7d8d2; padding: 8px; vertical-align: top; }}
      th {{ background: #eef0ea; text-align: left; }}
      code {{ background: #eef0ea; padding: 2px 5px; border-radius: 4px; }}
    </style>
  </head>
  <body>
    <h1>GitHub-ready Publication Bundle</h1>
    <div class="summary">
      <p><strong>{html.escape(str(bundle.get("headline") or ""))}</strong></p>
      <p>Bundle: <code>{html.escape(str(bundle.get("bundle_id") or ""))}</code>; status: <code>{html.escape(str(bundle.get("bundle_status") or ""))}</code>.</p>
      <p>Demo playbook: <code>{html.escape(str(bundle.get("demo_review_playbook_id") or ""))}</code>; release readiness: <code>{html.escape(str(evidence.get("validation_release_readiness") or ""))}</code>; checked endpoints: <code>{html.escape(str(evidence.get("api_contract_checked_endpoints") or 0))}</code>.</p>
      <p>ZIP excludes source GIS data.</p>
    </div>
    {sections}
    <section><h2>Repository File Manifest</h2><table><thead><tr><th>Path</th><th>Include</th><th>Purpose</th></tr></thead><tbody>{repo_files}</tbody></table></section>
    <section><h2>Publication Checklist</h2><table><thead><tr><th>Item</th><th>Required</th><th>Status</th></tr></thead><tbody>{checklist}</tbody></table></section>
    <section><h2>Claim Boundaries</h2><ul>{boundaries}</ul></section>
  </body>
</html>"""

    def write_zip(self, zip_path: Path, paths: list[Path]) -> None:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in paths:
                if path.exists() and self.safe_bundle_path(path):
                    zf.write(path, arcname=path.name)

    def bundle_dir(self, bundle_id: str) -> Path:
        return self.bundles_dir / safe_token(bundle_id, "missing_github_publication_bundle", 180)

    def safe_bundle_path(self, path: Path) -> bool:
        try:
            return str(path.resolve()).startswith(str(self.bundles_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
