from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


SOURCE_HANDOFF_EXECUTION_VERSION = "source_handoff_execution_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
EXECUTION_ACK_PHRASE = "execute approved handoff"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "source_handoff_execution") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:130] or fallback


def boolish(value: object, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    return str(value).strip().lower() not in {"false", "0", "no"}


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


class SourceHandoffExecutionController:
    def __init__(
        self,
        output_root: Path,
        workspaces_dir: Path,
        source_handoff: object,
        execution_queue: object,
        review_wording: str,
    ) -> None:
        self.output_root = output_root
        self.workspaces_dir = workspaces_dir
        self.source_handoff = source_handoff
        self.execution_queue = execution_queue
        self.review_wording = review_wording
        self.executions_dir = output_root / "georeview_studio_source_handoff_executions"

    def status(self) -> dict:
        candidates = self.candidates(limit=200)
        executions = self.list_executions(limit=200)
        successful = [row for row in executions if row.get("execution_readiness") == "executed_and_verified"]
        return {
            "ok": True,
            "source_handoff_execution_version": SOURCE_HANDOFF_EXECUTION_VERSION,
            "mode": "explicit_controlled_execution_from_approved_handoff",
            "output_dir": str(self.executions_dir),
            "candidate_count": len(candidates),
            "execution_count": len(executions),
            "successful_execution_count": len(successful),
            "execution_ack_phrase": EXECUTION_ACK_PHRASE,
            "readiness_level": "ready_for_controlled_handoff_execution" if candidates else "waiting_for_ready_source_handoff",
            "claim_boundaries": self.claim_boundaries(),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def candidates(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        try:
            handoffs = self.source_handoff.list_handoffs(max(1, min(int(limit or 20), 200)))
        except Exception:
            return rows
        for row in handoffs:
            if row.get("handoff_readiness") != "ready_for_controlled_execution":
                continue
            detail = self.source_handoff.detail(str(row.get("handoff_id") or ""))
            if detail.get("error"):
                continue
            rows.append({
                "handoff_id": detail.get("handoff_id"),
                "created_at": detail.get("created_at"),
                "request_id": detail.get("request_id"),
                "decision_id": detail.get("decision_id"),
                "profile_id": detail.get("profile_id"),
                "dataset_id": detail.get("dataset_id"),
                "pilot_osm_id": detail.get("pilot_osm_id"),
                "target_workspace_id": detail.get("target_workspace_id"),
                "planned_queue_job_id": detail.get("queue_job_id"),
                "handoff_readiness": detail.get("handoff_readiness"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def execute_handoff(self, body: dict | None, runner: Callable[[str, dict], dict]) -> dict:
        body = body or {}
        ack_error = self.validate_acknowledgements(body)
        if ack_error:
            return ack_error
        handoff_id = str(body.get("handoff_id") or "").strip()
        if not handoff_id:
            candidates = self.candidates(limit=1)
            if not candidates:
                return self.error("source_handoff_execution_input_missing", "handoff_id is required when no ready handoff candidate exists.")
            handoff_id = str(candidates[0].get("handoff_id") or "")
        handoff = self.source_handoff.detail(handoff_id)
        if handoff.get("error"):
            return {"ok": False, "error": "source_handoff_not_found", "handoff_id": handoff_id, "source_gis_modified": False, "mutates_config": False}
        if handoff.get("handoff_readiness") != "ready_for_controlled_execution" or handoff.get("ready_for_controlled_execution") is not True:
            return self.error("source_handoff_execution_not_ready", "The handoff is not ready for controlled execution.", handoff_id)

        profile_id = str(body.get("profile_id") or handoff.get("profile_id") or "")
        dataset_id = str(body.get("dataset_id") or handoff.get("dataset_id") or "")
        pilot_osm_id = str(body.get("pilot_osm_id") or handoff.get("pilot_osm_id") or "53796999")
        target_workspace_id = str(body.get("target_workspace_id") or handoff.get("target_workspace_id") or "")
        route_aware = boolish(body.get("route_aware"), default=False)
        route_workspace_id = str(body.get("route_workspace_id") or f"{target_workspace_id}_route_aware")
        if not profile_id or not dataset_id or not target_workspace_id:
            return self.error("source_handoff_execution_input_missing", "profile_id, dataset_id and target_workspace_id are required.", handoff_id)

        queue_job = self.execution_queue.enqueue({
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
            "workspace_id": target_workspace_id,
            "route_workspace_id": route_workspace_id,
            "route_aware": route_aware,
            "execute_now": True,
        }, runner)
        generated_workspace_id = self.generated_workspace_id(queue_job, target_workspace_id)
        workspace = self.workspace_evidence(generated_workspace_id)
        comparison = self.compare_evidence(handoff, queue_job, workspace, generated_workspace_id, target_workspace_id)
        ready = queue_job.get("status") == "succeeded" and comparison.get("comparison_readiness") == "outputs_match_handoff_evidence"
        stamp = utc_now()
        execution_id = self.next_execution_id(profile_id, dataset_id)
        json_path = self.execution_path(execution_id, ".json")
        md_path = self.execution_path(execution_id, ".md")
        latest_path = self.executions_dir / "latest_source_handoff_execution.json"
        execution = {
            "ok": True,
            "source_handoff_execution_version": SOURCE_HANDOFF_EXECUTION_VERSION,
            "execution_id": execution_id,
            "created_at": stamp,
            "created_by": str(body.get("created_by") or "local_operator"),
            "handoff_id": handoff.get("handoff_id"),
            "request_id": handoff.get("request_id"),
            "decision_id": handoff.get("decision_id"),
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
            "route_aware": route_aware,
            "planned_queue_job_id": handoff.get("queue_job_id"),
            "execution_queue_job_id": queue_job.get("job_id"),
            "execution_status": queue_job.get("status"),
            "generated_workspace_id": generated_workspace_id,
            "execution_readiness": "executed_and_verified" if ready else "execution_needs_review",
            "comparison": comparison,
            "queue_job": self.compact_queue_job(queue_job),
            "workspace": workspace,
            "claim_boundaries": self.claim_boundaries(),
            "review_wording": self.review_wording,
            "source_gis_modified": False,
            "mutates_config": False,
            "files": {"json": str(json_path), "markdown": str(md_path), "latest": str(latest_path)},
        }
        write_json(json_path, execution)
        write_json(latest_path, execution)
        md_path.write_text(self.execution_markdown(execution), encoding="utf-8", newline="\n")
        return {"ok": True, "execution": execution, "source_gis_modified": False, "mutates_config": False}

    def list_executions(self, limit: int = 20) -> list[dict]:
        rows: list[dict] = []
        if not self.executions_dir.exists():
            return rows
        for path in sorted(self.executions_dir.glob("source_handoff_execution_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("source_handoff_execution_version") != SOURCE_HANDOFF_EXECUTION_VERSION:
                continue
            rows.append({
                "execution_id": data.get("execution_id"),
                "created_at": data.get("created_at"),
                "handoff_id": data.get("handoff_id"),
                "profile_id": data.get("profile_id"),
                "dataset_id": data.get("dataset_id"),
                "execution_queue_job_id": data.get("execution_queue_job_id"),
                "execution_status": data.get("execution_status"),
                "generated_workspace_id": data.get("generated_workspace_id"),
                "execution_readiness": data.get("execution_readiness"),
                "source_gis_modified": False,
                "mutates_config": False,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, execution_id: str) -> dict:
        path = self.execution_path(execution_id, ".json")
        if not path.exists() or not self.safe_execution_path(path):
            return {"ok": False, "error": "source_handoff_execution_not_found", "execution_id": execution_id, "source_gis_modified": False}
        data = read_json(path)
        if not data:
            return {"ok": False, "error": "source_handoff_execution_not_found", "execution_id": execution_id, "source_gis_modified": False}
        return data

    def output_file(self, execution_id: str, output_id: str = "source_handoff_execution") -> dict:
        execution = self.detail(execution_id)
        if execution.get("error"):
            return execution
        path = Path((execution.get("files") or {}).get("markdown") or "")
        if output_id not in {"source_handoff_execution", "markdown"} or not path.exists():
            return {"ok": False, "error": "source_handoff_execution_output_not_found", "execution_id": execution_id, "output_id": output_id}
        return {"ok": True, "path": path, "source_gis_modified": False, "mutates_config": False}

    def validate_acknowledgements(self, body: dict) -> dict:
        required = {
            "execution_ack": str(body.get("execution_ack") or "").strip() == EXECUTION_ACK_PHRASE,
            "source_files_read_only_ack": bool(body.get("source_files_read_only_ack")),
            "generated_outputs_only_ack": bool(body.get("generated_outputs_only_ack")),
            "claim_boundary_ack": bool(body.get("claim_boundary_ack")),
            "compare_outputs_ack": bool(body.get("compare_outputs_ack")),
        }
        missing = [key for key, ok in required.items() if not ok]
        if missing:
            return {
                "ok": False,
                "error": "source_handoff_execution_ack_missing",
                "detail": f"execution is missing required acknowledgements: {', '.join(missing)}",
                "execution_ack_phrase": EXECUTION_ACK_PHRASE,
                "source_gis_modified": False,
                "mutates_config": False,
            }
        return {}

    def workspace_evidence(self, workspace_id: str) -> dict:
        workspace_dir = self.workspaces_dir / safe_token(workspace_id, "workspace")
        manifest_path = workspace_dir / "manifest.json"
        manifest = read_json(manifest_path)
        tables = manifest.get("tables", []) if isinstance(manifest, dict) else []
        return {
            "workspace_id": workspace_id,
            "workspace_dir": str(workspace_dir),
            "manifest_exists": bool(manifest),
            "table_count": len(tables),
            "tables": [
                {
                    "table": table.get("table"),
                    "rows": table.get("rows"),
                    "file": table.get("file"),
                }
                for table in tables
            ],
            "source_gis_modified": manifest.get("source_gis_modified") is True if manifest else False,
        }

    def compare_evidence(self, handoff: dict, queue_job: dict, workspace: dict, generated_workspace_id: str, target_workspace_id: str) -> dict:
        expected_outputs = self.expected_outputs(handoff)
        actual_tables = {str(table.get("table") or "") for table in workspace.get("tables", [])}
        missing_outputs = [name for name in expected_outputs if name not in actual_tables]
        checks = [
            self.check("profile_matches", str(queue_job.get("profile_id") or "") == str(handoff.get("profile_id") or ""), {"handoff_profile": handoff.get("profile_id"), "queue_profile": queue_job.get("profile_id")}),
            self.check("dataset_matches", str(queue_job.get("dataset_id") or "") == str(handoff.get("dataset_id") or ""), {"handoff_dataset": handoff.get("dataset_id"), "queue_dataset": queue_job.get("dataset_id")}),
            self.check("target_workspace_matches", generated_workspace_id == target_workspace_id, {"generated_workspace_id": generated_workspace_id, "target_workspace_id": target_workspace_id}),
            self.check("planned_to_executed", handoff.get("queue_status") == "planned" and queue_job.get("status") == "succeeded", {"planned_queue_status": handoff.get("queue_status"), "execution_status": queue_job.get("status")}),
            self.check("workspace_manifest_exists", workspace.get("manifest_exists") is True, {"workspace_id": generated_workspace_id, "workspace_dir": workspace.get("workspace_dir")}),
            self.check("canonical_outputs_present", not missing_outputs and len(expected_outputs) > 0, {"expected_outputs": expected_outputs, "actual_tables": sorted(actual_tables), "missing_outputs": missing_outputs}),
            self.check("source_gis_read_only", handoff.get("source_gis_modified") is False and queue_job.get("source_gis_modified") is False and workspace.get("source_gis_modified") is False, {"handoff": handoff.get("source_gis_modified"), "queue": queue_job.get("source_gis_modified"), "workspace": workspace.get("source_gis_modified")}),
        ]
        passed = all(item.get("passed") for item in checks)
        return {
            "comparison_readiness": "outputs_match_handoff_evidence" if passed else "comparison_needs_review",
            "passed_check_count": sum(1 for item in checks if item.get("passed")),
            "check_count": len(checks),
            "expected_outputs": expected_outputs,
            "actual_tables": sorted(actual_tables),
            "missing_outputs": missing_outputs,
            "checks": checks,
            "source_gis_modified": False,
        }

    def expected_outputs(self, handoff: dict) -> list[str]:
        mapper_json = Path(((handoff.get("mapper_plan") or {}).get("json_file") or ""))
        mapper_plan = read_json(mapper_json)
        outputs = mapper_plan.get("canonical_outputs", [])
        if isinstance(outputs, list) and outputs:
            return [str(item) for item in outputs]
        return ["pedestrian_generators", "crossings", "road_segments", "risk_assessment_results"]

    @staticmethod
    def check(check_id: str, passed: bool, evidence: dict) -> dict:
        return {"check_id": check_id, "passed": passed, "status": "passed" if passed else "failed", "evidence": evidence}

    @staticmethod
    def generated_workspace_id(queue_job: dict, fallback: str) -> str:
        runner_result = queue_job.get("runner_result", {}) if isinstance(queue_job, dict) else {}
        workspace_id = runner_result.get("workspace_id") if isinstance(runner_result, dict) else ""
        return str(workspace_id or fallback)

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
            "runner_result": job.get("runner_result", {}),
        }

    def execution_path(self, execution_id: str, suffix: str) -> Path:
        return self.executions_dir / f"{safe_token(execution_id)}{suffix}"

    def safe_execution_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.executions_dir.resolve())
            return True
        except ValueError:
            return False

    def next_execution_id(self, profile_id: str, dataset_id: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"source_handoff_execution_{safe_token(profile_id)}_{safe_token(dataset_id)}_{safe_token(stamp)}"

    def error(self, error: str, detail: str, handoff_id: str = "") -> dict:
        return {
            "ok": False,
            "error": error,
            "detail": detail,
            "handoff_id": handoff_id,
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def claim_boundaries(self) -> list[str]:
        return [
            "Source handoff execution is explicit and acknowledgement-gated.",
            "It writes generated workspace and queue evidence under analysis_output only.",
            "It does not edit, move, rename or overwrite source GIS files.",
            "Generated metrics remain infrastructure review indicators and data-quality evidence.",
            self.review_wording,
        ]

    def execution_markdown(self, execution: dict) -> str:
        comparison = execution.get("comparison", {})
        lines = [
            "# Source Handoff Execution",
            "",
            f"Execution: `{execution.get('execution_id')}`",
            f"Created: `{execution.get('created_at')}`",
            f"Readiness: `{execution.get('execution_readiness')}`",
            "",
            "## Handoff",
            "",
            f"- Handoff: `{execution.get('handoff_id')}`",
            f"- Request: `{execution.get('request_id')}`",
            f"- Decision: `{execution.get('decision_id')}`",
            f"- Profile: `{execution.get('profile_id')}`",
            f"- Dataset: `{execution.get('dataset_id')}`",
            f"- Target workspace: `{execution.get('target_workspace_id')}`",
            "",
            "## Execution",
            "",
            f"- Planned queue job: `{execution.get('planned_queue_job_id')}`",
            f"- Execution queue job: `{execution.get('execution_queue_job_id')}`",
            f"- Execution status: `{execution.get('execution_status')}`",
            f"- Generated workspace: `{execution.get('generated_workspace_id')}`",
            "",
            "## Comparison",
            "",
            f"- Readiness: `{comparison.get('comparison_readiness')}`",
            f"- Checks passed: `{comparison.get('passed_check_count')}` / `{comparison.get('check_count')}`",
            f"- Expected outputs: `{', '.join(comparison.get('expected_outputs', []))}`",
            f"- Missing outputs: `{', '.join(comparison.get('missing_outputs', []))}`",
            "",
            "## Check Details",
            "",
        ]
        for check in comparison.get("checks", []):
            lines.append(f"- `{check.get('check_id')}`: `{check.get('status')}`")
        lines.extend(["", "## Boundaries", ""])
        for item in self.claim_boundaries():
            lines.append(f"- {item}")
        lines.extend([
            "",
            "Source GIS modified: `false`",
            "Config mutated: `false`",
            "",
        ])
        return "\n".join(lines)
