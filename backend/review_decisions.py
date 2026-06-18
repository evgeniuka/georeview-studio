"""Per-candidate reviewer decisions: status / note / assignee, persisted.

Local-first and dependency-free: an embedded SQLite database (Python stdlib
``sqlite3``), not an external server, so it honours the project's "no external
database" rule while still giving durable, transactional, concurrency-safe
storage for the reviewer's actual triage output. Writes are serialised with a
lock so the threaded HTTP server cannot interleave them.

This is the layer that turns the ranked candidate list into a tool a field team
works in: a reviewer can mark a location reviewed / queued / dismissed, attach a
note, and assign it, and the state survives a page reload and process restart.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

REVIEW_STATUSES = ("unreviewed", "to_review", "reviewed", "dismissed")
DEFAULT_STATUS = "unreviewed"
MAX_NOTE_LEN = 4000
MAX_ASSIGNEE_LEN = 200


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReviewDecisionStore:
    """SQLite-backed store of reviewer decisions, keyed by (workspace_id, generator_id)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_decisions (
                    workspace_id TEXT NOT NULL,
                    generator_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unreviewed',
                    note TEXT NOT NULL DEFAULT '',
                    assignee TEXT NOT NULL DEFAULT '',
                    updated_at_utc TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, generator_id)
                )
                """
            )

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "generator_id": row["generator_id"],
            "status": row["status"],
            "note": row["note"],
            "assignee": row["assignee"],
            "updated_at_utc": row["updated_at_utc"],
        }

    @staticmethod
    def _summary(decisions: list) -> dict:
        counts = {status: 0 for status in REVIEW_STATUSES}
        for decision in decisions:
            status = decision.get("status")
            if status in counts:
                counts[status] += 1
        counts["total_recorded"] = len(decisions)
        return counts

    def list_for_workspace(self, workspace_id: str) -> dict:
        workspace_id = str(workspace_id or "")
        if not workspace_id:
            return {"error": "review_decisions_workspace_required"}
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT generator_id, status, note, assignee, updated_at_utc "
                "FROM review_decisions WHERE workspace_id = ? ORDER BY updated_at_utc DESC",
                (workspace_id,),
            ).fetchall()
        decisions = [self._row_to_dict(row) for row in rows]
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "decisions": decisions,
            "summary": self._summary(decisions),
            "statuses": list(REVIEW_STATUSES),
            "source_gis_modified": False,
            "mutates_config": False,
        }

    def set_decision(self, workspace_id: str, body: dict) -> dict:
        workspace_id = str(workspace_id or "")
        generator_id = str(body.get("generator_id") or "").strip()
        if not workspace_id or not generator_id:
            return {"error": "review_decision_target_required"}
        status = str(body.get("status") or DEFAULT_STATUS).strip()
        if status not in REVIEW_STATUSES:
            return {"error": "review_decision_invalid_status", "allowed": list(REVIEW_STATUSES)}
        note = str(body.get("note") or "")[:MAX_NOTE_LEN]
        assignee = str(body.get("assignee") or "")[:MAX_ASSIGNEE_LEN]
        updated_at = _utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO review_decisions "
                "(workspace_id, generator_id, status, note, assignee, updated_at_utc) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (workspace_id, generator_id, status, note, assignee, updated_at),
            )
        return {
            "ok": True,
            "workspace_id": workspace_id,
            "decision": {
                "generator_id": generator_id,
                "status": status,
                "note": note,
                "assignee": assignee,
                "updated_at_utc": updated_at,
            },
            "source_gis_modified": False,
            "mutates_config": False,
        }
