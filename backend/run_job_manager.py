from __future__ import annotations

import json
import time
import threading
import traceback
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from uuid import uuid4


TERMINAL_STATUSES = {"succeeded", "failed"}


class RunJobManager:
    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = runs_dir
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def start(self, job_type: str, payload: dict, runner) -> dict:
        job_id = f"job_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex[:10]}"
        record = {
            "job_id": job_id,
            "job_type": job_type,
            "status": "queued",
            "created_at_utc": utc_now(),
            "started_at_utc": "",
            "finished_at_utc": "",
            "runtime_seconds": None,
            "payload": safe_payload(payload),
            "logs": [
                {
                    "ts": utc_now(),
                    "level": "info",
                    "message": "Job queued.",
                }
            ],
            "result": None,
            "error": None,
            "source_gis_modified": False,
        }
        self._write_record(record)
        thread = threading.Thread(target=self._run_job, args=(job_id, runner), daemon=True)
        with self._lock:
            self._threads[job_id] = thread
        thread.start()
        return self.detail(job_id)

    def detail(self, job_id: str) -> dict:
        path = self._record_path(job_id)
        if not path.exists():
            return {"error": "job_not_found", "job_id": job_id}
        return read_json(path)

    def list(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(limit, 200))
        records = []
        for path in sorted(self.runs_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            record = read_json(path)
            if not record:
                continue
            records.append(compact_record(record))
            if len(records) >= limit:
                break
        return records

    def _run_job(self, job_id: str, runner) -> None:
        started = datetime.now(timezone.utc)
        record = self.detail(job_id)
        record.update({
            "status": "running",
            "started_at_utc": started.isoformat(),
        })
        append_log(record, "info", "Job started.")
        self._write_record(record)
        try:
            result = runner(record.get("payload", {}), lambda message: self._log(job_id, "info", message))
            finished = datetime.now(timezone.utc)
            record = self.detail(job_id)
            ok = bool(result.get("ok")) if isinstance(result, dict) else False
            record.update({
                "status": "succeeded" if ok else "failed",
                "finished_at_utc": finished.isoformat(),
                "runtime_seconds": round((finished - started).total_seconds(), 3),
                "result": result,
                "error": None if ok else result.get("error", "job_failed") if isinstance(result, dict) else "job_failed",
                "source_gis_modified": False,
            })
            append_log(record, "info" if ok else "error", "Job finished." if ok else "Job failed.")
            self._write_record(record)
        except Exception as exc:  # pragma: no cover - visible local job error
            finished = datetime.now(timezone.utc)
            record = self.detail(job_id)
            record.update({
                "status": "failed",
                "finished_at_utc": finished.isoformat(),
                "runtime_seconds": round((finished - started).total_seconds(), 3),
                "result": None,
                "error": repr(exc),
                "traceback_tail": traceback.format_exc()[-4000:],
                "source_gis_modified": False,
            })
            append_log(record, "error", f"Job raised {type(exc).__name__}.")
            self._write_record(record)
        finally:
            with self._lock:
                self._threads.pop(job_id, None)

    def _log(self, job_id: str, level: str, message: str) -> None:
        record = self.detail(job_id)
        if "error" in record:
            return
        append_log(record, level, message)
        self._write_record(record)

    def _write_record(self, record: dict) -> None:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        path = self._record_path(record["job_id"])
        payload = json.dumps(record, ensure_ascii=False, indent=2)

        # Windows can briefly lock a JSON record while the API polls job status.
        for attempt in range(12):
            temp_path = path.with_suffix(f".{uuid4().hex}.tmp")
            temp_path.write_text(payload, encoding="utf-8")
            try:
                temp_path.replace(path)
                return
            except PermissionError:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
                if attempt == 11:
                    raise
                time.sleep(0.05 * (attempt + 1))

    def _record_path(self, job_id: str) -> Path:
        clean = "".join(ch for ch in str(job_id) if ch.isalnum() or ch in {"_", "-"})
        return self.runs_dir / f"{clean}.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_log(record: dict, level: str, message: str) -> None:
    logs = record.setdefault("logs", [])
    logs.append({
        "ts": utc_now(),
        "level": level,
        "message": message,
    })


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (JSONDecodeError, OSError):
        return {}


def safe_payload(payload: dict) -> dict:
    allowed = {
        "dataset_id",
        "pilot_osm_id",
        "pilot_name",
        "workspace_id",
        "route_workspace_id",
        "route_aware",
    }
    return {key: value for key, value in payload.items() if key in allowed}


def compact_record(record: dict) -> dict:
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    return {
        "job_id": record.get("job_id"),
        "job_type": record.get("job_type"),
        "status": record.get("status"),
        "created_at_utc": record.get("created_at_utc"),
        "started_at_utc": record.get("started_at_utc"),
        "finished_at_utc": record.get("finished_at_utc"),
        "runtime_seconds": record.get("runtime_seconds"),
        "pilot_osm_id": record.get("payload", {}).get("pilot_osm_id"),
        "pilot_name": record.get("payload", {}).get("pilot_name"),
        "active_workspace_id": result.get("active_workspace_id"),
        "error": record.get("error"),
        "source_gis_modified": record.get("source_gis_modified") is True,
        "log_count": len(record.get("logs", [])),
    }
