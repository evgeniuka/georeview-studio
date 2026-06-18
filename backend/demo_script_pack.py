from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


DEMO_SCRIPT_PACK_VERSION = "demo_script_pack_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "demo_script_pack", max_len: int = 120) -> str:
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
        return {"error": "demo_script_pack_probe_failed", "detail": repr(exc)}


class DemoScriptPackBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        portable_release_package: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.portable_release_package = portable_release_package
        self.expected_api_endpoints = expected_api_endpoints
        self.packs_dir = output_root / "georeview_studio_demo_script_packs"

    def status(self) -> dict:
        packages = self.package_rows(100)
        packs = self.list_packs(100)
        ready_packs = [row for row in packs if row.get("pack_readiness") == "ready_for_demo_walkthrough"]
        portable_status = safe_call(self.portable_release_package.status, {})
        manifest = safe_call(self.manifest_reader, {})
        targets = self.screenshot_targets()
        return {
            "ok": True,
            "demo_script_pack_version": DEMO_SCRIPT_PACK_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "repeatable_portfolio_walkthrough_and_screenshot_smoke",
            "output_dir": str(self.packs_dir),
            "portable_package_count": len(packages),
            "ready_portable_package_count": len([row for row in packages if row.get("package_readiness") == "ready_to_share_portable_release"]),
            "screenshot_target_count": len(targets),
            "script_step_count": len(self.script_steps()),
            "pack_count": len(packs),
            "ready_pack_count": len(ready_packs),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_demo_script_pack" if self.is_ready(portable_status, packages, targets) else "waiting_for_portable_release_package",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_pack(self, body: dict | None = None) -> dict:
        body = body or {}
        package_id = str(body.get("package_id") or "").strip()
        package = self.resolve_package(package_id)
        if package.get("error"):
            return package
        if package.get("package_readiness") != "ready_to_share_portable_release":
            return self.error("demo_script_pack_not_ready", "The selected portable release package must be ready_to_share_portable_release.")

        targets = self.screenshot_targets()
        steps = self.script_steps()
        if len(targets) < 6 or len(steps) < 6:
            return self.error("demo_script_pack_input_missing", "Demo script pack requires at least six screenshot targets and script steps.")

        stamp = utc_now()
        pack_id = f"demo_script_pack_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        pack_dir = self.pack_dir(pack_id)
        pack_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = pack_dir / "demo_script_pack_manifest.json"
        script_path = pack_dir / "demo_script.md"
        smoke_path = pack_dir / "screenshot_smoke_plan.md"
        contact_sheet_path = pack_dir / "screenshot_contact_sheet.html"
        latest_path = self.packs_dir / "latest_demo_script_pack.json"
        validation_summary = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        pack = {
            "ok": True,
            "demo_script_pack_version": DEMO_SCRIPT_PACK_VERSION,
            "pack_id": pack_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Repeatable portfolio demo script and screenshot smoke plan."),
            "app_version": self.app_version,
            "portable_release_package_id": package.get("package_id"),
            "pack_readiness": "ready_for_demo_walkthrough",
            "script_step_count": len(steps),
            "screenshot_target_count": len(targets),
            "script_steps": steps,
            "screenshot_targets": targets,
            "demo_duration_minutes": 8,
            "validation_summary": {
                "passed": validation_summary.get("passed"),
                "app_version": validation_summary.get("app_version"),
                "release_readiness_level": validation_summary.get("release_readiness_level"),
                "release_readiness_failed_gates": validation_summary.get("release_readiness_failed_gates"),
            },
            "api_contract": {
                "passed": api_contract.get("passed"),
                "checked_endpoints": api_contract.get("checked_endpoints"),
            },
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "manifest": str(manifest_path),
                "demo_script": str(script_path),
                "screenshot_smoke_plan": str(smoke_path),
                "contact_sheet": str(contact_sheet_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, pack)
        write_json(latest_path, pack)
        script_path.write_text(self.demo_script_markdown(pack, package), encoding="utf-8", newline="\n")
        smoke_path.write_text(self.smoke_plan_markdown(pack), encoding="utf-8", newline="\n")
        contact_sheet_path.write_text(self.contact_sheet_html(pack), encoding="utf-8", newline="\n")
        return {"ok": True, "pack": pack, "source_gis_modified": False, "mutates_config": False}

    def list_packs(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.packs_dir.exists():
            return rows
        manifests = sorted(
            self.packs_dir.glob("demo_script_pack_*/demo_script_pack_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            payload = read_json(path)
            if payload.get("demo_script_pack_version") != DEMO_SCRIPT_PACK_VERSION:
                continue
            rows.append({
                "pack_id": payload.get("pack_id"),
                "created_at": payload.get("created_at"),
                "pack_readiness": payload.get("pack_readiness"),
                "portable_release_package_id": payload.get("portable_release_package_id"),
                "script_step_count": payload.get("script_step_count"),
                "screenshot_target_count": payload.get("screenshot_target_count"),
                "download_url": f"/api/demo-script-pack/packs/{payload.get('pack_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, pack_id: str) -> dict:
        path = self.pack_dir(pack_id) / "demo_script_pack_manifest.json"
        if not path.exists() or not self.safe_pack_path(path):
            return {"ok": False, "error": "demo_script_pack_not_found", "pack_id": pack_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "demo_script_pack_not_found", "pack_id": pack_id, "source_gis_modified": False}
        return payload

    def output_file(self, pack_id: str, output_id: str = "demo_script") -> dict:
        detail = self.detail(pack_id)
        if detail.get("error"):
            return detail
        if output_id not in {"demo_script", "markdown"}:
            return {"ok": False, "error": "demo_script_pack_output_not_found", "pack_id": pack_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("demo_script") or ""))
        if not path.exists() or not self.safe_pack_path(path):
            return {"ok": False, "error": "demo_script_pack_output_not_found", "pack_id": pack_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def resolve_package(self, package_id: str) -> dict:
        if package_id:
            detail = safe_call(lambda: self.portable_release_package.detail(package_id), {})
            return detail if isinstance(detail, dict) else self.error("portable_release_package_not_found", "Portable package detail failed.")
        packages = self.package_rows(1)
        if not packages:
            return self.error("demo_script_pack_input_missing", "At least one ready portable release package is required.")
        detail = safe_call(lambda: self.portable_release_package.detail(str(packages[0].get("package_id") or "")), {})
        return detail if isinstance(detail, dict) else self.error("portable_release_package_not_found", "Portable package detail failed.")

    def package_rows(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.portable_release_package.list_packages(limit), [])
        return rows if isinstance(rows, list) else []

    def is_ready(self, portable_status: object, packages: list[dict], targets: list[dict]) -> bool:
        if not isinstance(portable_status, dict):
            return False
        return (
            portable_status.get("portable_release_package_version") == "portable_release_package_v001"
            and int(portable_status.get("ready_package_count") or 0) >= 1
            and len(packages) >= 1
            and len(targets) >= 6
        )

    def script_steps(self) -> list[dict]:
        return [
            {"step_id": "open_local_app", "minute": "0:00", "title": "Open GeoReview Studio", "talk_track": "Show that this is a local-first GIS review workbench and source GIS files remain read-only.", "evidence": "Health endpoint and current version."},
            {"step_id": "show_source_scope", "minute": "0:45", "title": "Show Data Scope", "talk_track": "Explain Kfar Saba pilot, OSM/Geofabrik evidence, and the difference between mapped evidence and real-world absence.", "evidence": "Source onboarding and validation summary."},
            {"step_id": "show_safe_access_profile", "minute": "1:45", "title": "Show Safe Access Indicators", "talk_track": "Review pedestrian generators, crossings, road proximity and field-review prioritization.", "evidence": "Dashboard candidates and map features."},
            {"step_id": "show_multi_profile_reuse", "minute": "3:00", "title": "Show Reusable Profiles", "talk_track": "Move from Safe Access to transit, park/playground and OSM tag quality profiles.", "evidence": "Profile dashboard rows and profile reports."},
            {"step_id": "show_reproducibility", "minute": "4:15", "title": "Show Reproducibility Evidence", "talk_track": "Open execution diff, audit packet and reviewer index to prove repeatable local evidence.", "evidence": "Reproducibility audit packet and reviewer audit index."},
            {"step_id": "show_portable_package", "minute": "5:45", "title": "Show Portable Release Package", "talk_track": "Download/open the small release ZIP and show that it excludes source GIS data.", "evidence": "Portable release package manifest and ZIP download."},
            {"step_id": "claim_boundary", "minute": "6:45", "title": "State Claim Boundary", "talk_track": REVIEW_WORDING, "evidence": "Approved wording in manifest, reports and demo script."},
            {"step_id": "next_steps", "minute": "7:30", "title": "Close With Engineering Roadmap", "talk_track": "Explain PostGIS, profile SDK, upload guardrails and future city pilots as engineering growth paths.", "evidence": "Product architecture roadmap and release readiness."},
        ]

    def screenshot_targets(self) -> list[dict]:
        base = "http://127.0.0.1:8831"
        return [
            {"target_id": "home_overview", "url": f"{base}/", "selector_hint": "header", "expected_text": "GeoReview Studio"},
            {"target_id": "source_guardrails_panel", "url": f"{base}/", "selector_hint": "Source Import Guardrails", "expected_text": "Source Import Guardrails"},
            {"target_id": "portfolio_launcher_panel", "url": f"{base}/", "selector_hint": "Portfolio Export Launcher", "expected_text": "Portfolio Export Launcher"},
            {"target_id": "portable_package_panel", "url": f"{base}/", "selector_hint": "Portable Release Package", "expected_text": "Portable Release Package"},
            {"target_id": "demo_script_pack_panel", "url": f"{base}/", "selector_hint": "Demo Script Pack", "expected_text": "Demo Script Pack"},
            {"target_id": "release_readiness_api", "url": f"{base}/api/release-readiness", "selector_hint": "json", "expected_text": "ready_for_local_portfolio_demo"},
            {"target_id": "portable_package_api", "url": f"{base}/api/portable-release-package", "selector_hint": "json", "expected_text": "portable_release_package_v001"},
            {"target_id": "demo_script_pack_api", "url": f"{base}/api/demo-script-pack", "selector_hint": "json", "expected_text": "demo_script_pack_v001"},
        ]

    def demo_script_markdown(self, pack: dict, package: dict) -> str:
        lines = [
            "# Demo Script Pack",
            "",
            f"- Pack id: `{pack.get('pack_id')}`",
            f"- App version: `{pack.get('app_version')}`",
            f"- Portable package: `{package.get('package_id')}`",
            f"- Duration: `{pack.get('demo_duration_minutes')}` minutes",
            f"- API endpoints checked: `{pack.get('api_contract', {}).get('checked_endpoints')}`",
            f"- Release readiness: `{pack.get('validation_summary', {}).get('release_readiness_level')}`",
            "",
            "## Opening",
            "",
            "GeoReview Studio is a local-first GIS evidence workbench. The first implemented domain is Safe Access Israel for pedestrian infrastructure risk indicators near generators such as schools, bus stops, parks and playgrounds.",
            "",
            "It does not claim crash risk and it does not infer real-world absence from missing OSM tags.",
            "",
            "## Walkthrough",
            "",
        ]
        for step in pack.get("script_steps", []):
            lines.extend([
                f"### {step.get('minute')} - {step.get('title')}",
                "",
                f"- Step id: `{step.get('step_id')}`",
                f"- Say: {step.get('talk_track')}",
                f"- Evidence: {step.get('evidence')}",
                "",
            ])
        lines.extend([
            "## Screenshot Smoke Targets",
            "",
        ])
        for target in pack.get("screenshot_targets", []):
            lines.append(f"- `{target.get('target_id')}` - {target.get('url')} - expected `{target.get('expected_text')}`")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- Missing OSM tags remain data-quality evidence unless an explicit mapped value is present.",
            "- The demo is a portfolio walkthrough over generated evidence, not automated site judgement.",
            "",
        ])
        return "\n".join(lines)

    def smoke_plan_markdown(self, pack: dict) -> str:
        lines = [
            "# Screenshot Smoke Plan",
            "",
            "Use this checklist while capturing portfolio screenshots or recording the walkthrough.",
            "",
            "## Targets",
            "",
        ]
        for index, target in enumerate(pack.get("screenshot_targets", []), start=1):
            lines.extend([
                f"{index}. `{target.get('target_id')}`",
                f"   URL: `{target.get('url')}`",
                f"   Expected text: `{target.get('expected_text')}`",
                f"   Selector hint: `{target.get('selector_hint')}`",
                "",
            ])
        lines.extend([
            "## Pass Criteria",
            "",
            "- The page or endpoint loads locally.",
            "- Expected text is visible in the rendered page or JSON response.",
            "- No screenshot or narration uses absolute safety claims.",
            "- The portable release package remains evidence-only and excludes source GIS files.",
            "",
        ])
        return "\n".join(lines)

    def contact_sheet_html(self, pack: dict) -> str:
        cards = "\n".join(
            f"<section><h2>{target.get('target_id')}</h2><p><code>{target.get('url')}</code></p><p>Expected: <strong>{target.get('expected_text')}</strong></p></section>"
            for target in pack.get("screenshot_targets", [])
        )
        return f"""<!doctype html>
<html lang=\"en\">
<head><meta charset=\"utf-8\"><title>Demo Script Pack Contact Sheet</title>
<style>body{{font-family:Arial,sans-serif;margin:24px;background:#f7f7f5;color:#1d1d1b}}section{{border:1px solid #bbb;background:#fff;margin:12px 0;padding:16px;border-radius:6px}}code{{font-size:13px}}</style></head>
<body>
<h1>Demo Script Pack Contact Sheet</h1>
<p>Pack: <code>{pack.get('pack_id')}</code></p>
{cards}
<h2>Claim Boundary</h2>
<p>{self.review_wording}</p>
</body>
</html>"""

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["infrastructure risk indicators", "data-quality flags", "field-review prioritization", "portfolio walkthrough evidence"],
            "not_allowed": ["crash prediction", "proof of real-world absence from missing tags", "absolute safety claims"],
            "missing_tag_rule": "Missing OSM tags add data-quality flags, not risk points by default.",
        }

    def pack_dir(self, pack_id: str) -> Path:
        return self.packs_dir / safe_token(pack_id, "missing_pack", 180)

    def safe_pack_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.packs_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
