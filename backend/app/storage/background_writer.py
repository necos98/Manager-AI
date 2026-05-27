from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.storage.write_queue import WriteQueue

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class BackgroundWriter:
    """Async worker that drains the write queue to disk.

    Reads batches from WriteQueue, calls the low-level disk write helpers
    in each store module, and rebuilds index YAML files. Never blocks
    the caller — writes are fire-and-forget from the API perspective.
    """

    def __init__(self, write_queue: WriteQueue) -> None:
        self._queue = write_queue
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._flush_remaining()

    def ensure_running(self) -> None:
        if not self._running:
            asyncio.create_task(self.start())

    async def _loop(self) -> None:
        while self._running:
            batch = self._queue.dequeue_batch(limit=10)
            if not batch:
                await asyncio.sleep(0.5)
                continue
            for row in batch:
                try:
                    self._process(row)
                    self._queue.remove(row["id"])
                except Exception:
                    retries = self._queue.increment_retry(row["id"])
                    if retries >= MAX_RETRIES:
                        logger.error(
                            "Write failed after %d retries: %s/%s/%s",
                            MAX_RETRIES,
                            row["store_type"],
                            row["record_id"],
                            row["action"],
                        )
                        self._queue.remove(row["id"])
                        self._emit_write_failed(row)
                    else:
                        logger.warning(
                            "Write retry %d for %s/%s",
                            retries,
                            row["store_type"],
                            row["record_id"],
                        )

    def _process(self, row: dict[str, Any]) -> None:
        project_path = row["project_path"]
        store_type = row["store_type"]
        record_id = row["record_id"]
        action = row["action"]

        if action == "delete":
            delete_from_disk(project_path, store_type, record_id)
        elif action == "upsert":
            payload = json.loads(row["payload_json"]) if row["payload_json"] else None
            if payload is not None:
                _write_to_disk(project_path, store_type, record_id, payload)

        rebuild_index_for(project_path, store_type)

    async def _flush_remaining(self) -> None:
        batch = self._queue.dequeue_batch(limit=100)
        for row in batch:
            try:
                self._process(row)
                self._queue.remove(row["id"])
            except Exception:
                logger.exception(
                    "Flush failed for %s/%s", row["store_type"], row["record_id"]
                )

    def _emit_write_failed(self, row: dict[str, Any]) -> None:
        try:
            from app.services.event_service import event_service

            asyncio.create_task(
                event_service.emit(
                    {
                        "type": "write_failed",
                        "project_id": "",
                        "store_type": row.get("store_type", ""),
                        "record_id": row.get("record_id", ""),
                        "source": "background_writer",
                    }
                )
            )
        except Exception:
            pass


# -- low-level disk helpers ------------------------------------------------
# These call the private write/delete/rebuild functions in each store module.
# They exist here (not in the store modules) to avoid circular imports
# between store modules and BackgroundWriter.


def _write_to_disk(
    project_path: str, store_type: str, record_id: str, payload: dict[str, Any]
) -> None:
    if store_type == "memories":
        from app.storage.memory_store import _write_memory_record

        _write_memory_record(project_path, payload)
    elif store_type == "issues":
        from app.storage.issue_store import _write_issue_record

        _write_issue_record(project_path, payload)
    elif store_type == "files":
        from app.storage.file_store import _write_file_record

        _write_file_record(project_path, payload)


def delete_from_disk(project_path: str, store_type: str, record_id: str) -> None:
    from app.storage import atomic, paths

    if store_type == "memories":
        atomic.remove_if_exists(paths.memory_md(project_path, record_id))
    elif store_type == "issues":
        import shutil

        folder = paths.issue_dir(project_path, record_id)
        if folder.exists():
            shutil.rmtree(folder)
    elif store_type == "files":
        atomic.remove_if_exists(paths.file_text_cache(project_path, record_id))


def flush_all_pending(write_queue: WriteQueue) -> int:
    """Process all pending writes synchronously. For tests and shutdown."""
    count = 0
    while True:
        batch = write_queue.dequeue_batch(limit=100)
        if not batch:
            break
        for row in batch:
            try:
                if row["action"] == "delete":
                    delete_from_disk(row["project_path"], row["store_type"], row["record_id"])
                elif row["action"] == "upsert":
                    payload = json.loads(row["payload_json"]) if row["payload_json"] else None
                    if payload is not None:
                        _write_to_disk(row["project_path"], row["store_type"], row["record_id"], payload)
                rebuild_index_for(row["project_path"], row["store_type"])
                write_queue.remove(row["id"])
                count += 1
            except Exception:
                logger.exception("Flush failed for %s/%s", row["store_type"], row["record_id"])
    return count


def rebuild_index_for(project_path: str, store_type: str) -> None:
    if store_type == "memories":
        from app.storage.memory_store import rebuild_memories_index

        rebuild_memories_index(project_path)
    elif store_type == "issues":
        from app.storage.issue_store import rebuild_issues_index

        rebuild_issues_index(project_path)
    elif store_type == "files":
        from app.storage.file_store import rebuild_files_index

        rebuild_files_index(project_path)
