from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REVIEWER_AUDIT_INDEX_VERSION = "reviewer_audit_index_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "reviewer_audit_index", max_len: int = 120) -> str:
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
        return {"error": "reviewer_audit_index_probe_failed", "detail": repr(exc)}


class ReviewerAuditIndexBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        reproducibility_audit_packet: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.reproducibility_audit_packet = reproducibility_audit_packet
        self.expected_api_endpoints = expected_api_endpoints
        self.index_dir = output_root / "georeview_studio_reviewer_audit_indexes"

    def status(self) -> dict:
        packets = self.packet_rows(500)
        indexes = self.list_indexes(500)
        ready_indexes = [row for row in indexes if row.get("index_readiness") == "ready_for_reviewer"]
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "reviewer_audit_index_version": REVIEWER_AUDIT_INDEX_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "index_reproducibility_packets_and_portfolio_handoffs",
            "output_dir": str(self.index_dir),
            "packet_count": len(packets),
            "ready_packet_count": len([row for row in packets if row.get("packet_readiness") == "ready_for_reviewer"]),
            "portfolio_link_count": len(self.portfolio_links()),
            "index_count": len(indexes),
            "ready_index_count": len(ready_indexes),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_reviewer_index" if packets else "waiting_for_audit_packets",
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def create_index(self, body: dict | None = None) -> dict:
        body = body or {}
        packets = self.packet_rows(int(body.get("packet_limit") or 25))
        if not packets:
            return self.error("reviewer_audit_index_input_missing", "At least one reproducibility audit packet is required.")
        ready_packets = [row for row in packets if row.get("packet_readiness") == "ready_for_reviewer"]
        if not ready_packets:
            return self.error("reviewer_audit_index_not_ready", "At least one packet must be ready_for_reviewer.")
        stamp = utc_now()
        index_id = f"reviewer_audit_index_{safe_token(stamp.replace(':', '_'), max_len=36)}"
        json_path = self.index_path(index_id, ".json")
        md_path = self.index_path(index_id, ".md")
        html_path = self.index_path(index_id, ".html")
        latest_path = self.index_dir / "latest_reviewer_audit_index.json"
        validation_summary = read_json(self.project_dir / "validation_summary.json")
        api_contract = read_json(self.project_dir / "api_contract_summary.json")
        portfolio_links = self.portfolio_links()
        index = {
            "ok": True,
            "reviewer_audit_index_version": REVIEWER_AUDIT_INDEX_VERSION,
            "index_id": index_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer-facing index over audit packets and portfolio handoff evidence."),
            "app_version": self.app_version,
            "index_readiness": "ready_for_reviewer",
            "packet_count": len(packets),
            "ready_packet_count": len(ready_packets),
            "portfolio_link_count": len(portfolio_links),
            "packets": packets,
            "portfolio_links": portfolio_links,
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
        write_json(json_path, index)
        write_json(latest_path, index)
        md_path.write_text(self.index_markdown(index), encoding="utf-8", newline="\n")
        html_path.write_text(self.index_html(index), encoding="utf-8", newline="\n")
        return {"ok": True, "index": index, "source_gis_modified": False, "mutates_config": False}

    def list_indexes(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.index_dir.exists():
            return rows
        for path in sorted(self.index_dir.glob("reviewer_audit_index_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            payload = read_json(path)
            if payload.get("reviewer_audit_index_version") != REVIEWER_AUDIT_INDEX_VERSION:
                continue
            rows.append({
                "index_id": payload.get("index_id"),
                "created_at": payload.get("created_at"),
                "index_readiness": payload.get("index_readiness"),
                "packet_count": payload.get("packet_count"),
                "ready_packet_count": payload.get("ready_packet_count"),
                "portfolio_link_count": payload.get("portfolio_link_count"),
                "download_url": f"/api/reviewer-audit-index/indexes/{payload.get('index_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, index_id: str) -> dict:
        path = self.index_path(index_id, ".json")
        if not path.exists() or not self.safe_index_path(path):
            return {"ok": False, "error": "reviewer_audit_index_not_found", "index_id": index_id, "source_gis_modified": False}
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "reviewer_audit_index_not_found", "index_id": index_id, "source_gis_modified": False}
        return payload

    def output_file(self, index_id: str, output_id: str = "reviewer_audit_index") -> dict:
        detail = self.detail(index_id)
        if detail.get("error"):
            return detail
        if output_id not in {"reviewer_audit_index", "markdown"}:
            return {"ok": False, "error": "reviewer_audit_index_output_not_found", "index_id": index_id, "output_id": output_id}
        path = Path(str(detail.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_index_path(path):
            return {"ok": False, "error": "reviewer_audit_index_output_not_found", "index_id": index_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def packet_rows(self, limit: int = 25) -> list[dict]:
        rows = safe_call(lambda: self.reproducibility_audit_packet.list_packets(max(1, min(int(limit or 25), 500))), [])
        return rows if isinstance(rows, list) else []

    def portfolio_links(self, limit: int = 20) -> list[dict]:
        roots = [
            ("portfolio_handoff_page", self.output_root / "georeview_studio_portfolio_handoff_pages", "*.html"),
            ("portfolio_evidence_gallery", self.output_root / "georeview_studio_portfolio_evidence_galleries", "*.html"),
            ("portfolio_narrative", self.output_root / "georeview_studio_portfolio_narratives", "*.md"),
            ("release_readiness", self.output_root / "georeview_studio_release_readiness", "*.md"),
        ]
        links = []
        for kind, folder, pattern in roots:
            if not folder.exists():
                continue
            for path in sorted(folder.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)[:5]:
                links.append({"kind": kind, "name": path.name, "path": str(path), "size_bytes": path.stat().st_size})
                if len(links) >= limit:
                    return links
        return links

    def index_markdown(self, index: dict) -> str:
        lines = [
            "# Reviewer Audit Index",
            "",
            f"- Index id: `{index.get('index_id')}`",
            f"- Created at: `{index.get('created_at')}`",
            f"- App version: `{index.get('app_version')}`",
            f"- Readiness: `{index.get('index_readiness')}`",
            f"- Ready packets: `{index.get('ready_packet_count')}` / `{index.get('packet_count')}`",
            f"- Portfolio links: `{index.get('portfolio_link_count')}`",
            f"- API endpoints checked: `{index.get('api_contract', {}).get('checked_endpoints')}`",
            f"- Release readiness: `{index.get('validation_summary', {}).get('release_readiness_level')}`",
            "",
            "## Purpose",
            "",
            "This index gives a reviewer one place to open reproducibility audit packets, portfolio handoff evidence, validation status and API contract coverage.",
            "",
            "It documents generated evidence for infrastructure risk indicator review. It is not a crash prediction artifact and it does not claim real-world safety outcomes.",
            "",
            "## Audit Packets",
            "",
        ]
        for packet in index.get("packets", []):
            lines.append(f"- `{packet.get('packet_id')}` - `{packet.get('packet_readiness')}` - files `{packet.get('copied_file_count')}` - {packet.get('download_url')}")
        lines.extend(["", "## Portfolio Links", ""])
        for link in index.get("portfolio_links", []):
            lines.append(f"- `{link.get('kind')}` - `{link.get('name')}` - `{link.get('path')}`")
        lines.extend([
            "",
            "## Claim Boundaries",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- Missing OSM tags remain data-quality evidence unless an explicit mapped value is present.",
            "- The index is for reviewer navigation and reproducibility evidence, not automated site judgement.",
            "",
        ])
        return "\n".join(lines)

    def index_html(self, index: dict) -> str:
        packet_items = "\n".join(f"<li><code>{packet.get('packet_id')}</code> - {packet.get('packet_readiness')}</li>" for packet in index.get("packets", []))
        link_items = "\n".join(f"<li><code>{link.get('kind')}</code> - {link.get('name')}</li>" for link in index.get("portfolio_links", []))
        return f"""<!doctype html>
<html lang=\"en\">
<head><meta charset=\"utf-8\"><title>Reviewer Audit Index</title></head>
<body>
<h1>Reviewer Audit Index</h1>
<p>Index: <code>{index.get('index_id')}</code></p>
<p>Readiness: <code>{index.get('index_readiness')}</code></p>
<h2>Audit Packets</h2>
<ul>{packet_items}</ul>
<h2>Portfolio Links</h2>
<ul>{link_items}</ul>
<h2>Claim Boundaries</h2>
<p>{self.review_wording}</p>
<p>This is infrastructure indicator evidence, not a crash prediction artifact.</p>
</body>
</html>"""

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["infrastructure risk indicators", "data-quality flags", "field-review prioritization", "reviewer navigation"],
            "not_allowed": ["crash prediction", "proof of real-world absence from missing tags", "absolute safety claims"],
            "missing_tag_rule": "Missing OSM tags add data-quality flags, not risk points by default.",
        }

    def index_path(self, index_id: str, suffix: str) -> Path:
        return self.index_dir / f"{safe_token(index_id, 'missing_index')}{suffix}"

    def safe_index_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.index_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
