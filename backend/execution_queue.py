from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


EXECUTION_QUEUE_VERSION = "execution_queue_v001"
REVIEW_WORDING = "This location has infrastructure risk indicators and should be reviewed on-site."
ALLOWED_EXECUTION_STATUSES = {"dry_run_ready_existing_runner", "dry_run_ready_read_only_runner"}
ALLOWED_PROFILES = {
    "safe_access_pedestrian_review",
    "transit_stop_walk_access",
    "park_playground_access",
    "osm_tag_quality",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_token(value: object, fallback: str = "execution_queue") -> str:
    chars = []
    for char in str(value or ""):
        if char.isalnum() or char in {"_", "-"}:
            chars.append(char)
        else:
            chars.append("_")
    token = "_".join(part for part in "".join(chars).split("_") if part)
    return token[:120] or fallback


def boolish(value: object) -> bool:
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
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ControlledExecutionQueue:
    def __init__(self, contract_execution: object, output_root: Path) -> None:
        self.contract_execution = contract_execution
        self.output_root = output_root
        self.jobs_dir = output_root / "georeview_studio_execution_queue"

    def status(self) -> dict:
        contract_status = self.contract_execution.status()
        adapters = contract_status.get("adapters", [])
        executable = [
            adapter for adapter in adapters
            if adapter.get("profile_id") in ALLOWED_PROFILES and adapter.get("execution_status") in ALLOWED_EXECUTION_STATUSES
        ]
        jobs = self.list_jobs(200)
        return {
            "ok": True,
            "execution_queue_version": EXECUTION_QUEUE_VERSION,
            "mode": "controlled_local_execution",
            "jobs_dir": str(self.jobs_dir),
            "allowed_profiles": sorted(ALLOWED_PROFILES),
            "allowed_execution_statuses": sorted(ALLOWED_EXECUTION_STATUSES),
            "adapter_count": len(adapters),
            "executable_profile_count": len(executable),
            "job_count": len(jobs),
            "recent_jobs": jobs[:5],
            "policy": {
                "requires_contract_dry_run_can_execute_now": True,
                "allowlisted_profiles_only": True,
                "authored_draft_execution_supported": True,
                "writes_only_queue_records_and_runner_outputs_under_analysis_output": True,
                "does_not_modify_source_gis": True,
                "no_credentials_required": True,
            },
            "approved_review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }

    def enqueue(self, body: dict | None, runner: Callable[[str, dict], dict]) -> dict:
        body = body or {}
        profile_id = str(body.get("profile_id") or "osm_tag_quality")
        dataset_id = str(body.get("dataset_id") or "israel-and-palestine-260521-free-shp-zip")
        pilot_osm_id = str(body.get("pilot_osm_id") or "53796999")
        target_workspace_id = str(body.get("target_workspace_id") or body.get("workspace_id") or self.contract_execution.default_workspace_id(profile_id))
        execute_now = boolish(body.get("execute_now", True))
        dry_run = self.contract_execution.dry_run({
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
        }, write_files=True)
        job_id = self.next_job_id(profile_id, dataset_id)
        job = {
            "ok": True,
            "execution_queue_version": EXECUTION_QUEUE_VERSION,
            "job_id": job_id,
            "created_at_utc": utc_now(),
            "completed_at_utc": "",
            "profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": pilot_osm_id,
            "target_workspace_id": target_workspace_id,
            "execute_now": execute_now,
            "status": "queued",
            "request": {
                "profile_id": profile_id,
                "dataset_id": dataset_id,
                "pilot_osm_id": pilot_osm_id,
                "target_workspace_id": target_workspace_id,
                "execute_now": execute_now,
            },
            "dry_run": dry_run,
            "runner_result": {},
            "blockers": [],
            "review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }
        if profile_id not in ALLOWED_PROFILES:
            return self.blocked_job(job, "profile_not_allowlisted")
        adapter_status = dry_run.get("adapter", {}).get("execution_status")
        if adapter_status not in ALLOWED_EXECUTION_STATUSES:
            return self.blocked_job(job, adapter_status or "adapter_not_executable")
        if dry_run.get("can_execute_now") is not True:
            blockers = dry_run.get("blockers", []) or ["dry_run_not_executable"]
            return self.blocked_job(job, *blockers)
        if not execute_now:
            job["status"] = "planned"
            job["completed_at_utc"] = utc_now()
            return self.write_job(job)

        payload = dict(body)
        payload["workspace_id"] = target_workspace_id
        payload.setdefault("dataset_id", dataset_id)
        payload.setdefault("pilot_osm_id", pilot_osm_id)
        try:
            runner_result = runner(profile_id, payload)
        except Exception as exc:  # pragma: no cover - preserved in local job record
            job["status"] = "failed"
            job["blockers"] = [repr(exc)]
            job["completed_at_utc"] = utc_now()
            return self.write_job(job)
        job["runner_result"] = self.compact_runner_result(runner_result)
        job["status"] = "succeeded" if runner_result.get("ok") else "failed"
        if not runner_result.get("ok"):
            job["blockers"] = [str(runner_result.get("error") or "runner_failed")]
        job["completed_at_utc"] = utc_now()
        return self.write_job(job)

    def enqueue_authored_draft(self, body: dict | None, draft_provider: object, runner) -> dict:
        body = body or {}
        draft_id = str(body.get("draft_id") or "").strip()
        execute_now = boolish(body.get("execute_now", True))
        if not draft_id:
            return {
                "ok": False,
                "error": "authored_profile_draft_missing",
                "detail": "draft_id is required",
                "source_gis_modified": False,
            }
        draft = draft_provider.detail(draft_id)
        profile_id = str(draft.get("profile_id") or "authored_profile_audit")
        dataset_id = str(body.get("dataset_id") or draft.get("dataset_id") or "israel-and-palestine-260521-free-shp-zip")
        target_workspace_id = str(body.get("target_workspace_id") or body.get("workspace_id") or f"authored_profile_{safe_token(profile_id)}_v001")
        job_id = self.next_job_id(f"authored_{profile_id}", dataset_id)
        compatibility = draft.get("compatibility", {}) if isinstance(draft, dict) else {}
        job = {
            "ok": True,
            "execution_queue_version": EXECUTION_QUEUE_VERSION,
            "job_id": job_id,
            "created_at_utc": utc_now(),
            "completed_at_utc": "",
            "profile_id": "authored_profile_audit",
            "authored_profile_id": profile_id,
            "dataset_id": dataset_id,
            "pilot_osm_id": str(body.get("pilot_osm_id") or "53796999"),
            "target_workspace_id": target_workspace_id,
            "execute_now": execute_now,
            "status": "queued",
            "request": {
                "draft_id": draft_id,
                "profile_id": profile_id,
                "dataset_id": dataset_id,
                "target_workspace_id": target_workspace_id,
                "execute_now": execute_now,
            },
            "dry_run": {
                "ok": not bool(draft.get("error")),
                "dry_run_type": "authored_template_draft",
                "draft_id": draft_id,
                "profile_id": profile_id,
                "can_execute_now": compatibility.get("can_plan") is True,
                "blockers": compatibility.get("blockers", []) if isinstance(compatibility, dict) else [],
                "warnings": compatibility.get("warnings", []) if isinstance(compatibility, dict) else [],
                "read_only_policy": "source_gis_modified=false",
            },
            "runner_result": {},
            "blockers": [],
            "review_wording": REVIEW_WORDING,
            "source_gis_modified": False,
        }
        if draft.get("error"):
            return self.blocked_job(job, draft.get("error"))
        if compatibility.get("can_plan") is not True:
            return self.blocked_job(job, *(compatibility.get("blockers", []) or ["draft_not_compatible"]))
        if not execute_now:
            job["status"] = "planned"
            job["completed_at_utc"] = utc_now()
            return self.write_job(job)
        payload = dict(body)
        payload["workspace_id"] = target_workspace_id
        payload.setdefault("dataset_id", dataset_id)
        try:
            runner_result = runner(draft_id, payload)
        except Exception as exc:  # pragma: no cover - preserved in local job record
            job["status"] = "failed"
            job["blockers"] = [repr(exc)]
            job["completed_at_utc"] = utc_now()
            return self.write_job(job)
        job["runner_result"] = self.compact_runner_result(runner_result)
        job["status"] = "succeeded" if runner_result.get("ok") else "failed"
        if not runner_result.get("ok"):
            job["blockers"] = [str(runner_result.get("error") or "runner_failed")]
        job["completed_at_utc"] = utc_now()
        return self.write_job(job)

    def blocked_job(self, job: dict, *blockers: object) -> dict:
        job["ok"] = False
        job["error"] = "execution_queue_profile_blocked"
        job["status"] = "blocked"
        job["blockers"] = [str(item) for item in blockers if item]
        job["completed_at_utc"] = utc_now()
        return self.write_job(job)

    def write_job(self, job: dict) -> dict:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.job_path(job["job_id"], ".json")
        md_path = self.job_path(job["job_id"], ".md")
        write_json(json_path, job)
        md_path.write_text(self.job_markdown(job), encoding="utf-8")
        job["json_file"] = str(json_path)
        job["markdown_file"] = str(md_path)
        return job

    def list_jobs(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 200))
        rows = []
        if not self.jobs_dir.exists():
            return rows
        for path in sorted(self.jobs_dir.glob("execution_queue_job_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path)
            if data.get("execution_queue_version") != EXECUTION_QUEUE_VERSION:
                continue
            rows.append({
                "ok": True,
                "job_id": data.get("job_id"),
                "profile_id": data.get("profile_id"),
                "dataset_id": data.get("dataset_id"),
                "target_workspace_id": data.get("target_workspace_id"),
                "status": data.get("status"),
                "execute_now": data.get("execute_now"),
                "created_at_utc": data.get("created_at_utc"),
                "completed_at_utc": data.get("completed_at_utc"),
                "source_gis_modified": data.get("source_gis_modified") is True,
            })
            if len(rows) >= limit:
                break
        return rows

    def detail(self, job_id: str) -> dict:
        path = self.job_path(job_id, ".json")
        if not path.exists() or not self.safe_job_path(path):
            return {"ok": False, "error": "execution_queue_job_not_found", "job_id": job_id, "source_gis_modified": False}
        data = read_json(path)
        if not data:
            return {"ok": False, "error": "execution_queue_job_not_found", "job_id": job_id, "source_gis_modified": False}
        data["json_file"] = str(path)
        md_path = self.job_path(job_id, ".md")
        data["markdown_file"] = str(md_path) if md_path.exists() else ""
        return data

    @staticmethod
    def compact_runner_result(result: dict) -> dict:
        workspace = result.get("workspace", {}) if isinstance(result, dict) else {}
        manifest = workspace.get("manifest", {}) if isinstance(workspace, dict) else {}
        summary = workspace.get("summary", {}) if isinstance(workspace, dict) else {}
        return {
            "ok": result.get("ok") if isinstance(result, dict) else False,
            "error": result.get("error", "") if isinstance(result, dict) else "runner_result_not_dict",
            "workspace_id": manifest.get("workspace_id") or result.get("active_workspace_id", "") if isinstance(result, dict) else "",
            "profile_id": manifest.get("profile_id") or result.get("profile_id", "") if isinstance(result, dict) else "",
            "created": result.get("created") if isinstance(result, dict) else "",
            "summary_counts": summary.get("counts", {}) if isinstance(summary, dict) else {},
            "source_gis_modified": result.get("source_gis_modified") is True if isinstance(result, dict) else False,
        }

    @staticmethod
    def job_markdown(job: dict) -> str:
        lines = [
            "# Controlled Execution Queue Job",
            "",
            f"Job id: `{job.get('job_id')}`",
            f"Profile: `{job.get('profile_id')}`",
            f"Authored profile: `{job.get('authored_profile_id', '')}`",
            f"Status: `{job.get('status')}`",
            f"Target workspace: `{job.get('target_workspace_id')}`",
            "",
            "## Gates",
            "",
            f"- Contract dry run can execute now: `{job.get('dry_run', {}).get('can_execute_now')}`",
            f"- Execute now: `{job.get('execute_now')}`",
            "- Source GIS files are not modified.",
            f"- {REVIEW_WORDING}",
        ]
        if job.get("blockers"):
            lines.extend(["", "## Blockers", ""])
            for blocker in job.get("blockers", []):
                lines.append(f"- `{blocker}`")
        return "\n".join(lines).rstrip() + "\n"

    def next_job_id(self, profile_id: str, dataset_id: str) -> str:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
        return f"execution_queue_job_{safe_token(profile_id)}_{safe_token(dataset_id)}_{safe_token(stamp)}"

    def job_path(self, job_id: str, suffix: str) -> Path:
        return self.jobs_dir / f"{safe_token(job_id)}{suffix}"

    def safe_job_path(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.jobs_dir.resolve())
            return True
        except ValueError:
            return False
