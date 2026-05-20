from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class WriteQueue:
    """Durable SQLite-backed write queue. Survives process crashes.

    Pending writes are replayed on next startup if the BackgroundWriter
    doesn't get to flush them before shutdown.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute(
                """CREATE TABLE IF NOT EXISTS pending_writes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT NOT NULL,
                    store_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0
                )"""
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_pending_sort ON pending_writes(id)"
            )
            self._conn.commit()
        return self._conn

    def enqueue(
        self,
        project_path: str,
        store_type: str,
        record_id: str,
        action: str,
        payload: Any,
        now: str,
    ) -> None:
        conn = self._ensure_conn()
        payload_json = json.dumps(payload, default=str) if payload is not None else None
        conn.execute(
            "DELETE FROM pending_writes WHERE project_path=? AND store_type=? AND record_id=?",
            (project_path, store_type, record_id),
        )
        conn.execute(
            "INSERT INTO pending_writes (project_path, store_type, record_id, action, payload_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_path, store_type, record_id, action, payload_json, now),
        )
        conn.commit()

    def dequeue_batch(self, limit: int = 10) -> list[dict[str, Any]]:
        conn = self._ensure_conn()
        rows = conn.execute(
            "SELECT * FROM pending_writes ORDER BY id LIMIT ?", (limit,)
        ).fetchall()
        return [{k: r[k] for k in r.keys()} for r in rows]

    def remove(self, row_id: int) -> None:
        conn = self._ensure_conn()
        conn.execute("DELETE FROM pending_writes WHERE id=?", (row_id,))
        conn.commit()

    def increment_retry(self, row_id: int) -> int:
        conn = self._ensure_conn()
        conn.execute(
            "UPDATE pending_writes SET retry_count = retry_count + 1 WHERE id=?",
            (row_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT retry_count FROM pending_writes WHERE id=?", (row_id,)
        ).fetchone()
        return row[0] if row else 0

    def count_pending(self) -> int:
        conn = self._ensure_conn()
        row = conn.execute("SELECT COUNT(*) FROM pending_writes").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
