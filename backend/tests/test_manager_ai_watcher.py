from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio

from app.services import event_service as event_service_mod
from app.services.manager_ai_watcher import ManagerAiWatcher
from app.storage import atomic, memory_store, paths
from app.storage.memory_store import MemoryRecord


@pytest_asyncio.fixture
async def watcher_with_project(tmp_path, monkeypatch):
    captured: list[dict] = []

    async def fake_emit(event):
        captured.append(event)

    monkeypatch.setattr(event_service_mod.event_service, "emit", fake_emit)

    watcher = ManagerAiWatcher()
    await watcher.start_project("proj-w", str(tmp_path))
    try:
        yield watcher, str(tmp_path), captured
    finally:
        await watcher.stop_all()


async def test_watcher_rebuilds_memories_index(watcher_with_project):
    watcher, project_path, captured = watcher_with_project

    record = MemoryRecord(
        id="m-ext",
        project_id="proj-w",
        title="External",
        parent_id=None,
        description="Written by external process",
        created_at="2026-04-23T10:00:00",
        updated_at="2026-04-23T10:00:00",
        links=[],
    )
    # Bypass service layer: write only the .md, no index update.
    memory_store._write_memory_file(project_path, record)  # type: ignore[attr-defined]

    # Wait for debounce (500ms) + safety margin
    await asyncio.sleep(1.2)

    data = atomic.read_yaml(paths.memories_index(project_path))
    ids = [e["id"] for e in (data.get("memories") or [])]
    assert "m-ext" in ids, f"Expected m-ext in rebuilt index, got {ids}"

    assert any(ev.get("type") == "memory_updated" for ev in captured)


async def test_watcher_ignores_tmp_files(watcher_with_project):
    watcher, project_path, captured = watcher_with_project
    initial = len(captured)

    tmp = paths.memories_dir(project_path) / "x.md.tmp"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("stale", encoding="utf-8")

    await asyncio.sleep(1.0)
    # *.tmp create should not trigger an event
    assert len(captured) == initial
