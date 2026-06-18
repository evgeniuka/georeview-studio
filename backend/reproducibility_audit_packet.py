from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPRODUCIBILITY_AUDIT_PACKET_VERSION = "reproducibility_audit_packet_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "reproducibility_audit_packet", max_len: int = 96) -> str:
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
        return {"error": "reproducibility_audit_packet_probe_failed", "detail": repr(exc)}


class ReproducibilityAuditPacketBuilder:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        app_version: str,
        manifest_reader: Callable[[], dict],
        review_wording: str,
        execution_result_diff: object,
        execution_diff_gallery: object,
        execution_diff_detail: object,
        expected_api_endpoints: int,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root
        self.app_version = app_version
        self.manifest_reader = manifest_reader
        self.review_wording = review_wording
        self.execution_result_diff = execution_result_diff
        self.execution_diff_gallery = execution_diff_gallery
        self.execution_diff_detail = execution_diff_detail
        self.expected_api_endpoints = expected_api_endpoints
        self.packets_dir = output_root / "georeview_studio_reproducibility_audit_packets"

    def status(self) -> dict:
        candidates = self.candidates(limit=500)
        packets = self.list_packets(limit=500)
        ready_packets = [row for row in packets if row.get("packet_readiness") == "ready_for_reviewer"]
        manifest = safe_call(self.manifest_reader, {})
        return {
            "ok": True,
            "reproducibility_audit_packet_version": REPRODUCIBILITY_AUDIT_PACKET_VERSION,
            "app_version": self.app_version,
            "project_manifest_version": manifest.get("version") if isinstance(manifest, dict) else "",
            "mode": "bundle_diff_detail_gallery_and_release_evidence",
            "output_dir": str(self.packets_dir),
            "candidate_count": len(candidates),
            "packet_count": len(packets),
            "ready_packet_count": len(ready_packets),
            "expected_api_endpoints": self.expected_api_endpoints,
            "readiness_level": "ready_for_audit_packet" if candidates else "waiting_for_execution_diff_detail",
            "packet_contents": [
                "packet_manifest.json",
                "packet_summary.md",
                "selected execution diff detail evidence",
                "selected execution result diff evidence",
                "selected execution diff gallery evidence",
                "validation summary",
                "API contract summary",
                "project manifest",
            ],
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def candidates(self, limit: int = 20) -> list[dict]:
        drilldowns = safe_call(lambda: self.execution_diff_detail.list_drilldowns(500), [])
        if not isinstance(drilldowns, list):
            return []
        rows = []
        for item in drilldowns:
            if item.get("drilldown_readiness") != "ready_for_reviewer":
                continue
            rows.append({
                "detail_id": item.get("detail_id"),
                "created_at": item.get("created_at"),
                "diff_id": item.get("diff_id"),
                "baseline_diff_id": item.get("baseline_diff_id"),
                "changed_table_count": item.get("changed_table_count", 0),
                "output_delta_count": item.get("output_delta_count", 0),
                "review_action_count": item.get("review_action_count", 0),
                "packet_readiness_candidate": "ready_for_packet",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def create_packet(self, body: dict | None = None) -> dict:
        body = body or {}
        detail_id = str(body.get("detail_id") or "").strip()
        if not detail_id:
            candidates = self.candidates(1)
            if not candidates:
                return self.error("reproducibility_audit_packet_input_missing", "A ready execution diff detail id is required when no packet candidate exists.")
            detail_id = str(candidates[0].get("detail_id") or "")

        detail = safe_call(lambda: self.execution_diff_detail.detail(detail_id), {})
        if not isinstance(detail, dict) or detail.get("error"):
            return {"ok": False, "error": "execution_diff_detail_not_found", "detail_id": detail_id, "source_gis_modified": False, "mutates_config": False}
        if detail.get("drilldown_readiness") != "ready_for_reviewer":
            return self.error("reproducibility_audit_packet_not_ready", "The selected execution diff detail must be ready_for_reviewer.")

        diff_id = str(detail.get("diff_id") or "")
        diff = safe_call(lambda: self.execution_result_diff.detail(diff_id), {})
        if not isinstance(diff, dict) or diff.get("error"):
            return {"ok": False, "error": "execution_result_diff_not_found", "diff_id": diff_id, "source_gis_modified": False, "mutates_config": False}

        gallery = self.resolve_gallery(str(body.get("gallery_id") or ""), diff_id)
        if gallery.get("error"):
            return gallery

        stamp = utc_now()
        packet_id = f"reproducibility_audit_packet_{safe_token(detail_id, max_len=72)}_{safe_token(stamp.replace(':', '_'), max_len=32)}"
        packet_dir = self.packet_dir(packet_id)
        manifest_path = packet_dir / "packet_manifest.json"
        summary_path = packet_dir / "packet_summary.md"
        latest_path = self.packets_dir / "latest_reproducibility_audit_packet.json"

        copied_files = []
        copied_files.extend(self.copy_evidence_files(packet_dir, "execution_diff_detail", detail))
        copied_files.extend(self.copy_evidence_files(packet_dir, "execution_result_diff", diff))
        copied_files.extend(self.copy_evidence_files(packet_dir, "execution_diff_gallery", gallery))
        copied_files.extend(self.copy_project_summaries(packet_dir))

        packet_readiness = self.packet_readiness(detail, diff, gallery, copied_files)
        packet = {
            "ok": True,
            "reproducibility_audit_packet_version": REPRODUCIBILITY_AUDIT_PACKET_VERSION,
            "packet_id": packet_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewer-facing reproducibility audit packet."),
            "app_version": self.app_version,
            "detail_id": detail.get("detail_id"),
            "diff_id": diff.get("diff_id"),
            "baseline_diff_id": detail.get("baseline_diff_id"),
            "gallery_id": gallery.get("gallery_id"),
            "packet_readiness": packet_readiness,
            "summary": self.packet_summary(detail, diff, gallery, copied_files),
            "copied_files": copied_files,
            "claim_boundaries": self.claim_boundaries(),
            "approved_review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {
                "directory": str(packet_dir),
                "json": str(manifest_path),
                "markdown": str(summary_path),
                "latest": str(latest_path),
            },
        }
        write_json(manifest_path, packet)
        write_json(latest_path, packet)
        summary_path.write_text(self.packet_markdown(packet), encoding="utf-8", newline="\n")
        return {"ok": True, "packet": packet, "source_gis_modified": False, "mutates_config": False}

    def list_packets(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.packets_dir.exists():
            return rows
        manifests = sorted(
            self.packets_dir.glob("reproducibility_audit_packet_*/packet_manifest.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in manifests:
            data = read_json(path)
            if data.get("reproducibility_audit_packet_version") != REPRODUCIBILITY_AUDIT_PACKET_VERSION:
                continue
            rows.append({
                "packet_id": data.get("packet_id"),
                "created_at": data.get("created_at"),
                "packet_readiness": data.get("packet_readiness"),
                "detail_id": data.get("detail_id"),
                "diff_id": data.get("diff_id"),
                "gallery_id": data.get("gallery_id"),
                "copied_file_count": len(data.get("copied_files", [])) if isinstance(data.get("copied_files"), list) else 0,
                "download_url": f"/api/reproducibility-audit-packet/packets/{data.get('packet_id')}/download",
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= max(1, min(int(limit or 20), 500)):
                break
        return rows

    def detail(self, packet_id: str) -> dict:
        manifest_path = self.packet_dir(packet_id) / "packet_manifest.json"
        if not manifest_path.exists() or not self.safe_packet_path(manifest_path):
            return {"ok": False, "error": "reproducibility_audit_packet_not_found", "packet_id": packet_id, "source_gis_modified": False}
        payload = read_json(manifest_path)
        if not payload:
            return {"ok": False, "error": "reproducibility_audit_packet_not_found", "packet_id": packet_id, "source_gis_modified": False}
        return payload

    def output_file(self, packet_id: str, output_id: str = "packet_summary") -> dict:
        packet = self.detail(packet_id)
        if packet.get("error"):
            return packet
        if output_id not in {"packet_summary", "markdown"}:
            return {"ok": False, "error": "reproducibility_audit_packet_output_not_found", "packet_id": packet_id, "output_id": output_id}
        path = Path(str(packet.get("files", {}).get("markdown") or ""))
        if not path.exists() or not self.safe_packet_path(path):
            return {"ok": False, "error": "reproducibility_audit_packet_output_not_found", "packet_id": packet_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def resolve_gallery(self, gallery_id: str, diff_id: str) -> dict:
        if gallery_id:
            gallery = safe_call(lambda: self.execution_diff_gallery.detail(gallery_id), {})
            if isinstance(gallery, dict) and not gallery.get("error"):
                return gallery
            return {"ok": False, "error": "execution_diff_gallery_not_found", "gallery_id": gallery_id, "source_gis_modified": False, "mutates_config": False}
        galleries = safe_call(lambda: self.execution_diff_gallery.list_galleries(50), [])
        if isinstance(galleries, list):
            for row in galleries:
                detail = safe_call(lambda row=row: self.execution_diff_gallery.detail(str(row.get("gallery_id") or "")), {})
                if not isinstance(detail, dict) or detail.get("error"):
                    continue
                items = detail.get("items", []) if isinstance(detail.get("items"), list) else []
                if any(item.get("diff_id") == diff_id for item in items):
                    return detail
            if galleries:
                first = galleries[0]
                detail = safe_call(lambda: self.execution_diff_gallery.detail(str(first.get("gallery_id") or "")), {})
                if isinstance(detail, dict) and not detail.get("error"):
                    return detail
        return self.error("reproducibility_audit_packet_not_ready", "A ready execution diff gallery is required for the audit packet.")

    def copy_evidence_files(self, packet_dir: Path, label: str, artifact: dict) -> list[dict]:
        copied = []
        files = artifact.get("files", {}) if isinstance(artifact.get("files"), dict) else {}
        for source_key, suffix in [("json", ".json"), ("markdown", ".md")]:
            source = Path(str(files.get(source_key) or ""))
            if not source.exists() or source.stat().st_size > 5_000_000:
                continue
            target = packet_dir / f"selected_{label}{suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append({
                "file_id": f"selected_{label}_{source_key}",
                "source_path": str(source),
                "packet_path": str(target),
                "size_bytes": target.stat().st_size,
            })
        return copied

    def copy_project_summaries(self, packet_dir: Path) -> list[dict]:
        copied = []
        for file_name in ["validation_summary.json", "api_contract_summary.json", "project_manifest.json"]:
            source = self.project_dir / file_name
            if not source.exists() or source.stat().st_size > 5_000_000:
                continue
            target = packet_dir / file_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append({
                "file_id": file_name.replace(".", "_"),
                "source_path": str(source),
                "packet_path": str(target),
                "size_bytes": target.stat().st_size,
            })
        return copied

    @staticmethod
    def packet_readiness(detail: dict, diff: dict, gallery: dict, copied_files: list[dict]) -> str:
        has_summary_inputs = len([row for row in copied_files if row.get("file_id") in {"validation_summary_json", "api_contract_summary_json", "project_manifest_json"}]) >= 3
        if (
            detail.get("drilldown_readiness") == "ready_for_reviewer"
            and diff.get("diff_readiness") == "ready_for_reviewer"
            and gallery.get("gallery_readiness") == "ready_for_reviewer"
            and has_summary_inputs
        ):
            return "ready_for_reviewer"
        return "needs_evidence_review"

    @staticmethod
    def packet_summary(detail: dict, diff: dict, gallery: dict, copied_files: list[dict]) -> dict:
        drilldown = detail.get("drilldown", {}) if isinstance(detail.get("drilldown"), dict) else {}
        return {
            "diff_classification": diff.get("diff_classification"),
            "comparison_scope": diff.get("comparison_scope"),
            "changed_table_count": drilldown.get("changed_table_count"),
            "output_delta_count": drilldown.get("output_delta_count"),
            "review_action_count": len(drilldown.get("review_actions", [])) if isinstance(drilldown.get("review_actions"), list) else 0,
            "gallery_item_count": gallery.get("item_count"),
            "copied_file_count": len(copied_files),
        }

    def packet_markdown(self, packet: dict) -> str:
        summary = packet.get("summary", {}) if isinstance(packet.get("summary"), dict) else {}
        copied = packet.get("copied_files", []) if isinstance(packet.get("copied_files"), list) else []
        lines = [
            "# Reproducibility Audit Packet",
            "",
            f"- Packet id: `{packet.get('packet_id')}`",
            f"- Created at: `{packet.get('created_at')}`",
            f"- App version: `{packet.get('app_version')}`",
            f"- Readiness: `{packet.get('packet_readiness')}`",
            f"- Detail id: `{packet.get('detail_id')}`",
            f"- Diff id: `{packet.get('diff_id')}`",
            f"- Baseline diff id: `{packet.get('baseline_diff_id')}`",
            f"- Gallery id: `{packet.get('gallery_id')}`",
            f"- Source GIS modified: `{packet.get('source_gis_modified')}`",
            f"- Mutates config: `{packet.get('mutates_config')}`",
            "",
            "## Purpose",
            "",
            "This packet bundles the small reviewer-facing evidence needed to reproduce and inspect one generated execution diff. It is intended for portfolio review, engineering review and local field-review prioritization workflows.",
            "",
            "It does not claim real-world safety outcomes and it is not a crash prediction artifact.",
            "",
            "## Evidence Summary",
            "",
            f"- Diff classification: `{summary.get('diff_classification')}`",
            f"- Comparison scope: `{summary.get('comparison_scope')}`",
            f"- Changed table count: `{summary.get('changed_table_count')}`",
            f"- Output delta count: `{summary.get('output_delta_count')}`",
            f"- Review action count: `{summary.get('review_action_count')}`",
            f"- Gallery item count: `{summary.get('gallery_item_count')}`",
            f"- Copied file count: `{summary.get('copied_file_count')}`",
            "",
            "## Included Files",
            "",
        ]
        for row in copied:
            lines.append(f"- `{row.get('file_id')}` - `{row.get('packet_path')}` ({row.get('size_bytes')} bytes)")
        lines.extend([
            "",
            "## Claim Boundaries",
            "",
            f"- Approved review wording: {self.review_wording}",
            "- Missing OSM tags remain data-quality evidence unless an explicit mapped value is present.",
            "- The packet documents infrastructure indicators, generated outputs, validation summaries and API contract evidence.",
            "- It should support reviewer inspection and local demo reproducibility, not automated site judgement.",
            "",
            "## Recommended Review Steps",
            "",
            "1. Open the selected execution diff detail Markdown and inspect table/output/quality deltas.",
            "2. Check the execution result diff Markdown for package lineage and source handoff context.",
            "3. Use the gallery Markdown to understand whether the diff is a representative baseline or a review-priority item.",
            "4. Confirm validation and API contract summaries match the app version being demonstrated.",
            "5. Keep infrastructure risk indicators separate from data-quality flags in any shared narrative.",
            "",
        ])
        return "\n".join(lines)

    def claim_boundaries(self) -> dict:
        return {
            "allowed": ["infrastructure risk indicators", "data-quality flags", "field-review prioritization", "reproducibility evidence"],
            "not_allowed": ["crash prediction", "proof of real-world absence from missing tags", "absolute safety claims"],
            "missing_tag_rule": "Missing OSM tags add data-quality flags, not risk points by default.",
        }

    def packet_dir(self, packet_id: str) -> Path:
        return self.packets_dir / safe_token(packet_id, "missing_packet", 180)

    def safe_packet_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            return str(resolved).startswith(str(self.packets_dir.resolve()))
        except OSError:
            return False

    @staticmethod
    def error(code: str, message: str) -> dict:
        return {"ok": False, "error": code, "message": message, "source_gis_modified": False, "mutates_config": False}
