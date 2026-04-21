from __future__ import annotations

from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppError
from app.models.memory import Memory, MemoryLink


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, project_id: str, title: str, description: str = "", parent_id: str | None = None) -> Memory:
        if parent_id:
            parent = await self.session.get(Memory, parent_id)
            if parent is None:
                raise AppError("Parent memory not found", status_code=404)
            if parent.project_id != project_id:
                raise AppError("Parent memory belongs to a different project", status_code=400)
        memory = Memory(project_id=project_id, title=title, description=description, parent_id=parent_id)
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get(self, memory_id: str) -> Memory:
        memory = await self.session.get(Memory, memory_id)
        if memory is None:
            raise AppError("Memory not found", status_code=404)
        return memory

    async def list(self, *, project_id: str, parent_id: str | None = None, limit: int = 50, offset: int = 0) -> list[Memory]:
        stmt = select(Memory).where(Memory.project_id == project_id)
        if parent_id is not None:
            stmt = stmt.where(Memory.parent_id == parent_id)
        stmt = stmt.order_by(Memory.created_at).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(self, memory_id: str, *, title: str | None = None, description: str | None = None, parent_id: str | None = ..., ) -> Memory:
        memory = await self.get(memory_id)
        if title is not None:
            memory.title = title
        if description is not None:
            memory.description = description
        if parent_id is not ...:
            if parent_id is not None:
                if parent_id == memory_id:
                    raise AppError("A memory cannot be its own parent", status_code=400)
                parent = await self.session.get(Memory, parent_id)
                if parent is None:
                    raise AppError("Parent memory not found", status_code=404)
                if parent.project_id != memory.project_id:
                    raise AppError("Parent memory belongs to a different project", status_code=400)
                if await self._would_create_cycle(ancestor_id=memory_id, new_parent_id=parent_id):
                    raise AppError("Parent change would create a cycle", status_code=400)
            memory.parent_id = parent_id
        await self.session.flush()
        return memory

    async def delete(self, memory_id: str) -> None:
        memory = await self.get(memory_id)
        await self.session.delete(memory)
        await self.session.flush()

    async def link(self, from_id: str, to_id: str, relation: str = "") -> MemoryLink:
        if from_id == to_id:
            raise AppError("Cannot link a memory to itself", status_code=400)
        a = await self.get(from_id)
        b = await self.get(to_id)
        if a.project_id != b.project_id:
            raise AppError("Links must stay within one project", status_code=400)
        link = MemoryLink(from_id=from_id, to_id=to_id, relation=relation or "")
        self.session.add(link)
        await self.session.flush()
        return link

    async def unlink(self, from_id: str, to_id: str, relation: str = "") -> bool:
        stmt = select(MemoryLink).where(
            MemoryLink.from_id == from_id,
            MemoryLink.to_id == to_id,
            MemoryLink.relation == (relation or ""),
        )
        link = (await self.session.execute(stmt)).scalar_one_or_none()
        if link is None:
            return False
        await self.session.delete(link)
        await self.session.flush()
        return True

    async def get_related(self, memory_id: str) -> dict[str, Any]:
        memory = await self.get(memory_id)
        parent = await self.session.get(Memory, memory.parent_id) if memory.parent_id else None
        children = list((await self.session.execute(
            select(Memory).where(Memory.parent_id == memory_id).order_by(Memory.created_at)
        )).scalars().all())
        links_out = list((await self.session.execute(
            select(MemoryLink).where(MemoryLink.from_id == memory_id)
        )).scalars().all())
        links_in = list((await self.session.execute(
            select(MemoryLink).where(MemoryLink.to_id == memory_id)
        )).scalars().all())
        return {"memory": memory, "parent": parent, "children": children, "links_out": links_out, "links_in": links_in}

    async def counts(self, memory_id: str) -> dict[str, int]:
        children = (await self.session.execute(select(func.count()).select_from(Memory).where(Memory.parent_id == memory_id))).scalar_one()
        out = (await self.session.execute(select(func.count()).select_from(MemoryLink).where(MemoryLink.from_id == memory_id))).scalar_one()
        inn = (await self.session.execute(select(func.count()).select_from(MemoryLink).where(MemoryLink.to_id == memory_id))).scalar_one()
        return {"children_count": children, "links_out_count": out, "links_in_count": inn}

    async def search(self, *, project_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        sql = text(
            "SELECT m.id, bm25(memories_fts) AS rank, "
            "snippet(memories_fts, -1, '[', ']', '…', 10) AS snippet "
            "FROM memories_fts f JOIN memories m ON m.rowid = f.rowid "
            "WHERE memories_fts MATCH :q AND m.project_id = :pid "
            "ORDER BY rank LIMIT :lim"
        )
        rows = (await self.session.execute(sql, {"q": query, "pid": project_id, "lim": limit})).all()
        hits: list[dict[str, Any]] = []
        for row in rows:
            memory = await self.session.get(Memory, row.id)
            if memory is not None:
                hits.append({"memory": memory, "snippet": row.snippet or "", "rank": float(row.rank)})
        return hits

    async def _would_create_cycle(self, *, ancestor_id: str, new_parent_id: str) -> bool:
        current: str | None = new_parent_id
        visited: set[str] = set()
        while current is not None:
            if current == ancestor_id:
                return True
            if current in visited:
                return False
            visited.add(current)
            parent = await self.session.get(Memory, current)
            current = parent.parent_id if parent else None
        return False
