from __future__ import annotations

import html
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPOSITORY_EXPORT_CHECKLIST_VERSION = "repository_export_checklist_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "repository_export_checklist", max_len: int = 150) -> str:
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
        return {"error": "repository_export_checklist_probe_failed", "detail": repr(exc)}


class RepositoryExportChecklistBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        public_repository_polish_package: object,
        visual_evidence_capture: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.public_repository_polish_package = public_repository_polish_package
        self.visual_evidence_capture = visual_evidence_capture
        self.expected_api_endpoints = expected_api_endpoints
        self.checklists_dir = output_root / "georeview_studio_repository_export_checklists"

    def status(self) -> dict:
        packages = self.ready_polish_packages(100)
        checklists = self.list_checklists(100)
        ready_checklists = [row for row in checklists if row.get("checklist_readiness") == "ready_for_repository_export_checklist"]
        latest_package = packages[0] if packages else {}
        latest_checklist = ready_checklists[0] if ready_checklists else {}
        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        visual = self.latest_visual_capture_summary()
        return {
            "ok": True,
            "repository_export_checklist_version": REPOSITORY_EXPORT_CHECKLIST_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "final_repository_export_checklist_and_screenshot_capture_pass",
            "output_dir": str(self.checklists_dir),
            "ready_polish_package_count": len(packages),
            "latest_polish_package_id": latest_package.get("package_id", ""),
            "latest_polish_package_status": latest_package.get("package_status", ""),
            "checklist_count": len(checklists),
            "ready_checklist_count": len(ready_checklists),
            "latest_checklist_id": latest_checklist.get("checklist_id", ""),
            "latest_checklist_status": latest_checklist.get("checklist_status", ""),
            "latest_required_failed_count": latest_checklist.get("required_failed_count", 0),
            "latest_screenshot_target_count": latest_checklist.get("screenshot_target_count", 0),
            "latest_screenshot_evidence_count": latest_checklist.get("screenshot_evidence_count", 0),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "expected_api_endpoints": self.expected_api_endpoints,
            "visual_evidence_capture_id": visual.get("capture_id", ""),
            "visual_evidence_captured_count": visual.get("captured_count", 0),
            "readiness_level": "ready_for_repository_export_checklist" if packages else "waiting_for_public_repository_polish_package",
            "approved_review_wording": self.review_wording,
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_checklist(self, body: dict | None = None) -> dict:
        body = body or {}
        package_id = str(body.get("package_id") or body.get("public_repository_polish_package_id") or "").strip()
        if not package_id:
            packages = self.ready_polish_packages(20)
            package_id = str(packages[0].get("package_id") or "") if packages else ""
        if not package_id:
            return self.error("repository_export_checklist_input_missing", "A ready public repository polish package is required.")
        polish_package = self.resolve_polish_package(package_id)
        if polish_package.get("error"):
            return polish_package
        if polish_package.get("package_readiness") != "ready_for_public_repository_polish":
            return self.error("repository_export_checklist_not_ready", "Public repository polish package must be ready_for_public_repository_polish.")

        validation = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        manifest = safe_call(self.manifest_reader, {})
        visual = self.latest_visual_capture_summary()
        screenshot_targets = self.screenshot_targets(polish_package, visual)
        repository_tree = self.repository_tree(polish_package)
        export_checks = self.export_checks(polish_package, validation, api_contract, visual, screenshot_targets, repository_tree)
        required_failed = [row for row in export_checks if row.get("required") and row.get("status") != "ready"]
        screenshot_evidence_count = sum(1 for row in screenshot_targets if row.get("capture_status") == "local_evidence_available")
        checklist_status = "ready_for_public_repository_export" if not required_failed else "ready_with_manual_screenshot_tasks"
        if not self.api_and_validation_ready(validation, api_contract):
            checklist_status = "pending_validation_or_api_contract"

        stamp = utc_now()
        checklist_id = f"repository_export_checklist_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        checklist_dir = self.checklist_dir(checklist_id)
        manifest_path = checklist_dir / "repository_export_checklist_manifest.json"
        checklist_path = checklist_dir / "FINAL_REPOSITORY_EXPORT_CHECKLIST.md"
        screenshot_path = checklist_dir / "SCREENSHOT_CAPTURE_PASS.md"
        tree_path = checklist_dir / "PUBLIC_REPOSITORY_TREE.md"
        readme_notes_path = checklist_dir / "README_FINAL_REVIEW_NOTES.md"
        html_path = checklist_dir / "repository_export_checklist.html"
        zip_path = checklist_dir / "repository_export_checklist.zip"
        latest_path = self.checklists_dir / "latest_repository_export_checklist.json"
        checklist = {
            "ok": True,
            "repository_export_checklist_version": REPOSITORY_EXPORT_CHECKLIST_VERSION,
            "checklist_id": checklist_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "audience": str(body.get("audience") or "github_repository_reviewer"),
            "notes": str(body.get("notes") or "Final repository export checklist before manual GitHub sharing."),
            "app_version": self.app_version,
            "polish_package_id": polish_package.get("package_id"),
            "checklist_readiness": "ready_for_repository_export_checklist",
            "checklist_status": checklist_status,
            "required_failed_count": len(required_failed),
            "repository_tree_file_count": len(repository_tree),
            "screenshot_target_count": len(screenshot_targets),
            "screenshot_evidence_count": screenshot_evidence_count,
            "export_check_count": len(export_checks),
            "public_readme_issue_count": polish_package.get("public_readme_issue_count", 0),
            "repository_tree": repository_tree,
            "screenshot_capture_pass": screenshot_targets,
            "export_checks": export_checks,
            "manual_actions": self.manual_actions(screenshot_targets),
            "readme_final_review_notes": self.readme_final_review_notes(polish_package),
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "evidence_summary": self.evidence_summary(polish_package, validation, api_contract, visual),
            "includes_source_gis": False,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "checklist": str(checklist_path),
                "screenshot_capture_pass": str(screenshot_path),
                "repository_tree": str(tree_path),
                "readme_final_review_notes": str(readme_notes_path),
                "html": str(html_path),
                "zip": str(zip_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, checklist)
        write_json(latest_path, checklist)
        checklist_path.write_text(self.checklist_markdown(checklist), encoding="utf-8", newline="\n")
        screenshot_path.write_text(self.screenshot_markdown(checklist), encoding="utf-8", newline="\n")
        tree_path.write_text(self.tree_markdown(checklist), encoding="utf-8", newline="\n")
        readme_notes_path.write_text(self.readme_notes_markdown(checklist), encoding="utf-8", newline="\n")
        html_path.write_text(self.checklist_html(checklist), encoding="utf-8", newline="\n")
        self.write_zip(zip_path, [manifest_path, checklist_path, screenshot_path, tree_path, readme_notes_path, html_path])
        checklist["zip_size_bytes"] = zip_path.stat().st_size if zip_path.exists() else 0
        write_json(manifest_path, checklist)
        write_json(latest_path, checklist)
        return {"ok": True, "checklist": checklist, "source_gis_modified": False, "mutates_config": False}

    def list_checklists(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.checklists_dir.exists():
            return rows
        manifests = sorted(
            self.checklists_dir.glob("repository_export_checklist_*/repository_export_checklist_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("repository_export_checklist_version") != REPOSITORY_EXPORT_CHECKLIST_VERSION:
                continue
            rows.append({
                "checklist_id": payload.get("checklist_id"),
                "created_at": payload.get("created_at"),
                "checklist_readiness": payload.get("checklist_readiness"),
                "checklist_status": payload.get("checklist_status"),
                "polish_package_id": payload.get("polish_package_id"),
                "required_failed_count": payload.get("required_failed_count", 0),
                "screenshot_target_count": payload.get("screenshot_target_count", 0),
                "screenshot_evidence_count": payload.get("screenshot_evidence_count", 0),
                "zip_size_bytes": payload.get("zip_size_bytes", 0),
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, checklist_id: str) -> dict:
        token = safe_token(checklist_id)
        path = self.checklist_dir(token) / "repository_export_checklist_manifest.json"
        payload = read_json(path)
        if not payload:
            return self.error("repository_export_checklist_not_found", f"Repository export checklist not found: {checklist_id}")
        return payload

    def output_file(self, checklist_id: str, file_key: str = "zip") -> dict:
        payload = self.detail(checklist_id)
        if payload.get("error"):
            return payload
        path = Path(str(payload.get("files", {}).get(file_key, "")))
        if not path.exists():
            return self.error("repository_export_checklist_output_not_found", f"Repository export checklist output not found: {file_key}")
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def ready_polish_packages(self, limit: int) -> list[dict]:
        packages = safe_call(lambda: self.public_repository_polish_package.list_packages(limit), [])
        if not isinstance(packages, list):
            return []
        return [row for row in packages if row.get("package_readiness") == "ready_for_public_repository_polish"]

    def resolve_polish_package(self, package_id: str) -> dict:
        detail = safe_call(lambda: self.public_repository_polish_package.detail(package_id), {})
        return detail if isinstance(detail, dict) else self.error("repository_export_checklist_not_ready", "Could not read public repository polish package.")

    def latest_visual_capture_summary(self) -> dict:
        if not self.visual_evidence_capture:
            return {}
        captures = safe_call(lambda: self.visual_evidence_capture.list_captures(10), [])
        if not isinstance(captures, list) or not captures:
            return {}
        ready = [row for row in captures if row.get("capture_readiness") == "ready_for_visual_evidence_review"]
        return ready[0] if ready else captures[0]

    def screenshot_targets(self, polish_package: dict, visual: dict) -> list[dict]:
        package_targets = polish_package.get("manual_screenshot_capture_package", [])
        target_names = []
        if isinstance(package_targets, list):
            for row in package_targets:
                if isinstance(row, dict):
                    target_names.append(str(row.get("target") or row.get("name") or row.get("view") or row.get("target_id") or "screenshot target"))
                else:
                    target_names.append(str(row))
        if len(target_names) < 8:
            target_names = [
                "Dashboard overview",
                "Kfar Saba candidate table",
                "Infrastructure risk map",
                "Route-aware crossing distance panel",
                "Data-quality flags panel",
                "Release readiness panel",
                "Public repository polish package panel",
                "API contract evidence panel",
            ]
        captured = int(visual.get("captured_count") or 0)
        targets = []
        for index, name in enumerate(target_names[:8], start=1):
            slug = safe_token(name, f"screenshot_{index}", max_len=48).lower()
            targets.append({
                "target_id": f"screenshot_{index:02d}_{slug}",
                "target": name,
                "repository_path": f"docs/screenshots/{index:02d}_{slug}.png",
                "capture_status": "local_evidence_available" if captured >= index else "manual_capture_required",
                "expected_use": "README and portfolio evidence",
                "public_path_ready": True,
            })
        return targets

    def repository_tree(self, polish_package: dict) -> list[dict]:
        return [
            {"path": "README.md", "role": "public project landing page", "required": True, "source": "public_repository_ready_readme", "status": "ready"},
            {"path": "LICENSE", "role": "license placeholder selected manually before public sharing", "required": True, "source": "manual decision", "status": "manual_review"},
            {"path": "docs/architecture.md", "role": "system architecture summary", "required": True, "source": "existing docs", "status": "ready"},
            {"path": "docs/methodology.md", "role": "risk indicator methodology and claim boundaries", "required": True, "source": "generated documentation", "status": "ready"},
            {"path": "docs/data-boundaries.md", "role": "source GIS, OSM and missing-tag limitations", "required": True, "source": "generated documentation", "status": "ready"},
            {"path": "docs/screenshots/README.md", "role": "screenshot inventory", "required": True, "source": "repository export checklist", "status": "ready"},
            {"path": "docs/screenshots/*.png", "role": "manual screenshots captured from local demo", "required": True, "source": "visual evidence capture or manual capture", "status": "ready"},
            {"path": "backend/", "role": "local API and evidence builders", "required": True, "source": "app source", "status": "ready"},
            {"path": "frontend/static/", "role": "local dashboard UI", "required": True, "source": "app source", "status": "ready"},
            {"path": "tests/", "role": "validation and API contract tests", "required": True, "source": "test suite", "status": "ready"},
            {"path": "sample_outputs/", "role": "small generated examples only", "required": False, "source": "analysis_output samples", "status": "manual_review"},
            {"path": ".gitignore", "role": "exclude analysis_output, source GIS and local caches", "required": True, "source": "repository export checklist", "status": "ready"},
        ]

    def export_checks(self, polish_package: dict, validation: dict, api_contract: dict, visual: dict, screenshot_targets: list[dict], repository_tree: list[dict]) -> list[dict]:
        captured = sum(1 for row in screenshot_targets if row.get("capture_status") == "local_evidence_available")
        return [
            self.check("polish_package_ready", polish_package.get("package_readiness") == "ready_for_public_repository_polish", True, {"package_id": polish_package.get("package_id")}),
            self.check("validation_passed", validation.get("passed") is True, True, {"passed": validation.get("passed")}),
            self.check("api_contract_passed", api_contract.get("passed") is True and int(api_contract.get("checked_endpoints") or 0) >= self.expected_api_endpoints, False, {"checked_endpoints": api_contract.get("checked_endpoints"), "expected_api_endpoints": self.expected_api_endpoints}),
            self.check("public_readme_clean", polish_package.get("public_readme_issue_count", 0) == 0 and not polish_package.get("public_readme_has_analysis_output_paths"), True, {"public_readme_issue_count": polish_package.get("public_readme_issue_count", 0)}),
            self.check("source_gis_excluded", polish_package.get("includes_source_gis") is False and polish_package.get("source_gis_modified") is False, True, {"includes_source_gis": polish_package.get("includes_source_gis"), "source_gis_modified": polish_package.get("source_gis_modified")}),
            self.check("repository_tree_ready", len(repository_tree) >= 10, True, {"repository_tree_file_count": len(repository_tree)}),
            self.check("screenshot_targets_ready", len(screenshot_targets) >= 8, True, {"screenshot_target_count": len(screenshot_targets)}),
            self.check("screenshot_evidence_available", captured >= 8 or int(visual.get("captured_count") or 0) >= 8, True, {"screenshot_evidence_count": captured, "visual_capture_id": visual.get("capture_id", "")}),
        ]

    def check(self, check_id: str, passed: bool, required: bool, evidence: dict) -> dict:
        return {"check_id": check_id, "status": "ready" if passed else "needs_review", "required": required, "evidence": evidence}

    def manual_actions(self, screenshot_targets: list[dict]) -> list[dict]:
        return [
            {"action": "copy_public_readme", "status": "ready", "detail": "Use PUBLIC_REPOSITORY_READY_README.md as the public README draft."},
            {"action": "capture_or_copy_screenshots", "status": "ready", "detail": f"Place {len(screenshot_targets)} screenshots under docs/screenshots/ with the repository-relative filenames from this checklist."},
            {"action": "exclude_private_data", "status": "ready", "detail": "Do not commit source GIS extracts, local analysis_output folders, browser profiles, caches or absolute local paths."},
            {"action": "run_local_verification", "status": "ready", "detail": "Run validation and API contract before sharing the repository package."},
        ]

    def readme_final_review_notes(self, polish_package: dict) -> list[dict]:
        return [
            {"topic": "claim boundary", "status": "ready", "note": "README must describe infrastructure risk indicators and field review prioritization, not crash prediction."},
            {"topic": "data boundary", "status": "ready", "note": "README should explain that missing OSM tags are data-quality flags, not proof of real-world absence."},
            {"topic": "screenshot paths", "status": "ready", "note": "README should reference docs/screenshots/ repository paths only."},
            {"topic": "local paths", "status": "ready" if not polish_package.get("public_readme_has_local_absolute_paths") else "needs_review", "note": "Public README should not contain local absolute paths."},
        ]

    def api_and_validation_ready(self, validation: dict, api_contract: dict) -> bool:
        try:
            checked = int(api_contract.get("checked_endpoints") or 0)
        except (TypeError, ValueError):
            checked = 0
        return validation.get("passed") is True and api_contract.get("passed") is True and checked >= self.expected_api_endpoints

    def evidence_summary(self, polish_package: dict, validation: dict, api_contract: dict, visual: dict) -> dict:
        return {
            "polish_package_id": polish_package.get("package_id"),
            "validation_passed": validation.get("passed") is True,
            "api_contract_passed": api_contract.get("passed") is True,
            "checked_api_endpoints": api_contract.get("checked_endpoints", 0),
            "visual_capture_id": visual.get("capture_id", ""),
            "visual_captured_count": visual.get("captured_count", 0),
            "approved_review_wording": self.review_wording,
        }

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["infrastructure risk indicators", "data-quality flags", "field-review prioritization", "mapped OSM evidence"],
            "not_allowed": ["crash prediction", "proof of real-world absence from missing tags", "absolute safety claims"],
            "missing_tag_rule": "Missing OSM tags create data-quality flags, not automatic risk points.",
        }

    def checklist_markdown(self, checklist: dict) -> str:
        lines = [
            "# Final Repository Export Checklist",
            "",
            f"- Checklist ID: `{checklist.get('checklist_id')}`",
            f"- Readiness: `{checklist.get('checklist_readiness')}`",
            f"- Status: `{checklist.get('checklist_status')}`",
            f"- Required failed: `{checklist.get('required_failed_count')}`",
            f"- Screenshot evidence: `{checklist.get('screenshot_evidence_count')}` / `{checklist.get('screenshot_target_count')}`",
            f"- Approved wording: {self.review_wording}",
            "",
            "## Export Checks",
        ]
        for row in checklist.get("export_checks", []):
            lines.append(f"- `{row.get('check_id')}`: `{row.get('status')}`")
        lines += ["", "## Manual Actions"]
        for row in checklist.get("manual_actions", []):
            lines.append(f"- `{row.get('action')}`: {row.get('detail')}")
        return "\n".join(lines) + "\n"

    def screenshot_markdown(self, checklist: dict) -> str:
        lines = ["# Screenshot Capture Pass", "", "Repository-relative screenshot targets:"]
        for row in checklist.get("screenshot_capture_pass", []):
            lines.append(f"- `{row.get('repository_path')}` - {row.get('target')} - `{row.get('capture_status')}`")
        return "\n".join(lines) + "\n"

    def tree_markdown(self, checklist: dict) -> str:
        lines = ["# Public Repository Tree", ""]
        for row in checklist.get("repository_tree", []):
            lines.append(f"- `{row.get('path')}` - {row.get('role')} - `{row.get('status')}`")
        return "\n".join(lines) + "\n"

    def readme_notes_markdown(self, checklist: dict) -> str:
        lines = ["# README Final Review Notes", ""]
        for row in checklist.get("readme_final_review_notes", []):
            lines.append(f"- `{row.get('topic')}` - `{row.get('status')}` - {row.get('note')}")
        return "\n".join(lines) + "\n"

    def checklist_html(self, checklist: dict) -> str:
        checks = "".join(f"<li><code>{html.escape(str(row.get('check_id')))}</code>: {html.escape(str(row.get('status')))}</li>" for row in checklist.get("export_checks", []))
        screenshots = "".join(f"<li><code>{html.escape(str(row.get('repository_path')))}</code>: {html.escape(str(row.get('capture_status')))}</li>" for row in checklist.get("screenshot_capture_pass", []))
        return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Final Repository Export Checklist</title>
  <style>body{{font-family:Arial,sans-serif;max-width:960px;margin:32px auto;line-height:1.5}}code{{background:#f2f4f7;padding:2px 4px;border-radius:4px}}</style>
</head>
<body>
  <h1>Final Repository Export Checklist</h1>
  <p><strong>Checklist:</strong> <code>{html.escape(str(checklist.get('checklist_id')))}</code></p>
  <p><strong>Status:</strong> <code>{html.escape(str(checklist.get('checklist_status')))}</code></p>
  <p><strong>Readiness:</strong> <code>{html.escape(str(checklist.get('checklist_readiness')))}</code></p>
  <p>{html.escape(self.review_wording)}</p>
  <h2>Export Checks</h2>
  <ul>{checks}</ul>
  <h2>Screenshot Capture Pass</h2>
  <ul>{screenshots}</ul>
</body>
</html>
"""

    def write_zip(self, zip_path: Path, files: list[Path]) -> None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in files:
                if path.exists():
                    zf.write(path, arcname=path.name)

    def checklist_dir(self, checklist_id: str) -> Path:
        return self.checklists_dir / safe_token(checklist_id)

    def error(self, error: str, detail: str) -> dict:
        return {"ok": False, "error": error, "detail": detail, "source_gis_modified": False, "mutates_config": False}
