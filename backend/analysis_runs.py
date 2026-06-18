from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path


ANALYSIS_RUNS_VERSION = "analysis_runs_v001"
ANALYSIS_JOB_TYPES = {"analysis_workflow_safe_access", "safe_access_pilot"}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (JSONDecodeError, OSError):
        return {}


def parse_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def output_id(kind: str, name: str) -> str:
    allowed = []
    for char in f"{kind}_{Path(name).stem}".lower():
        allowed.append(char if char.isalnum() else "_")
    return "_".join(part for part in "".join(allowed).split("_") if part)


class AnalysisRuns:
    def __init__(self, runs_dir: Path, workspaces_dir: Path) -> None:
        self.runs_dir = runs_dir
        self.workspaces_dir = workspaces_dir

    def list(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(limit, 200))
        runs = []
        for path in sorted(self.runs_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            record = read_json(path)
            if not self.is_analysis_record(record):
                continue
            runs.append(self.compact_run(record))
            if len(runs) >= limit:
                break
        return runs

    def detail(self, run_id: str) -> dict:
        record = self.record(run_id)
        if not record:
            return {"error": "analysis_run_not_found", "run_id": run_id}
        workspace_id = self.active_workspace_id(record)
        outputs = self.outputs_for_workspace(workspace_id)
        self.add_download_urls(record.get("job_id"), outputs)
        workspace_summary = self.workspace_summary(workspace_id)
        return {
            "ok": True,
            "analysis_runs_version": ANALYSIS_RUNS_VERSION,
            "run": self.compact_run(record, outputs),
            "payload": record.get("payload", {}),
            "logs": record.get("logs", []),
            "outputs": outputs,
            "dashboard_links": self.dashboard_links(workspace_id),
            "workspace_summary": workspace_summary,
            "source_gis_modified": record.get("source_gis_modified") is True,
        }

    def outputs(self, run_id: str) -> dict:
        detail = self.detail(run_id)
        if "error" in detail:
            return detail
        return {
            "ok": True,
            "run_id": run_id,
            "active_workspace_id": detail["run"].get("active_workspace_id"),
            "outputs": detail.get("outputs", []),
            "source_gis_modified": False,
        }

    def output_file(self, run_id: str, requested_output_id: str) -> dict:
        detail = self.detail(run_id)
        if "error" in detail:
            return detail
        for item in detail.get("outputs", []):
            if item.get("output_id") == requested_output_id:
                path = Path(item.get("path", ""))
                if not self.safe_output_path(path) or not path.exists() or not path.is_file():
                    return {"error": "analysis_output_not_found", "run_id": run_id, "output_id": requested_output_id}
                return {"ok": True, "path": path, "file_name": path.name, "kind": item.get("kind")}
        return {"error": "analysis_output_not_found", "run_id": run_id, "output_id": requested_output_id}

    def rerun_payload(self, run_id: str) -> dict:
        record = self.record(run_id)
        if not record:
            return {"error": "analysis_run_not_found", "run_id": run_id}
        payload = record.get("payload", {})
        if not payload.get("pilot_osm_id"):
            return {"error": "analysis_run_payload_missing", "run_id": run_id}
        return dict(payload)

    def record(self, run_id: str) -> dict:
        clean = "".join(ch for ch in str(run_id) if ch.isalnum() or ch in {"_", "-"})
        path = self.runs_dir / f"{clean}.json"
        record = read_json(path)
        return record if self.is_analysis_record(record) else {}

    def compact_run(self, record: dict, outputs: list[dict] | None = None) -> dict:
        payload = record.get("payload", {})
        workspace_id = self.active_workspace_id(record)
        output_count = len(outputs) if outputs is not None else len(self.outputs_for_workspace(workspace_id))
        return {
            "run_id": record.get("job_id"),
            "job_id": record.get("job_id"),
            "run_type": record.get("job_type"),
            "status": record.get("status"),
            "created_at_utc": record.get("created_at_utc"),
            "started_at_utc": record.get("started_at_utc"),
            "finished_at_utc": record.get("finished_at_utc"),
            "runtime_seconds": record.get("runtime_seconds"),
            "dataset_id": payload.get("dataset_id"),
            "pilot_osm_id": payload.get("pilot_osm_id"),
            "pilot_name": payload.get("pilot_name"),
            "route_aware": payload.get("route_aware") is True,
            "active_workspace_id": workspace_id,
            "output_count": output_count,
            "dashboard_url": f"/api/dashboard-workspaces/{workspace_id}/summary" if workspace_id else "",
            "error": record.get("error"),
            "source_gis_modified": record.get("source_gis_modified") is True,
            "log_count": len(record.get("logs", [])),
        }

    def outputs_for_workspace(self, workspace_id: str) -> list[dict]:
        if not workspace_id:
            return []
        workspace_dir = self.workspaces_dir / workspace_id
        manifest = read_json(workspace_dir / "manifest.json")
        if not manifest:
            return []
        outputs = []
        for table in manifest.get("tables", []):
            file_path = Path(table.get("file", ""))
            if self.safe_output_path(file_path) and file_path.exists():
                item_id = output_id("table", table.get("table") or file_path.name)
                outputs.append({
                    "output_id": item_id,
                    "kind": "table",
                    "label": table.get("table") or file_path.name,
                    "file_name": file_path.name,
                    "path": str(file_path),
                    "rows": table.get("rows"),
                    "size_bytes": file_path.stat().st_size,
                    "download_url": "",
                })
        for report_name, report_path in manifest.get("reports", {}).items():
            file_path = Path(report_path)
            if self.safe_output_path(file_path) and file_path.exists():
                item_id = output_id("report", report_name)
                outputs.append({
                    "output_id": item_id,
                    "kind": "report",
                    "label": report_name,
                    "file_name": file_path.name,
                    "path": str(file_path),
                    "rows": None,
                    "size_bytes": file_path.stat().st_size,
                    "download_url": "",
                })
        return outputs

    @staticmethod
    def add_download_urls(run_id: str, outputs: list[dict]) -> None:
        for item in outputs:
            item["download_url"] = f"/api/analysis-runs/{run_id}/outputs/{item.get('output_id')}"

    def workspace_summary(self, workspace_id: str) -> dict:
        if not workspace_id:
            return {}
        return read_json(self.workspaces_dir / workspace_id / "reports" / "workspace_summary.json")

    @staticmethod
    def dashboard_links(workspace_id: str) -> dict:
        if not workspace_id:
            return {}
        encoded = workspace_id
        return {
            "summary": f"/api/dashboard-workspaces/{encoded}/summary",
            "candidates": f"/api/dashboard-workspaces/{encoded}/candidates?limit=150",
            "network_access": f"/api/dashboard-workspaces/{encoded}/network-access?limit=150",
            "map_features": f"/api/dashboard-workspaces/{encoded}/map-features",
            "validation": f"/api/dashboard-workspaces/{encoded}/validation",
        }

    @staticmethod
    def is_analysis_record(record: dict) -> bool:
        return isinstance(record, dict) and record.get("job_type") in ANALYSIS_JOB_TYPES and bool(record.get("job_id"))

    @staticmethod
    def active_workspace_id(record: dict) -> str:
        result = record.get("result") if isinstance(record.get("result"), dict) else {}
        payload = record.get("payload", {}) if isinstance(record.get("payload"), dict) else {}
        return (
            result.get("active_workspace_id")
            or payload.get("route_workspace_id")
            or payload.get("workspace_id")
            or ""
        )

    def safe_output_path(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
            root = self.workspaces_dir.resolve()
        except OSError:
            return False
        try:
            resolved.relative_to(root)
        except ValueError:
            return False
        return True
