"""Filesystem watcher for `.manager_ai/` folders.

Rebuilds root yaml indices (issues.yaml, memories.yaml, files.yaml)
and emits realtime events when anyone — LLM via Write/Edit, another
user via git pull, an external script — mutates the file layout
without going through the backend API.

Debounced (500 ms) per project+area so atomic temp→rename bursts
collapse into a single rebuild.

Uses ``watchfiles`` (Rust ``notify`` crate) for async-native,
thread-free filesystem events — avoids Python 3.14 ``parking_lot``
semaphore bugs present in threaded ``watchdog``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from watchfiles import Change, awatch

from app.services.event_service import event_service
from app.storage import file_store, issue_store, memory_store, paths

logger = logging.getLogger(__name__)

_DEBOUNCE_SECONDS = 0.5
_AWATCH_DEBOUNCE_MS = 200

_TARGET_SUFFIXES = {".md", ".yaml", ".txt"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify(path: Path, root: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    parts = relative.parts
    if not parts:
        return None
    if parts[0] == "issues" and len(parts) > 1:
        return "issues"
    if parts[0] == "memories" and len(parts) > 1:
        return "memories"
    if parts[0] == "files" and len(parts) > 1:
        return "files"
    if parts[0] == "plugins.yaml":
        return "plugins"
    return None


def _watch_filter(change: Change, path_str: str) -> bool:
    return Path(path_str).suffix in _TARGET_SUFFIXES


class ManagerAiWatcher:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_project(
        self, project_id: str, project_path: str, mcp=None, plugin_manager=None
    ) -> None:
        async with self._lock:
            if project_id in self._tasks:
                return
            # Skip if project is archived — no watcher, no index rebuild.
            if await self._is_archived(project_id):
                logger.info("Project %s is archived, skipping watcher + index rebuild", project_id)
                return
            root = paths.manager_ai_root(project_path)
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.warning("Cannot create %s, skipping watcher", root)
                return
            # Regenerate index YAMLs on every startup.
            logger.info("Rebuilding indices for project %s", project_id)
            issue_count = issue_store.rebuild_issues_index(project_path)
            issue_store.invalidate_issue_cache(project_path)
            memory_count = memory_store.rebuild_memories_index(project_path)
            memory_store.invalidate_memory_cache(project_path)
            file_count = file_store.rebuild_files_index(project_path)
            file_store.invalidate_file_cache(project_path)
            logger.info(
                "Indices rebuilt for project %s: %d issues, %d memories, %d files",
                project_id, issue_count, memory_count, file_count,
            )

            task = asyncio.create_task(
                self._watch_project(
                    project_id, project_path, root, mcp, plugin_manager,
                )
            )
            self._tasks[project_id] = task
            logger.info("Watcher started for project %s at %s", project_id, root)

    @staticmethod
    async def _is_archived(project_id: str) -> bool:
        from app.database import async_session
        from sqlalchemy import select
        from app.models.project import Project
        async with async_session() as session:
            result = await session.execute(
                select(Project.archived_at).where(Project.id == project_id)
            )
            row = result.scalar_one_or_none()
            return row is not None

    async def _watch_project(
        self,
        project_id: str,
        project_path: str,
        root: Path,
        mcp,
        plugin_manager,
    ) -> None:
        debounce_tasks: dict[str, asyncio.Task] = {}
        debounce_lock = asyncio.Lock()

        async def flush(area: str) -> None:
            try:
                if area == "issues":
                    await asyncio.to_thread(issue_store.rebuild_issues_index, project_path)
                    await asyncio.to_thread(issue_store.invalidate_issue_cache, project_path)
                    event_type = "issue_updated"
                elif area == "memories":
                    await asyncio.to_thread(memory_store.rebuild_memories_index, project_path)
                    await asyncio.to_thread(memory_store.invalidate_memory_cache, project_path)
                    event_type = "memory_updated"
                elif area == "files":
                    await asyncio.to_thread(file_store.rebuild_files_index, project_path)
                    await asyncio.to_thread(file_store.invalidate_file_cache, project_path)
                    event_type = "file_updated"
                elif area == "plugins":
                    if plugin_manager and mcp:
                        await self._reload_plugins(project_id, project_path, mcp, plugin_manager)
                    return
                else:
                    return
            except Exception:
                logger.exception("Rebuilding %s index failed for project %s", area, project_id)
                return

            try:
                await event_service.emit({
                    "type": event_type,
                    "project_id": project_id,
                    "source": "fs_watcher",
                    "timestamp": _now_iso(),
                })
            except Exception:
                pass

        try:
            async for changes in awatch(root, debounce=_AWATCH_DEBOUNCE_MS, watch_filter=_watch_filter):
                for _change_type, path_str in changes:
                    area = _classify(Path(path_str), root)
                    if area is None:
                        continue
                    async with debounce_lock:
                        existing = debounce_tasks.pop(area, None)
                        if existing and not existing.done():
                            existing.cancel()
                        debounce_tasks[area] = asyncio.create_task(
                            self._debounced_flush(area, flush)
                        )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Watcher for project %s crashed, restarting soon", project_id)

    @staticmethod
    async def _debounced_flush(area: str, flush_fn) -> None:
        try:
            await asyncio.sleep(_DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            return
        await flush_fn(area)

    async def _reload_plugins(
        self, project_id: str, project_path: str, mcp, plugin_manager
    ) -> None:
        try:
            from app.mcp.plugin_config import load_plugins as load_plugins_cfg
            config = load_plugins_cfg(project_path)
            current = plugin_manager._state.get(project_id, {})

            for key in list(current.keys()):
                proj_cfg = config.plugins.get(key)
                if proj_cfg is None or not proj_cfg.enabled:
                    await plugin_manager.disable_plugin(
                        project_id, project_path, key, mcp
                    )

            for key, proj_cfg in config.plugins.items():
                if not proj_cfg.enabled:
                    continue
                existing = current.get(key)
                if existing is None:
                    await plugin_manager.enable_plugin(
                        project_id, project_path, key, mcp
                    )
        except Exception:
            logger.exception("Plugin reload failed for project %s", project_id)

    async def stop_project(self, project_id: str) -> None:
        async with self._lock:
            task = self._tasks.pop(project_id, None)
            if task is None:
                return
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def stop_all(self) -> None:
        ids = list(self._tasks.keys())
        for pid in ids:
            await self.stop_project(pid)


manager_ai_watcher = ManagerAiWatcher()
