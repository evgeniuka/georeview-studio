from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


PORTFOLIO_EXPORT_LAUNCHER_VERSION = "portfolio_export_launcher_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "portfolio_export_launcher", max_len: int = 120) -> str:
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
        return {"error": "portfolio_export_launcher_probe_failed", "detail": repr(exc)}


class PortfolioExportLauncherBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        reviewer_audit_index: object,
        reproducibility_audit_packet: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.reviewer_audit_index = reviewer_audit_index
        self.reproducibility_audit_packet = reproducibility_audit_packet
        self.expected_api_endpoints = expected_api_endpoints
        self.launcher_dir = output_root / "georeview_studio_portfolio_export_launchers"

    def status(self) -> dict:
        targets = self.launch_targets(500)
        launchers = self.list_launchers(500)
        ready_launchers = [row for row in launchers if row.get("launcher_readiness") == "ready_for_portfolio_launch"]
        manifest = safe_call(self.manifest_reader, {})
        reviewer_status = safe_call(self.reviewer_audit_index.status, {})
        packet_status = safe_call(self.reproducibility_audit_packet.status, {})
        return {
            "ok": True,
            "portfolio_export_launcher_version": PORTFOLIO_EXPORT_LAUNCHER_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "start_here_portfolio_reviewer_entrypoint",
            "output_dir": str(self.launcher_dir),
            "launch_target_count": len(targets),
            "reviewer_index_count": len([row for row in targets if row.get("kind") == "reviewer_audit_index"]),
            "audit_packet_count": len([row for row in targets if row.get("kind") == "reproducibility_audit_packet"]),
            "portfolio_artifact_count": len([row for row in targets if row.get("kind") not in {"reviewer_audit_index", "reproducibility_audit_packet"}]),
            "launcher_count": len(launchers),
            "ready_launcher_count": len(ready_launchers),
            "ready_index_count": reviewer_status.get("ready_index_count") if isinstance(reviewer_status, dict) else 0,
            "ready_packet_count": packet_status.get("ready_packet_count") if isinstance(packet_status, dict) else 0,
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_portfolio_launch" if self.is_ready(targets, reviewer_status, packet_status) else "waiting_for_reviewer_artifacts",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_launcher(self, body: dict | None = None) -> dict:
        body = body or {}
        target_limit = max(3, min(int(body.get("target_limit") or 25), 100))
        targets = self.launch_targets(target_limit)
        reviewer_status = safe_call(self.reviewer_audit_index.status, {})
        packet_status = safe_call(self.reproducibility_audit_packet.status, {})
        if not targets:
            return self.error("portfolio_export_launcher_input_missing", "At least one launch target is required.")
        if len(targets) < 3 or not self.is_ready(targets, reviewer_status, packet_status):
            return self.error("portfolio_export_launcher_not_ready", "Reviewer index, audit packet and portfolio artifact evidence are required.")

        stamp = utc_now()
        launcher_id = f"portfolio_export_launcher_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        json_path = self.launcher_path(launcher_id, ".json")
        md_path = self.launcher_path(launcher_id, ".md")
        html_path = self.launcher_path(launcher_id, ".html")
        latest_path = self.launcher_dir / "latest_portfolio_export_launcher.json"
        validation_summary = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        launcher = {
            "ok": True,
            "portfolio_export_launcher_version": PORTFOLIO_EXPORT_LAUNCHER_VERSION,
            "launcher_id": launcher_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Start-here launcher for local portfolio review."),
            "app_version": self.app_version,
            "launcher_readiness": "ready_for_portfolio_launch",
            "launch_target_count": len(targets),
            "primary_actions": self.primary_actions(targets),
            "launch_targets": targets,
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
            "files": {"json": str(json_path), "markdown": str(md_path), "html": str(html_path), "latest": str(latest_path)},
        }
        write_json(json_path, launcher)
        write_json(latest_path, launcher)
        md_path.write_text(self.launcher_markdown(launcher), encoding="utf-8", newline="\n")
        html_path.write_text(self.launcher_html(launcher), encoding="utf-8", newline="\n")
        return {"ok": True, "launcher": launcher, "source_gis_modified": False, "mutates_config": False}

    def list_launchers(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.launcher_dir.exists():
            return rows
        for path in sorted(self.launcher_dir.glob("portfolio_export_launcher_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            payload = read_json(path)
            if payload.get("portfolio_export_launcher_version") != PORTFOLIO_EXPORT_LAUNCHER_VERSION:
                continue
            rows.append({
                "launcher_id": payload.get("launcher_id"),
                "created_at": payload.get("created_at"),
                "launcher_readiness": payload.get("launcher_readiness"),
                "launch_target_count": payload.get("launch_target_count"),
                "download_url": f"/api/portfolio-export-launcher/launchers/{payload.get('launcher_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, launcher_id: str) -> dict:
        path = self.launcher_path(launcher_id, ".json")
        if not path.exists() or not self.safe_launcher_path(path):
            return {"ok": False, "error": "portfolio_export_launcher_not_found", "launcher_id": launcher_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "portfolio_export_launcher_not_found", "launcher_id": launcher_id, "source_gis_modified": False}
        return payload

    def output_file(self, launcher_id: str, output_id: str = "portfolio_export_launcher") -> dict:
        detail = self.detail(launcher_id)
        if detail.get("error"):
            return detail
        if output_id not in {"portfolio_export_launcher", "markdown"}:
            return {"ok": False, "error": "portfolio_export_launcher_output_not_found", "launcher_id": launcher_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_launcher_path(path):
            return {"ok": False, "error": "portfolio_export_launcher_output_not_found", "launcher_id": launcher_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def launch_targets(self, limit: int = 25) -> list[dict]:
        rows: list[dict] = []
        for row in self.safe_indexes(5):
            rows.append({
                "kind": "reviewer_audit_index",
                "artifact_id": row.get("index_id"),
                "label": "Reviewer audit index",
                "readiness": row.get("index_readiness"),
                "download_url": row.get("download_url"),
                "path": "",
                "source_gis_modified": False,
            })
        for row in self.safe_packets(5):
            rows.append({
                "kind": "reproducibility_audit_packet",
                "artifact_id": row.get("packet_id"),
                "label": "Reproducibility audit packet",
                "readiness": row.get("packet_readiness"),
                "download_url": row.get("download_url"),
                "path": "",
                "source_gis_modified": False,
            })
        for row in self.portfolio_file_targets(20):
            rows.append(row)
        return rows[: max(1, min(int(limit or 25), 500))]

    def portfolio_file_targets(self, limit: int = 20) -> list[dict]:
        roots = [
            ("portfolio_handoff_page", self.output_root / "georeview_studio_portfolio_handoff_pages", "*.html", "/api/portfolio-handoff-page/pages/{id}/download"),
            ("portfolio_evidence_gallery", self.output_root / "georeview_studio_portfolio_evidence_galleries", "*.html", "/api/portfolio-evidence-gallery/galleries/{id}/download"),
            ("portfolio_narrative", self.output_root / "georeview_studio_portfolio_narratives", "*.md", "/api/portfolio-narrative-export/narratives/{id}/download"),
            ("release_readiness", self.output_root / "georeview_studio_release_readiness", "*.md", ""),
        ]
        targets = []
        for kind, folder, pattern, url_template in roots:
            if not folder.exists():
                continue
            for path in sorted(folder.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)[:5]:
                download_url = url_template.replace("{id}", path.stem) if url_template else ""
                targets.append({
                    "kind": kind,
                    "artifact_id": path.stem,
                    "label": kind.replace("_", " ").title(),
                    "readiness": "available",
                    "download_url": download_url,
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "source_gis_modified": False,
                })
                if len(targets) >= limit:
                    return targets
        return targets

    def safe_indexes(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.reviewer_audit_index.list_indexes(limit), [])
        return rows if isinstance(rows, list) else []

    def safe_packets(self, limit: int) -> list[dict]:
        rows = safe_call(lambda: self.reproducibility_audit_packet.list_packets(limit), [])
        return rows if isinstance(rows, list) else []

    def primary_actions(self, targets: list[dict]) -> list[dict]:
        preferred = []
        for kind in ["reviewer_audit_index", "reproducibility_audit_packet", "portfolio_handoff_page", "portfolio_evidence_gallery", "portfolio_narrative", "release_readiness"]:
            match = next((row for row in targets if row.get("kind") == kind), None)
            if match:
                preferred.append(match)
        return preferred[:6]

    def is_ready(self, targets: list[dict], reviewer_status: object, packet_status: object) -> bool:
        has_index = any(row.get("kind") == "reviewer_audit_index" for row in targets)
        has_packet = any(row.get("kind") == "reproducibility_audit_packet" for row in targets)
        has_portfolio = any(row.get("kind") in {"portfolio_handoff_page", "portfolio_evidence_gallery", "portfolio_narrative", "release_readiness"} for row in targets)
        ready_index_count = int(reviewer_status.get("ready_index_count") or 0) if isinstance(reviewer_status, dict) else 0
        ready_packet_count = int(packet_status.get("ready_packet_count") or 0) if isinstance(packet_status, dict) else 0
        return has_index and has_packet and has_portfolio and ready_index_count >= 1 and ready_packet_count >= 1

    def launcher_markdown(self, launcher: dict) -> str:
        lines = [
            "# Portfolio Export Launcher",
            "",
            f"- Launcher id: `{launcher.get('launcher_id')}`",
            f"- Created at: `{launcher.get('created_at')}`",
            f"- App version: `{launcher.get('app_version')}`",
            f"- Readiness: `{launcher.get('launcher_readiness')}`",
            f"- Launch targets: `{launcher.get('launch_target_count')}`",
            f"- API endpoints checked: `{launcher.get('api_contract', {}).get('checked_endpoints')}`",
            f"- Release readiness: `{launcher.get('validation_summary', {}).get('release_readiness_level')}`",
            "",
            "## Purpose",
            "",
            "This start-here artifact gives a reviewer one compact entrypoint into the local GeoReview Studio evidence stack.",
            "",
            "It links the latest reviewer audit index, reproducibility audit packet and portfolio artifacts that explain how the GIS review outputs were generated and validated.",
            "",
            "## Primary Actions",
            "",
        ]
        for row in launcher.get("primary_actions", []):
            destination = row.get("download_url") or row.get("path") or ""
            lines.append(f"- `{row.get('kind')}` - `{row.get('artifact_id')}` - {destination}")
        lines.extend(["", "## All Launch Targets", ""])
        for row in launcher.get("launch_targets", []):
            destination = row.get("download_url") or row.get("path") or ""
            lines.append(f"- `{row.get('kind')}` - `{row.get('artifact_id')}` - `{row.get('readiness')}` - {destination}")
        lines.extend([
            "",
            "## Claim Boundaries",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- This is an infrastructure risk indicator and field-review prioritization project.",
            "- Missing OSM tags remain data-quality evidence unless an explicit mapped value is present.",
            "- The launcher is reviewer navigation evidence, not a crash prediction artifact and not a statement about real-world outcomes.",
            "",
            "## Recommended Demo Flow",
            "",
            "1. Open the reviewer audit index to show packet and evidence lineage.",
            "2. Open one reproducibility audit packet and inspect the selected execution diff evidence.",
            "3. Open the portfolio handoff page or evidence gallery for the concise story.",
            "4. Check validation and API contract summaries before discussing any analytics result.",
            "5. Keep infrastructure risk indicators separate from data-quality flags in the explanation.",
            "",
        ])
        return "\n".join(lines)

    def launcher_html(self, launcher: dict) -> str:
        actions = "\n".join(self.html_target(row) for row in launcher.get("primary_actions", []))
        all_targets = "\n".join(self.html_target(row) for row in launcher.get("launch_targets", []))
        return f"""<!doctype html>
<html lang=\"en\">
<head><meta charset=\"utf-8\"><title>Portfolio Export Launcher</title></head>
<body>
<h1>Portfolio Export Launcher</h1>
<p>Launcher: <code>{launcher.get('launcher_id')}</code></p>
<p>Readiness: <code>{launcher.get('launcher_readiness')}</code></p>
<h2>Primary Actions</h2>
<ul>{actions}</ul>
<h2>All Launch Targets</h2>
<ul>{all_targets}</ul>
<h2>Claim Boundaries</h2>
<p>{self.review_wording}</p>
<p>This is reviewer navigation evidence for infrastructure indicators and field-review prioritization, not crash prediction.</p>
</body>
</html>"""

    @staticmethod
    def html_target(row: dict) -> str:
        destination = row.get("download_url") or row.get("path") or ""
        if str(destination).startswith("/"):
            link = f"<a href=\"{destination}\">open</a>"
        elif destination:
            link = f"<code>{destination}</code>"
        else:
            link = ""
        return f"<li><code>{row.get('kind')}</code> - <code>{row.get('artifact_id')}</code> {link}</li>"

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["infrastructure risk indicators", "data-quality flags", "field-review prioritization", "reviewer navigation"],
            "not_allowed": ["crash prediction", "proof of real-world absence from missing tags", "absolute safety claims"],
            "missing_tag_rule": "Missing OSM tags add data-quality flags, not risk points by default.",
        }

    def launcher_path(self, launcher_id: str, suffix: str) -> Path:
        return self.launcher_dir / f"{safe_token(launcher_id, 'missing_launcher')}{suffix}"

    def safe_launcher_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.launcher_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
