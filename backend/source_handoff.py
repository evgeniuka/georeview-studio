from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


SOURCE_HANDOFF_VERSION = "source_handoff_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
DEFAULT_PILOT_OSM_ID = "53796999"
DEFAULT_DATASET_ID = "israel-and-palestine-260521-free-shp-zip"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "source_handoff") -> str:
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


class SourceHandoffPlanner:
    def __init__(
        self,
        output_root: Path,
        source_import_guardrails: object,
        profile_mapper: object,
        contract_execution: object,
        execution_queue: object,
        review_wording: str,
    ) -> None:
        self.output_root = output_root
        self.source_import_guardrails = source_import_guardrails
        self.profile_mapper = profile_mapper
        self.contract_execution = contract_execution
        self.execution_queue = execution_queue
        self.review_wording = review_wording
        self.handoffs_dir = output_root / "georeview_studio_source_handoffs"

    def status(self) -> dict:
        candidates = self.candidates(limit=200)
        handoffs = self.list_handoffs(200)
        ready_count = sum(1 for row in handoffs if row.get("handoff_readiness") == "ready_for_controlled_execution")
        return {
            "ok": True,
            "source_handoff_version": SOURCE_HANDOFF_VERSION,
            "mode": "approved_source_to_mapper_and_planned_queue_handoff",
            "output_dir": str(self.handoffs_dir),
            "approved_request_count": len(candidates),
            "candidate_count": len(candidates),
            "handoff_count": len(handoffs),
            "ready_handoff_count": ready_count,
            "readiness_level": "ready_for_approved_source_handoff" if candidates else "waiting_for_approved_source_import",
            "claim_boundaries": self.claim_boundaries(),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def candidates(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        try:
            requests = self.source_import_guardrails.list_requests(max(1, min(int(limit or 20), 200)))
        except Exception:
            return rows
        for row in requests:
            if row.get("latest_decision_state") != "approved_for_metadata_only_import":
                continue
            detail = self.source_import_guardrails.detail(str(row.get("request_id") or ""))
            if detail.get("error"):
                continue
            decision = self.latest_decision(detail)
            source = detail.get("source", {})
            rows.append({
                "request_id": detail.get("request_id"),
                "decision_id": decision.get("decision_id"),
                "decision_state": decision.get("decision_state"),
                "created_at": detail.get("created_at"),
                "dataset_id": source.get("dataset_id") or row.get("dataset_id") or DEFAULT_DATASET_ID,
                "file_name": source.get("file_name") or row.get("file_name"),
                "template_id": detail.get("template_id"),
                "hard_failed_count": detail.get("summary", {}).get("hard_failed_count"),
                "can_create_metadata_handoff": decision.get("can_create_metadata_handoff") is True,
                "recommended_profile_id": self.profile_for_template(str(detail.get("template_id") or "")),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def create_handoff(self, body: dict | None = None) -> dict:
        body = body or {}
        request_id = str(body.get("request_id") or "").strip()
        if not request_id:
            candidates = self.candidates(limit=1)
            if not candidates:
                return self.error("source_handoff_no_approved_request", "No approved source import request is available.")
            request_id = str(candidates[0].get("request_id") or "")
        request = self.source_import_guardrails.detail(request_id)
        if request.get("error"):
            return {
                "ok": False,
                "error": "source_import_request_not_found",
                "request_id": request_id,
                "source_gis_modified": False,
                "mutates_config": False,
            }
        decision = self.latest_decision(request)
        if decision.get("decision_state") != "approved_for_metadata_only_import":
            return self.error("source_handoff_not_approved", "The source import request is not approved for metadata-only handoff.", request_id)
        hard_failed_count = int(request.get("summary", {}).get("hard_failed_count") or 0)
        if hard_failed_count != 0 or decision.get("can_create_metadata_handoff") is not True:
            return self.error("source_handoff_not_ready", "The source import request still has blocking guardrail evidence.", request_id)

        source = request.get("source", {})
        template_id = str(request.get("template_id") or "")
        profile_id = str(body.get("profile_id") or self.profile_for_template(template_id))
        dataset_id = str(body.get("dataset_id") or source.get("dataset_id") or DEFAULT_DATASET_ID)
        pilot_osm_id = str(body.get("pilot_osm_id") or DEFAULT_PILOT_OSM_ID)
        target_workspace_id = str(
            body.get("target_workspace_id")
            or f"source_handoff_{safe_token(profile_id)}_{safe_token(dataset_id)}_planned_v001"
        )
        if not request_id or not profile_id or not dataset_id:
            return self.error("source_handoff_input_missing", "request_id, profile_id and dataset_id are required.", request_id)

        handoff_id = self.next_handoff_id(profile_id, dataset_id)
        mapper_plan = self.profile_mapper.mapper_plan({
            "profile_id": profile_id,
            "dataset_id": dataset_id,
        }, write_files=True)
        dry_run = self.contract_execution.dry_run({
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
        }, write_files=True)
        queue_job = self.execution_queue.enqueue({
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
            "execute_now": False,
        }, self.planned_only_runner)
        ready = (
            mapper_plan.get("ok") is True
            and mapper_plan.get("can_plan") is True
            and dry_run.get("ok") is True
            and dry_run.get("can_execute_now") is True
            and queue_job.get("status") == "planned"
        )
        blockers = []
        for label, payload in [("mapper_plan", mapper_plan), ("contract_dry_run", dry_run), ("queue_job", queue_job)]:
            if payload.get("error"):
                blockers.append(f"{label}:{payload.get('error')}")
            blockers.extend([f"{label}:{item}" for item in payload.get("blockers", [])])
        stamp = utc_now()
        json_path = self.handoff_path(handoff_id, ".json")
        md_path = self.handoff_path(handoff_id, ".md")
        latest_path = self.handoffs_dir / "latest_source_handoff.json"
        handoff = {
            "ok": True,
            "source_handoff_version": SOURCE_HANDOFF_VERSION,
            "handoff_id": handoff_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "request_id": request.get("request_id"),
            "decision_id": decision.get("decision_id"),
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
            "template_id": template_id,
            "source_file": source.get("file_name"),
            "source_path": source.get("path"),
            "mapper_plan_id": mapper_plan.get("plan_id"),
            "mapper_can_plan": mapper_plan.get("can_plan"),
            "contract_dry_run_id": dry_run.get("dry_run_id"),
            "contract_can_execute_now": dry_run.get("can_execute_now"),
            "queue_job_id": queue_job.get("job_id"),
            "queue_status": queue_job.get("status"),
            "execute_now": False,
            "handoff_readiness": "ready_for_controlled_execution" if ready else "blocked_by_handoff_gates",
            "ready_for_controlled_execution": ready,
            "blockers": blockers,
            "mapper_plan": self.compact_mapper(mapper_plan),
            "contract_dry_run": self.compact_dry_run(dry_run),
            "queue_job": self.compact_queue_job(queue_job),
            "claim_boundaries": self.claim_boundaries(),
            "review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)},
        }
        write_json(json_path, handoff)
        write_json(latest_path, handoff)
        md_path.write_text(self.handoff_markdown(handoff), encoding="utf-8", newline="\n")
        return {"ok": True, "handoff": handoff, "source_gis_modified": False, "mutates_config": False}

    def list_handoffs(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.handoffs_dir.exists():
            return rows
        for path in sorted(self.handoffs_dir.glob("source_handoff_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("source_handoff_version") != SOURCE_HANDOFF_VERSION:
                continue
            rows.append({
                "handoff_id": data.get("handoff_id"),
                "created_at": data.get("created_at"),
                "request_id": data.get("request_id"),
                "profile_id": data.get("profile_id"),
                "dataset_id": data.get("dataset_id"),
                "queue_job_id": data.get("queue_job_id"),
                "queue_status": data.get("queue_status"),
                "handoff_readiness": data.get("handoff_readiness"),
                "ready_for_controlled_execution": data.get("ready_for_controlled_execution"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, handoff_id: str) -> dict:
        path = self.handoff_path(handoff_id, ".json")
        if not path.exists() or not self.safe_handoff_path(path):
            return {"ok": False, "error": "source_handoff_not_found", "handoff_id": handoff_id, "source_gis_modified": False}
        data = read_json(path)
        if not data:
            return {"ok": False, "error": "source_handoff_not_found", "handoff_id": handoff_id, "source_gis_modified": False}
        return data

    def output_file(self, handoff_id: str, output_id: str = "source_handoff") -> dict:
        handoff = self.detail(handoff_id)
        if handoff.get("error"):
            return handoff
        files = handoff.get("files", {})
        path = Path(files.get("markdown") or "")
        if output_id not in {"source_handoff", "markdown"} or not path.exists():
            return {"ok": False, "error": "source_handoff_output_not_found", "handoff_id": handoff_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def handoff_path(self, handoff_id: str, suffix: str) -> Path:
        return self.handoffs_dir / f"{safe_token(handoff_id)}{suffix}"

    def safe_handoff_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.handoffs_dir.resolve())
            return True
        except ValueError:
            return False

    def next_handoff_id(self, profile_id: str, dataset_id: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"source_handoff_{safe_token(profile_id)}_{safe_token(dataset_id)}_{safe_token(stamp)}"

    @staticmethod
    def profile_for_template(template_id: str) -> str:
        mapping = {
            "safe_access": "safe_access_pedestrian_review",
            "osm_quality": "osm_tag_quality",
            "generic_layer_inventory": "generic_layer_inventory",
        }
        return mapping.get(template_id or "safe_access", "safe_access_pedestrian_review")

    @staticmethod
    def latest_decision(request: dict) -> dict:
        decisions = request.get("decisions", []) if isinstance(request, dict) else []
        return decisions[0] if decisions else {}

    @staticmethod
    def compact_mapper(plan: dict) -> dict:
        return {
            "plan_id": plan.get("plan_id"),
            "profile_id": plan.get("profile_id"),
            "dataset_id": plan.get("dataset_id"),
            "can_plan": plan.get("can_plan"),
            "blockers": plan.get("blockers", []),
            "json_file": plan.get("json_file", ""),
            "markdown_file": plan.get("markdown_file", ""),
        }

    @staticmethod
    def compact_dry_run(dry_run: dict) -> dict:
        return {
            "dry_run_id": dry_run.get("dry_run_id"),
            "profile_id": dry_run.get("profile_id"),
            "dataset_id": dry_run.get("dataset_id"),
            "can_execute_now": dry_run.get("can_execute_now"),
            "would_call": dry_run.get("would_call"),
            "blockers": dry_run.get("blockers", []),
            "json_file": dry_run.get("json_file", ""),
            "markdown_file": dry_run.get("markdown_file", ""),
        }

    @staticmethod
    def compact_queue_job(job: dict) -> dict:
        return {
            "job_id": job.get("job_id"),
            "profile_id": job.get("profile_id"),
            "dataset_id": job.get("dataset_id"),
            "target_workspace_id": job.get("target_workspace_id"),
            "status": job.get("status"),
            "execute_now": job.get("execute_now"),
            "blockers": job.get("blockers", []),
            "json_file": job.get("json_file", ""),
            "markdown_file": job.get("markdown_file", ""),
        }

    @staticmethod
    def planned_only_runner(profile_id: str, payload: dict) -> dict:
        return {
            "ok": False,
            "error": "planned_source_handoff_only",
            "profile_id": profile_id,
            "workspace_id": payload.get("workspace_id") or payload.get("target_workspace_id"),
            "source_gis_modified": False,
        }

    def error(self, error: str, detail: str, request_id: str = "") -> dict:
        return {
            "ok": False,
            "error": error,
            "detail": detail,
            "request_id": request_id,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def claim_boundaries(self) -> list[str]:
        return [
            "Source handoff creates mapper, dry-run and planned queue evidence only.",
            "It does not run domain analytics unless a separate controlled execution step is requested.",
            "It does not edit, move, rename or overwrite source GIS files.",
            "Missing OSM tags remain data-quality gaps, not proof that infrastructure is absent.",
            self.review_wording,
        ]

    def handoff_markdown(self, handoff: dict) -> str:
        lines = [
            "# Source Handoff",
            "",
            f"Handoff: `{handoff.get('handoff_id')}`",
            f"Created: `{handoff.get('created_at')}`",
            f"Readiness: `{handoff.get('handoff_readiness')}`",
            "",
            "## Approved Source",
            "",
            f"- Request: `{handoff.get('request_id')}`",
            f"- Decision: `{handoff.get('decision_id')}`",
            f"- Dataset: `{handoff.get('dataset_id')}`",
            f"- Source file: `{handoff.get('source_file')}`",
            f"- Source path: `{handoff.get('source_path')}`",
            "",
            "## Mapper Plan",
            "",
            f"- Profile: `{handoff.get('profile_id')}`",
            f"- Plan: `{handoff.get('mapper_plan_id')}`",
            f"- Can plan: `{handoff.get('mapper_can_plan')}`",
            "",
            "## Contract Dry Run",
            "",
            f"- Dry run: `{handoff.get('contract_dry_run_id')}`",
            f"- Can execute now: `{handoff.get('contract_can_execute_now')}`",
            f"- Target workspace: `{handoff.get('target_workspace_id')}`",
            "",
            "## Planned Queue Job",
            "",
            f"- Queue job: `{handoff.get('queue_job_id')}`",
            f"- Queue status: `{handoff.get('queue_status')}`",
            "- Execute now: `false`",
            "",
            "## Boundaries",
            "",
        ]
        for item in self.claim_boundaries():
            lines.append(f"- {item}")
        if handoff.get("blockers"):
            lines.extend(["", "## Blockers", ""])
            for blocker in handoff.get("blockers", []):
                lines.append(f"- `{blocker}`")
        lines.extend([
            "",
            "## Evidence Files",
            "",
            f"- Mapper JSON/Markdown: `{handoff.get('mapper_plan', {}).get('json_file')}` / `{handoff.get('mapper_plan', {}).get('markdown_file')}`",
            f"- Dry-run JSON/Markdown: `{handoff.get('contract_dry_run', {}).get('json_file')}` / `{handoff.get('contract_dry_run', {}).get('markdown_file')}`",
            f"- Queue JSON/Markdown: `{handoff.get('queue_job', {}).get('json_file')}` / `{handoff.get('queue_job', {}).get('markdown_file')}`",
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)
