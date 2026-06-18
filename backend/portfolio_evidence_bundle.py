from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PORTFOLIO_EVIDENCE_BUNDLE_VERSION = "portfolio_evidence_bundle_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "portfolio_evidence_bundle") -> str:
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
        return {"error": "portfolio_evidence_probe_failed", "detail": repr(exc)}


class PortfolioEvidenceBundleBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        dependencies: dict[str, object],
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.dependencies = dependencies
        self.bundles_dir = output_root / "georeview_studio_portfolio_evidence_bundles"

    def status(self) -> dict:
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "portfolio_evidence_bundle_version": PORTFOLIO_EVIDENCE_BUNDLE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "bundle_count": len(self.list_bundles(500)),
            "bundle_dir": str(self.bundles_dir),
            "evidence_sections": [
                "project_manifest",
                "release_readiness_snapshot",
                "guided_portfolio_demo_snapshot",
                "validation_summary",
                "api_contract_summary",
                "portfolio_case_study",
                "portfolio_pitch",
                "sample_review_candidates",
                "recent_reports",
            ],
            "default_action": "create_shareable_portfolio_evidence_bundle",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_bundle(self, body: dict | None = None) -> dict:
        body = body or {}
        stamp = utc_now()
        bundle_id = f"portfolio_evidence_bundle_{stamp.replace(':', '_')}_{safe_token(self.app_version)}"
        bundle_dir = self.bundles_dir / bundle_id
        files_dir = bundle_dir / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        release_snapshot = self.ensure_release_snapshot(body)
        demo_snapshot = self.ensure_demo_snapshot(body)
        evidence_files = self.collect_evidence_files(release_snapshot, demo_snapshot)
        copied_files = []
        for item in evidence_files:
            src = Path(str(item.get("source_path") or ""))
            if not src.exists() or not src.is_file():
                continue
            target = files_dir / f"{safe_token(item.get('label'), 'evidence')}_{src.name}"
            shutil.copy2(src, target)
            copied_files.append({
                "label": item.get("label"),
                "role": item.get("role"),
                "source_path": str(src),
                "bundle_path": str(target),
                "size_bytes": target.stat().st_size,
            })

        manifest = safe_call(self.manifest_reader, {})
        readiness_overview = release_snapshot.get("overview", {}) if isinstance(release_snapshot, dict) else {}
        demo_overview = demo_snapshot.get("overview", {}) if isinstance(demo_snapshot, dict) else {}
        reports = self.recent_reports()
        export_bundles = self.recent_export_bundles()
        bundle = {
            "ok": True,
            "bundle_id": bundle_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Shareable portfolio evidence bundle."),
            "portfolio_evidence_bundle_version": PORTFOLIO_EVIDENCE_BUNDLE_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "readiness_level": readiness_overview.get("readiness_level"),
            "readiness_gate_count": readiness_overview.get("summary", {}).get("gate_count"),
            "readiness_failed_gate_count": readiness_overview.get("summary", {}).get("failed_gate_count"),
            "portfolio_demo_step_count": demo_snapshot.get("step_count") or demo_overview.get("step_count"),
            "copied_file_count": len(copied_files),
            "copied_files": copied_files,
            "recent_reports": reports[:5],
            "recent_export_bundles": export_bundles[:5],
            "approved_review_wording": self.review_wording,
            "claim_boundary": "This bundle supports portfolio review of infrastructure indicators and data-quality evidence; it is not a crash prediction artifact.",
            "source_gis_modified": False,
            "mutates_config": False,
        }
        json_path = bundle_dir / f"{bundle_id}.json"
        md_path = bundle_dir / f"{bundle_id}.md"
        latest_path = self.bundles_dir / "latest_portfolio_evidence_bundle.json"
        bundle["files"] = {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path), "directory": str(bundle_dir)}
        write_json(json_path, bundle)
        write_json(latest_path, bundle)
        md_path.write_text(self.bundle_markdown(bundle), encoding="utf-8", newline="\n")
        return {"ok": True, "bundle": bundle, "source_gis_modified": False, "mutates_config": False}

    def list_bundles(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.bundles_dir.exists():
            return rows
        for path in sorted(self.bundles_dir.glob("portfolio_evidence_bundle_*/portfolio_evidence_bundle_*.json"), reverse=True):
            payload = read_json(path)
            if not payload:
                continue
            rows.append({
                "bundle_id": payload.get("bundle_id"),
                "created_at": payload.get("created_at"),
                "app_version": payload.get("app_version"),
                "readiness_level": payload.get("readiness_level"),
                "copied_file_count": payload.get("copied_file_count"),
                "json_file": str(path),
                "markdown_file": payload.get("files", {}).get("markdown"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, bundle_id: str) -> dict:
        token = safe_token(bundle_id, "missing")
        path = self.bundles_dir / token / f"{token}.json"
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "portfolio_evidence_bundle_not_found", "bundle_id": bundle_id, "source_gis_modified": False}
        return payload

    def output_file(self, bundle_id: str, output_id: str = "portfolio_evidence_bundle_report") -> dict:
        detail = self.detail(bundle_id)
        if detail.get("error"):
            return detail
        if output_id not in {"portfolio_evidence_bundle_report", "markdown"}:
            return {"ok": False, "error": "portfolio_evidence_bundle_output_not_found", "bundle_id": bundle_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists():
            return {"ok": False, "error": "portfolio_evidence_bundle_output_not_found", "bundle_id": bundle_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False}

    def ensure_release_snapshot(self, body: dict) -> dict:
        release_readiness = self.dependencies.get("release_readiness")
        if not release_readiness:
            return {}
        if body.get("reuse_latest", True):
            latest = read_json(self.output_root / "georeview_studio_release_readiness" / "latest_release_readiness_snapshot.json")
            if latest:
                return latest
        result = safe_call(lambda: release_readiness.create_snapshot({"created_by": "portfolio_evidence_bundle", "notes": "Bundle-created readiness snapshot."}), {})
        return result.get("snapshot", {}) if isinstance(result, dict) else {}

    def ensure_demo_snapshot(self, body: dict) -> dict:
        portfolio_demo = self.dependencies.get("portfolio_demo")
        if not portfolio_demo:
            return {}
        if body.get("reuse_latest", True):
            latest = read_json(self.output_root / "georeview_studio_portfolio_demo" / "latest_portfolio_demo_snapshot.json")
            if latest:
                return latest
        result = safe_call(lambda: portfolio_demo.create_snapshot({"created_by": "portfolio_evidence_bundle", "notes": "Bundle-created guided demo snapshot."}), {})
        return result.get("snapshot", {}) if isinstance(result, dict) else {}

    def collect_evidence_files(self, release_snapshot: dict, demo_snapshot: dict) -> list[dict]:
        portfolio_dir = self.project_dir / "portfolio"
        files = [
            {"label": "project_manifest", "role": "release metadata", "source_path": self.project_dir / "project_manifest.json"},
            {"label": "validation_summary", "role": "validation evidence", "source_path": self.project_dir / "validation_summary.json"},
            {"label": "api_contract_summary", "role": "API contract evidence", "source_path": self.project_dir / "api_contract_summary.json"},
            {"label": "portfolio_case_study", "role": "case study narrative", "source_path": portfolio_dir / "case_study.md"},
            {"label": "portfolio_pitch", "role": "short pitch", "source_path": portfolio_dir / "portfolio_pitch.md"},
            {"label": "sample_review_candidates", "role": "sample CSV export", "source_path": portfolio_dir / "sample_review_candidates_top20.csv"},
            {"label": "portfolio_manifest", "role": "portfolio artifact manifest", "source_path": portfolio_dir / "portfolio_manifest.json"},
            {"label": "static_map", "role": "static SVG map", "source_path": portfolio_dir / "assets" / "kfar_saba_static_map.svg"},
        ]
        for label, snapshot in [("release_readiness_snapshot", release_snapshot), ("portfolio_demo_snapshot", demo_snapshot)]:
            for key in ["json", "markdown"]:
                path = snapshot.get("files", {}).get(key) if isinstance(snapshot, dict) else ""
                if path:
                    files.append({"label": f"{label}_{key}", "role": f"{label} {key}", "source_path": Path(path)})
        return files

    def recent_reports(self) -> list[dict]:
        reports = self.dependencies.get("portfolio_reports")
        rows = safe_call(lambda: reports.list_reports(10), []) if reports else []
        return rows if isinstance(rows, list) else []

    def recent_export_bundles(self) -> list[dict]:
        bundles = self.dependencies.get("profile_export_bundles")
        rows = safe_call(lambda: bundles.list_bundles(10), []) if bundles else []
        return rows if isinstance(rows, list) else []

    def bundle_markdown(self, bundle: dict) -> str:
        lines = [
            "# GeoReview Studio Shareable Portfolio Evidence Bundle",
            "",
            f"Bundle: `{bundle.get('bundle_id')}`",
            f"Created: `{bundle.get('created_at')}`",
            f"App version: `{bundle.get('app_version')}`",
            f"Readiness: `{bundle.get('readiness_level')}`",
            "",
            "Approved review wording:",
            "",
            f"`{self.review_wording}`",
            "",
            "## Included Evidence Files",
            "",
        ]
        for item in bundle.get("copied_files", []):
            lines.append(f"- `{item.get('label')}`: `{item.get('bundle_path')}`")
        lines.extend([
            "",
            "## Recent Reports",
            "",
        ])
        for report in bundle.get("recent_reports", []):
            lines.append(f"- `{report.get('report_id')}` ({report.get('report_type')})")
        lines.extend([
            "",
            "## Claim Boundary",
            "",
            "This bundle supports portfolio review of infrastructure indicators and data-quality evidence.",
            "It does not make crash-prediction or absolute safety claims.",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)
