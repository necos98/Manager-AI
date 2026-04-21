from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.schemas.memory import MemoryDetail, MemoryLinkResponse, MemoryResponse, MemorySearchHit
from app.services.memory_service import MemoryService
from app.services.project_service import ProjectService

project_scoped = APIRouter(prefix="/api/projects/{project_id}/memories", tags=["memories"])
flat = APIRouter(prefix="/api/memories", tags=["memories"])


@project_scoped.get("", response_model=list[MemoryResponse])
async def list_memories(
    project_id: str,
    parent_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    project = await ProjectService(db).get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    svc = MemoryService(db)
    if q:
        hits = await svc.search(project_id=project_id, query=q, limit=limit)
        out: list[MemoryResponse] = []
        for hit in hits:
            counts = await svc.counts(hit["memory"].id)
            out.append(MemoryResponse.from_model(hit["memory"], **counts))
        return out
    rows = await svc.list(project_id=project_id, parent_id=parent_id, limit=limit, offset=offset)
    results: list[MemoryResponse] = []
    for m in rows:
        counts = await svc.counts(m.id)
        results.append(MemoryResponse.from_model(m, **counts))
    return results


@project_scoped.get("/search", response_model=list[MemorySearchHit])
async def search_memories(
    project_id: str,
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = MemoryService(db)
    hits = await svc.search(project_id=project_id, query=q, limit=limit)
    return [
        MemorySearchHit(
            memory=MemoryResponse.from_model(h["memory"], **(await svc.counts(h["memory"].id))),
            snippet=h["snippet"],
            rank=h["rank"],
        )
        for h in hits
    ]


@flat.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    svc = MemoryService(db)
    try:
        bundle = await svc.get_related(memory_id)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    memory = bundle["memory"]
    counts = await svc.counts(memory.id)
    parent = bundle["parent"]
    parent_resp = None
    if parent is not None:
        parent_counts = await svc.counts(parent.id)
        parent_resp = MemoryResponse.from_model(parent, **parent_counts)
    children_resp = []
    for c in bundle["children"]:
        ccounts = await svc.counts(c.id)
        children_resp.append(MemoryResponse.from_model(c, **ccounts))
    return MemoryDetail(
        **MemoryResponse.from_model(memory, **counts).model_dump(),
        parent=parent_resp,
        children=children_resp,
        links_out=[MemoryLinkResponse.model_validate(l, from_attributes=True) for l in bundle["links_out"]],
        links_in=[MemoryLinkResponse.model_validate(l, from_attributes=True) for l in bundle["links_in"]],
    )
