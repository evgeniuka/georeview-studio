from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from source_onboarding import SUPPORTED_EXTENSIONS


SOURCE_IMPORT_GUARDRAILS_VERSION = "source_import_guardrails_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
APPROVAL_PHRASE = "approve metadata-only import"
DEFAULT_TEMPLATE_ID = "safe_access"
MAX_REVIEW_SIZE_MB = 2048.0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "source_import") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:120] or fallback


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


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


class SourceImportGuardrails:
    def __init__(
        self,
        project_dir: Path,
        output_root: Path,
        maps_root: Path,
        onboarding: object,
        local_intake: object,
        default_dataset_id: str,
        review_wording: str,
    ) -> None:
        self.project_dir = project_dir
        self.output_root = output_root.resolve()
        self.maps_root = maps_root.resolve()
        self.onboarding = onboarding
        self.local_intake = local_intake
        self.default_dataset_id = default_dataset_id
        self.review_wording = review_wording
        self.requests_dir = self.output_root / "georeview_studio_source_import_guardrails"

    def status(self) -> dict:
        sources = self.safe_sources()
        requests = self.list_requests(1000)
        approved_count = 0
        for row in requests:
            if row.get("latest_decision_state") == "approved_for_metadata_only_import":
                approved_count += 1
        reviewable = [
            source for source in sources
            if (source.get("readiness", {}) or {}).get("supported_templates")
        ]
        return {
            "ok": True,
            "source_import_guardrails_version": SOURCE_IMPORT_GUARDRAILS_VERSION,
            "mode": "reviewed_metadata_only_source_import",
            "maps_root": str(self.maps_root),
            "output_dir": str(self.requests_dir),
            "source_count": len(sources),
            "reviewable_source_count": len(reviewable),
            "request_count": len(requests),
            "approved_request_count": approved_count,
            "guardrail_count": len(self.guardrail_catalog()),
            "approval_phrase": APPROVAL_PHRASE,
            "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
            "readiness_level": "ready_for_reviewed_local_import" if len(sources) > 0 else "no_local_sources_detected",
            "claim_boundaries": self.claim_boundaries(),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def guardrail_catalog(self) -> list[dict]:
        return [
            {"guardrail_id": "path_inside_maps_root", "severity": "hard", "purpose": "Only local sources under the configured maps folder can be reviewed."},
            {"guardrail_id": "analysis_output_excluded", "severity": "hard", "purpose": "Generated analysis_output artifacts cannot be re-imported as source data."},
            {"guardrail_id": "supported_format", "severity": "hard", "purpose": "The source must be one of the locally profiled GIS/OSM formats."},
            {"guardrail_id": "metadata_profile_available", "severity": "hard", "purpose": "The source needs at least lightweight metadata evidence before any workflow handoff."},
            {"guardrail_id": "template_compatibility_reviewed", "severity": "hard", "purpose": "The selected template must be supported or explicitly limited to generic inventory."},
            {"guardrail_id": "size_review", "severity": "warning", "purpose": "Large files are allowed only with explicit review because runtime and storage cost may be high."},
            {"guardrail_id": "manual_approval_required", "severity": "hard", "purpose": "A reviewer must approve the metadata-only import before handoff."},
            {"guardrail_id": "source_read_only_policy", "severity": "hard", "purpose": "The guardrail workflow never edits, moves, renames or overwrites source GIS files."},
            {"guardrail_id": "claim_boundary_required", "severity": "hard", "purpose": "Every request keeps infrastructure indicators separate from absolute safety claims."},
        ]

    def preview(self, body: dict | None = None) -> dict:
        body = body or {}
        template_id = str(body.get("template_id") or DEFAULT_TEMPLATE_ID)
        intake_body = self.intake_body(body)
        if not intake_body:
            return {
                "ok": False,
                "error": "source_import_input_missing",
                "detail": "dataset_id or path is required",
                "source_gis_modified": False,
                "mutates_config": False,
            }
        intake_preview = self.local_intake.preview(intake_body)
        if intake_preview.get("error"):
            return {
                "ok": False,
                "error": intake_preview.get("error"),
                "detail": intake_preview.get("detail") or intake_preview.get("path") or "",
                "intake_preview": intake_preview,
                "source_gis_modified": False,
                "mutates_config": False,
            }
        source = self.source_from_preview(intake_preview)
        guardrails = self.evaluate_guardrails(intake_preview, source, template_id)
        counts = self.guardrail_counts(guardrails)
        hard_failed_count = sum(1 for gate in guardrails if gate.get("severity") == "hard" and gate.get("status") == "failed")
        warnings = [gate for gate in guardrails if gate.get("status") == "warning"]
        return {
            "ok": True,
            "source_import_guardrails_version": SOURCE_IMPORT_GUARDRAILS_VERSION,
            "template_id": template_id,
            "dataset_id": source.get("dataset_id") or intake_body.get("dataset_id"),
            "input_type": intake_preview.get("input_type"),
            "source": source,
            "intake_preview": intake_preview,
            "guardrails": guardrails,
            "summary": {
                "guardrail_count": len(guardrails),
                "passed_guardrails": counts.get("passed", 0),
                "warning_guardrails": counts.get("warning", 0),
                "failed_guardrails": counts.get("failed", 0),
                "hard_failed_count": hard_failed_count,
            },
            "import_readiness": "ready_for_manual_review" if hard_failed_count == 0 else "blocked_by_guardrails",
            "approval_required": True,
            "approval_phrase": APPROVAL_PHRASE,
            "review_wording": self.review_wording,
            "claim_boundaries": self.claim_boundaries(),
            "source_gis_modified": False,
            "mutates_config": False,
            "warning_count": len(warnings),
        }

    def create_request(self, body: dict | None = None) -> dict:
        body = body or {}
        preview = self.preview(body)
        if preview.get("error"):
            return preview
        if preview.get("import_readiness") != "ready_for_manual_review":
            return {
                "ok": False,
                "error": "source_import_request_not_ready",
                "preview": preview,
                "source_gis_modified": False,
                "mutates_config": False,
            }
        stamp = utc_now()
        source = preview.get("source", {})
        seed = source.get("dataset_id") or source.get("file_name") or "source"
        request_id = f"source_import_review_{safe_token(seed)}_{safe_token(stamp)}"
        review_dir = self.requests_dir / request_id
        json_path = review_dir / f"{request_id}.json"
        md_path = review_dir / f"{request_id}.md"
        latest_path = self.requests_dir / "latest_source_import_review.json"
        request = {
            "ok": True,
            "source_import_guardrails_version": SOURCE_IMPORT_GUARDRAILS_VERSION,
            "request_id": request_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "notes": str(body.get("notes") or "Reviewed local source import request."),
            "approval_state": "awaiting_manual_approval",
            "review_readiness": "ready_for_manual_approval",
            "manual_approval_required": True,
            "approval_phrase": APPROVAL_PHRASE,
            "preview": preview,
            "source": source,
            "template_id": preview.get("template_id"),
            "guardrails": preview.get("guardrails", []),
            "summary": preview.get("summary", {}),
            "approved_operations": [
                "metadata profile review",
                "profile compatibility review",
                "metadata-only handoff planning",
            ],
            "forbidden_operations": [
                "editing source GIS files",
                "moving or renaming source GIS files",
                "overwriting source GIS files",
                "browser upload without a separate storage design",
                "making absolute site-safety claims",
            ],
            "review_wording": self.review_wording,
            "claim_boundaries": self.claim_boundaries(),
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)},
        }
        write_json(json_path, request)
        write_json(latest_path, request)
        md_path.write_text(self.request_markdown(request), encoding="utf-8", newline="\n")
        response = dict(request)
        response["decisions"] = []
        return {"ok": True, "request": response, "source_gis_modified": False, "mutates_config": False}

    def list_requests(self, limit: int = 50) -> list[dict]:
        rows: list[dict] = []
        if not self.requests_dir.exists():
            return rows
        paths = sorted(self.requests_dir.glob("source_import_review_*/source_import_review_*.json"), reverse=True)
        for path in paths:
            payload = read_json(path)
            if not payload:
                continue
            decisions = self.decisions_for(payload.get("request_id") or path.parent.name)
            latest = decisions[0] if decisions else {}
            rows.append({
                "request_id": payload.get("request_id"),
                "created_at": payload.get("created_at"),
                "dataset_id": payload.get("source", {}).get("dataset_id"),
                "file_name": payload.get("source", {}).get("file_name"),
                "template_id": payload.get("template_id"),
                "review_readiness": payload.get("review_readiness"),
                "approval_state": payload.get("approval_state"),
                "latest_decision_state": latest.get("decision_state"),
                "hard_failed_count": payload.get("summary", {}).get("hard_failed_count"),
                "json_file": str(path),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, request_id: str) -> dict:
        path = self.request_path(request_id)
        payload = read_json(path)
        if not payload:
            return {"ok": False, "error": "source_import_request_not_found", "request_id": request_id, "source_gis_modified": False}
        result = dict(payload)
        result["decisions"] = self.decisions_for(payload.get("request_id") or request_id)
        return result

    def decide(self, request_id: str, body: dict | None = None) -> dict:
        body = body or {}
        request = self.detail(request_id)
        if request.get("error"):
            return request
        decision = str(body.get("decision") or "").strip().lower()
        if decision not in {"approve", "reject"}:
            return self.invalid_decision("decision must be approve or reject")
        if decision == "approve":
            required = {
                "approval_phrase": str(body.get("approval_phrase") or "").strip() == APPROVAL_PHRASE,
                "source_files_read_only_ack": bool(body.get("source_files_read_only_ack")),
                "generated_outputs_only_ack": bool(body.get("generated_outputs_only_ack")),
                "no_browser_upload_ack": bool(body.get("no_browser_upload_ack")),
                "claim_boundary_ack": bool(body.get("claim_boundary_ack")),
            }
            missing = [key for key, ok in required.items() if not ok]
            if missing:
                return self.invalid_decision(f"approval is missing required acknowledgements: {', '.join(missing)}")
        stamp = utc_now()
        decision_id = f"source_import_decision_{safe_token(request_id)}_{safe_token(stamp)}"
        state = "approved_for_metadata_only_import" if decision == "approve" else "rejected"
        decision_payload = {
            "ok": True,
            "source_import_guardrails_version": SOURCE_IMPORT_GUARDRAILS_VERSION,
            "decision_id": decision_id,
            "request_id": request.get("request_id"),
            "created_at": stamp,
            "reviewer": str(body.get("reviewer") or "local_operator"),
            "decision": decision,
            "decision_state": state,
            "notes": str(body.get("notes") or ""),
            "can_create_metadata_handoff": decision == "approve" and request.get("summary", {}).get("hard_failed_count", 0) == 0,
            "can_run_domain_analytics": decision == "approve" and request.get("source", {}).get("readiness_level") == "ready_for_safe_access_selected_pilot",
            "approved_operations": request.get("approved_operations", []),
            "forbidden_operations": request.get("forbidden_operations", []),
            "source_gis_modified": False,
            "mutates_config": False,
        }
        decision_dir = self.request_dir(request_id) / "decisions"
        decision_path = decision_dir / f"{decision_id}.json"
        latest_path = self.request_dir(request_id) / "latest_source_import_decision.json"
        write_json(decision_path, decision_payload)
        write_json(latest_path, decision_payload)
        return {"ok": True, "decision": decision_payload, "request": request, "source_gis_modified": False, "mutates_config": False}

    def output_file(self, request_id: str, output_id: str = "source_import_review") -> dict:
        request = self.detail(request_id)
        if request.get("error"):
            return request
        files = request.get("files", {})
        path = Path(files.get("markdown") or "")
        if output_id not in {"source_import_review", "markdown"} or not path.exists():
            return {"ok": False, "error": "source_import_review_output_not_found", "request_id": request_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def evaluate_guardrails(self, intake_preview: dict, source: dict, template_id: str) -> list[dict]:
        source_path = self.source_path(source)
        readiness_level = source.get("readiness_level") or (intake_preview.get("readiness") or {}).get("level") or ""
        supported_templates = set(source.get("supported_templates") or (intake_preview.get("readiness") or {}).get("supported_templates") or [])
        extension = source.get("extension") or ""
        layer_count = int(source.get("layer_count") or len(intake_preview.get("layers") or []))
        size_mb = float(source.get("size_mb") or 0.0)
        guardrails = [
            self.gate(
                "path_inside_maps_root",
                "hard",
                "passed" if source_path and is_relative_to(source_path, self.maps_root) else "failed",
                {"path": str(source_path) if source_path else "", "maps_root": str(self.maps_root)},
                "Keep reviewed sources under the configured maps folder.",
            ),
            self.gate(
                "analysis_output_excluded",
                "hard",
                "passed" if source_path and not is_relative_to(source_path, self.output_root) else "failed",
                {"path": str(source_path) if source_path else "", "output_root": str(self.output_root)},
                "Do not import generated analysis_output artifacts as source data.",
            ),
            self.gate(
                "supported_format",
                "hard",
                "passed" if extension in SUPPORTED_EXTENSIONS else "failed",
                {"extension": extension, "supported_extensions": sorted(SUPPORTED_EXTENSIONS)},
                "Use Shapefile ZIP, OSM PBF, GeoPackage, Shapefile or GeoJSON sources.",
            ),
            self.gate(
                "metadata_profile_available",
                "hard",
                "passed" if layer_count > 0 or extension in {".osm.pbf", ".pbf"} else "failed",
                {"layer_count": layer_count, "readiness_level": readiness_level},
                "Run source onboarding or add a parser before workflow handoff.",
            ),
            self.gate(
                "template_compatibility_reviewed",
                "hard",
                "passed" if template_id in supported_templates or (template_id == "generic_layer_inventory" and supported_templates) else "failed",
                {"template_id": template_id, "supported_templates": sorted(supported_templates)},
                "Choose a compatible template or create a mapper contract first.",
            ),
            self.gate(
                "size_review",
                "warning",
                "passed" if size_mb <= MAX_REVIEW_SIZE_MB else "warning",
                {"size_mb": size_mb, "max_review_size_mb": MAX_REVIEW_SIZE_MB},
                "Large sources should use a PostGIS/osm2pgsql plan before execution.",
            ),
            self.gate(
                "manual_approval_required",
                "hard",
                "passed",
                {"approval_phrase": APPROVAL_PHRASE, "approval_state": "awaiting_manual_approval"},
                "Record an explicit approval decision before metadata handoff.",
            ),
            self.gate(
                "source_read_only_policy",
                "hard",
                "passed" if source.get("source_gis_modified") is False and intake_preview.get("source_gis_modified") is False else "failed",
                {"source_gis_modified": source.get("source_gis_modified"), "preview_source_gis_modified": intake_preview.get("source_gis_modified")},
                "Never edit, move, rename or overwrite source GIS files.",
            ),
            self.gate(
                "claim_boundary_required",
                "hard",
                "passed",
                {"review_wording": self.review_wording},
                "Use infrastructure review wording only.",
            ),
        ]
        blockers = (intake_preview.get("readiness") or {}).get("blockers") or source.get("blockers") or []
        if blockers:
            guardrails.append(self.gate(
                "source_readiness_blockers_logged",
                "warning",
                "warning",
                {"blockers": blockers},
                "Resolve blockers before claiming the source can run the selected domain profile.",
            ))
        return guardrails

    @staticmethod
    def gate(guardrail_id: str, severity: str, status: str, evidence: dict, recommendation: str) -> dict:
        return {
            "guardrail_id": guardrail_id,
            "severity": severity,
            "status": status,
            "passed": status == "passed",
            "evidence": evidence,
            "recommendation": recommendation,
        }

    @staticmethod
    def guardrail_counts(guardrails: list[dict]) -> dict:
        counts = {"passed": 0, "warning": 0, "failed": 0}
        for guardrail in guardrails:
            status = str(guardrail.get("status") or "failed")
            counts[status] = counts.get(status, 0) + 1
        return counts

    @staticmethod
    def source_from_preview(preview: dict) -> dict:
        source = dict(preview.get("source") or {})
        readiness = preview.get("readiness") or {}
        if readiness and "readiness_level" not in source:
            source["readiness_level"] = readiness.get("level")
            source["supported_templates"] = readiness.get("supported_templates", [])
            source["blockers"] = readiness.get("blockers", [])
        source.setdefault("source_gis_modified", False)
        return source

    @staticmethod
    def intake_body(body: dict) -> dict:
        dataset_id = str(body.get("dataset_id") or "").strip()
        path = str(body.get("path") or "").strip()
        if dataset_id:
            return {"dataset_id": dataset_id}
        if path:
            return {"path": path}
        return {}

    @staticmethod
    def source_path(source: dict) -> Path | None:
        try:
            value = source.get("path") or ""
            if not value:
                return None
            return Path(value).resolve(strict=False)
        except OSError:
            return None

    def request_dir(self, request_id: str) -> Path:
        return self.requests_dir / safe_token(request_id, "missing")

    def request_path(self, request_id: str) -> Path:
        token = safe_token(request_id, "missing")
        return self.requests_dir / token / f"{token}.json"

    def decisions_for(self, request_id: str) -> list[dict]:
        decision_dir = self.request_dir(request_id) / "decisions"
        if not decision_dir.exists():
            return []
        decisions = []
        for path in sorted(decision_dir.glob("source_import_decision_*.json"), reverse=True):
            payload = read_json(path)
            if payload:
                decisions.append(payload)
        return decisions

    def safe_sources(self) -> list[dict]:
        try:
            sources = self.onboarding.sources()
            return sources if isinstance(sources, list) else []
        except Exception:
            return []

    @staticmethod
    def invalid_decision(detail: str) -> dict:
        return {
            "ok": False,
            "error": "source_import_decision_invalid",
            "detail": detail,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def claim_boundaries(self) -> list[str]:
        return [
            "Source import guardrails create review evidence only.",
            "They do not upload, copy, edit, move, rename or overwrite source GIS files.",
            "Missing OSM tags are data-quality gaps, not proof that infrastructure is absent.",
            self.review_wording,
        ]

    def request_markdown(self, request: dict) -> str:
        source = request.get("source", {})
        summary = request.get("summary", {})
        lines = [
            "# Source Import Guardrails Review",
            "",
            f"Request: `{request.get('request_id')}`",
            f"Created: `{request.get('created_at')}`",
            f"Approval state: `{request.get('approval_state')}`",
            "",
            "## Source",
            "",
            f"- Dataset: `{source.get('dataset_id')}`",
            f"- File: `{source.get('file_name')}`",
            f"- Path: `{source.get('path')}`",
            f"- Extension: `{source.get('extension')}`",
            f"- Size MB: `{source.get('size_mb')}`",
            f"- Readiness: `{source.get('readiness_level')}`",
            "",
            "## Guardrail Summary",
            "",
            f"- Passed: `{summary.get('passed_guardrails')}`",
            f"- Warnings: `{summary.get('warning_guardrails')}`",
            f"- Failed: `{summary.get('failed_guardrails')}`",
            f"- Hard failed: `{summary.get('hard_failed_count')}`",
            "",
            "## Guardrails",
            "",
        ]
        for guardrail in request.get("guardrails", []):
            lines.append(f"- `{guardrail.get('guardrail_id')}`: `{guardrail.get('status')}` ({guardrail.get('severity')}) - {guardrail.get('recommendation')}")
        lines.extend([
            "",
            "## Manual Approval",
            "",
            f"Required phrase: `{APPROVAL_PHRASE}`",
            "",
            "Approval must acknowledge source read-only handling, generated-output-only writes, no browser upload, and claim-boundary wording.",
            "",
            "## Claim Boundary",
            "",
            f"`{self.review_wording}`",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)
