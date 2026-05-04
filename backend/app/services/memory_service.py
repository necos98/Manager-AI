"""File-backed MemoryService.

Memories live in .manager_ai/memories/<id>.md with YAML frontmatter;
memories.yaml is the rollup index. The DB session is kept only to
resolve project.path and to fetch cross-project memories (which
require scanning all projects, same as issue/task services).
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppError
from app.services.project_service import ProjectService
from app.storage import memory_store
from app.storage.memory_store import MemoryLinkRecord, MemoryRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep="T", timespec="microseconds")


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _path_for_project(self, project_id: str) -> str:
        project = await ProjectService(self.session).get_by_id(project_id)
        return project.path

    async def _locate_memory(self, memory_id: str) -> tuple[str, MemoryRecord] | None:
        for project in await ProjectService(self.session).list_all(archived=None):
            rec = memory_store.load_memory(project.path, memory_id)
            if rec is not None:
                return project.path, rec
        return None

    async def create(
        self,
        *,
        project_id: str,
        title: str,
        description: str = "",
        parent_id: str | None = None,
    ) -> MemoryRecord:
        path = await self._path_for_project(project_id)
        if parent_id:
            parent = memory_store.load_memory(path, parent_id)
            if parent is None:
                raise AppError("Parent memory not found", status_code=404)
            if parent.project_id != project_id:
                raise AppError("Parent memory belongs to a different project", status_code=400)

        now = _now_iso()
        record = MemoryRecord(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=title,
            parent_id=parent_id,
            description=description,
            created_at=now,
            updated_at=now,
            links=[],
        )
        memory_store.create_memory(path, record)
        return record

    async def get(self, memory_id: str) -> MemoryRecord:
        located = await self._locate_memory(memory_id)
        if located is None:
            raise AppError("Memory not found", status_code=404)
        return located[1]

    async def list(
        self,
        *,
        project_id: str,
        parent_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MemoryRecord]:
        path = await self._path_for_project(project_id)
        records = [r for r in memory_store.list_memories(path) if r.project_id == project_id]
        if parent_id is not None:
            records = [r for r in records if r.parent_id == (parent_id or None)]
        records.sort(key=lambda r: (r.created_at, r.id))
        return records[offset : offset + limit]

    async def update(
        self,
        memory_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        parent_id: str | None = ...,
    ) -> MemoryRecord:
        located = await self._locate_memory(memory_id)
        if located is None:
            raise AppError("Memory not found", status_code=404)
        path, record = located
        if title is not None:
            record.title = title
        if description is not None:
            record.description = description
        if parent_id is not ...:
            if parent_id is not None:
                if parent_id == memory_id:
                    raise AppError("A memory cannot be its own parent", status_code=400)
                parent = memory_store.load_memory(path, parent_id)
                if parent is None:
                    raise AppError("Parent memory not found", status_code=404)
                if parent.project_id != record.project_id:
                    raise AppError(
                        "Parent memory belongs to a different project", status_code=400
                    )
                if await self._would_create_cycle(
                    path=path, ancestor_id=memory_id, new_parent_id=parent_id
                ):
                    raise AppError("Parent change would create a cycle", status_code=400)
            record.parent_id = parent_id
        record.updated_at = _now_iso()
        memory_store.update_memory(path, record)
        return record

    async def delete(self, memory_id: str) -> None:
        located = await self._locate_memory(memory_id)
        if located is None:
            raise AppError("Memory not found", status_code=404)
        path, _ = located
        memory_store.delete_memory(path, memory_id)

    async def link(self, from_id: str, to_id: str, relation: str = "") -> MemoryLinkRecord:
        if from_id == to_id:
            raise AppError("Cannot link a memory to itself", status_code=400)
        a_loc = await self._locate_memory(from_id)
        b_loc = await self._locate_memory(to_id)
        if a_loc is None or b_loc is None:
            raise AppError("Memory not found", status_code=404)
        path_a, a = a_loc
        path_b, b = b_loc
        if a.project_id != b.project_id:
            raise AppError("Links must stay within one project", status_code=400)
        link = MemoryLinkRecord(to_id=to_id, relation=relation or "", created_at=_now_iso())
        memory_store.add_link(path_a, from_id, link)
        return link

    async def unlink(self, from_id: str, to_id: str, relation: str = "") -> bool:
        a_loc = await self._locate_memory(from_id)
        if a_loc is None:
            return False
        path_a, _ = a_loc
        return memory_store.remove_link(path_a, from_id, to_id, relation or "")

    async def get_related(self, memory_id: str) -> dict[str, Any]:
        located = await self._locate_memory(memory_id)
        if located is None:
            raise AppError("Memory not found", status_code=404)
        path, record = located
        parent = (
            memory_store.load_memory(path, record.parent_id) if record.parent_id else None
        )
        children = [
            m
            for m in memory_store.list_memories_full(path)
            if m.project_id == record.project_id and m.parent_id == memory_id
        ]
        children.sort(key=lambda m: (m.created_at, m.id))
        links_out = [
            _PseudoLink(from_id=memory_id, to_id=l.to_id, relation=l.relation, created_at=l.created_at)
            for l in record.links
        ]
        links_in: list[_PseudoLink] = []
        for m in memory_store.list_memories_full(path):
            for l in m.links:
                if l.to_id == memory_id:
                    links_in.append(
                        _PseudoLink(
                            from_id=m.id, to_id=memory_id, relation=l.relation, created_at=l.created_at
                        )
                    )
        return {
            "memory": record,
            "parent": parent,
            "children": children,
            "links_out": links_out,
            "links_in": links_in,
        }

    async def counts(self, memory_id: str) -> dict[str, int]:
        located = await self._locate_memory(memory_id)
        if located is None:
            return {"children_count": 0, "links_out_count": 0, "links_in_count": 0}
        path, record = located
        children = sum(
            1 for m in memory_store.list_memories(path)
            if m.parent_id == memory_id and m.project_id == record.project_id
        )
        out_count = len(record.links)
        in_count = 0
        for m in memory_store.list_memories_full(path):
            if m.project_id != record.project_id:
                continue
            for l in m.links:
                if l.to_id == memory_id:
                    in_count += 1
        return {
            "children_count": children,
            "links_out_count": out_count,
            "links_in_count": in_count,
        }

    async def search(self, *, project_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Naive in-process scan replacing FTS5. Ranks: title match first, then
        description match, then created_at DESC. Snippet = first match ±40 chars."""
        if not query.strip():
            return []
        path = await self._path_for_project(project_id)
        term = query.lower()
        hits: list[dict[str, Any]] = []
        for record in memory_store.list_memories_full(path):
            if record.project_id != project_id:
                continue
            title_l = record.title.lower()
            desc_l = (record.description or "").lower()
            if term in title_l:
                score = 2.0
                snippet = _snippet(record.title, term)
            elif term in desc_l:
                score = 1.0
                snippet = _snippet(record.description, term)
            else:
                continue
            hits.append({"memory": record, "snippet": snippet, "rank": score})
        hits.sort(key=lambda h: (-h["rank"], -_to_sort_key(h["memory"].created_at)))
        return hits[:limit]

    async def _would_create_cycle(
        self, *, path: str, ancestor_id: str, new_parent_id: str
    ) -> bool:
        visited: set[str] = set()
        current: str | None = new_parent_id
        while current is not None:
            if current == ancestor_id:
                return True
            if current in visited:
                return False
            visited.add(current)
            parent = memory_store.load_memory(path, current)
            current = parent.parent_id if parent else None
        return False


class _PseudoLink:
    """Shape-compatible with old MemoryLink ORM (from_id/to_id/relation/created_at)."""

    def __init__(self, *, from_id: str, to_id: str, relation: str, created_at: Any):
        self.from_id = from_id
        self.to_id = to_id
        self.relation = relation
        self.created_at = _to_datetime(created_at)


def _snippet(text: str, term: str) -> str:
    if not text:
        return ""
    lower = text.lower()
    idx = lower.find(term.lower())
    if idx < 0:
        return text[:80]
    start = max(0, idx - 40)
    end = min(len(text), idx + len(term) + 40)
    s = text[start:end]
    if start > 0:
        s = "…" + s
    if end < len(text):
        s = s + "…"
    return s


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return datetime.min


def _to_sort_key(value: Any) -> float:
    dt = _to_datetime(value)
    return dt.timestamp() if dt != datetime.min else 0.0
