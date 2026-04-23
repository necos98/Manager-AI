"""Filesystem watcher for `.manager_ai/` folders.

Rebuilds root yaml indices (issues.yaml, memories.yaml, files.yaml)
and emits realtime events when anyone — LLM via Write/Edit, another
user via git pull, an external script — mutates the file layout
without going through the backend API.

Debounced (500 ms) per project+area so atomic temp→rename bursts
collapse into a single rebuild.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.services.event_service import event_service
from app.storage import file_store, issue_store, memory_store, paths

logger = logging.getLogger(__name__)

_DEBOUNCE_SECONDS = 0.5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _Handler(FileSystemEventHandler):
    def __init__(self, *, project_id: str, project_path: str, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.project_id = project_id
        self.project_path = project_path
        self.loop = loop
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if getattr(event, "is_directory", False):
            return
        # Atomic writes emit a "moved" event from <final>.tmp → <final>. The
        # effective path is dest_path when present, src_path otherwise.
        raw = getattr(event, "dest_path", "") or event.src_path
        path = Path(raw)
        if path.suffix not in {".md", ".yaml", ".txt"}:
            return
        area = self._classify(path)
        if area is None:
            return
        self._schedule(area)

    def _classify(self, path: Path) -> str | None:
        root = paths.manager_ai_root(self.project_path)
        try:
            relative = path.resolve().relative_to(root.resolve())
        except (ValueError, OSError):
            return None
        parts = relative.parts
        if not parts:
            return None
        if parts[0] in {"issues", "issues.yaml"}:
            return "issues"
        if parts[0] in {"memories", "memories.yaml"}:
            return "memories"
        if parts[0] in {"files", "files.yaml"}:
            return "files"
        return None

    def _schedule(self, area: str) -> None:
        with self._lock:
            existing = self._timers.pop(area, None)
            if existing is not None:
                existing.cancel()
            timer = threading.Timer(_DEBOUNCE_SECONDS, self._flush, args=(area,))
            timer.daemon = True
            self._timers[area] = timer
            timer.start()

    def _flush(self, area: str) -> None:
        try:
            if area == "issues":
                issue_store.rebuild_issues_index(self.project_path)
                event_type = "issue_updated"
            elif area == "memories":
                memory_store.rebuild_memories_index(self.project_path)
                event_type = "memory_updated"
            elif area == "files":
                file_store.rebuild_files_index(self.project_path)
                event_type = "file_updated"
            else:
                return
        except Exception:
            logger.exception("Rebuilding %s index failed for project %s", area, self.project_id)
            return

        coro = event_service.emit(
            {
                "type": event_type,
                "project_id": self.project_id,
                "source": "fs_watcher",
                "timestamp": _now_iso(),
            }
        )
        asyncio.run_coroutine_threadsafe(coro, self.loop)


class ManagerAiWatcher:
    def __init__(self) -> None:
        self._observers: dict[str, Observer] = {}
        self._lock = asyncio.Lock()

    async def start_project(self, project_id: str, project_path: str) -> None:
        async with self._lock:
            if project_id in self._observers:
                return
            root = paths.manager_ai_root(project_path)
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.warning("Cannot create %s, skipping watcher", root)
                return
            loop = asyncio.get_running_loop()
            handler = _Handler(
                project_id=project_id, project_path=project_path, loop=loop
            )
            observer = Observer()
            observer.schedule(handler, str(root), recursive=True)
            observer.daemon = True
            observer.start()
            self._observers[project_id] = observer
            logger.info("Watcher started for project %s at %s", project_id, root)

    async def stop_project(self, project_id: str) -> None:
        async with self._lock:
            obs = self._observers.pop(project_id, None)
            if obs is None:
                return
            obs.stop()
            obs.join(timeout=2.0)

    async def stop_all(self) -> None:
        ids = list(self._observers.keys())
        for pid in ids:
            await self.stop_project(pid)


manager_ai_watcher = ManagerAiWatcher()
