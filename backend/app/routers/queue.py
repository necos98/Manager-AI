"""
Global queue status endpoints — aggregated across all projects.

- GET /api/queue         — all QUEUED issues (global FIFO)
- GET /api/queue/running — all issues with active terminals
- GET /api/queue/status  — aggregate counts + pause state
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.models.issue import IssueStatus
from app.models.queue_entry import QueueEntry, QueueEntryStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.settings_service import SettingsService
from app.services.terminal_service import TerminalService, terminal_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/queue", tags=["queue"])


# ── Schemas ──────────────────────────────────────────────────────────────

class QueuedIssueItem(BaseModel):
    position: int
    issue_id: str
    issue_name: str
    issue_description: str
    project_id: str
    project_name: str
    created_at: str


class RunningIssueItem(BaseModel):
    issue_id: str
    issue_name: str | None
    project_id: str
    project_name: str | None
    terminal_id: str
    issue_status: str | None
    started_at: str | None


class QueueStatus(BaseModel):
    queued_count: int
    running_count: int
    dispatching_count: int
    paused: bool
    auto_process_enabled: bool


class SetAutoProcessRequest(BaseModel):
    enabled: bool


class QueueResponse(BaseModel):
    queued: list[QueuedIssueItem]
    total: int


class RunningResponse(BaseModel):
    running: list[RunningIssueItem]
    total: int


# ── Helpers ──────────────────────────────────────────────────────────────

def get_terminal_service() -> TerminalService:
    return terminal_service


# ── Endpoints ────────────────────────────────────────────────────────────

@router.get("", response_model=QueueResponse)
async def list_global_queue(
    db: AsyncSession = Depends(get_db),
):
    """Return all pending queue entries across all projects, ordered by QueueEntry.order ASC.

    Uses the persistent QueueEntry table instead of IssueStatus.QUEUED.
    """
    from sqlalchemy import select

    issue_service = IssueService(db)
    project_service = ProjectService(db)

    # Query pending QueueEntries across all projects
    result = await db.execute(
        select(QueueEntry)
        .where(QueueEntry.status == QueueEntryStatus.PENDING)
        .order_by(QueueEntry.order.asc())
    )
    entries = result.scalars().all()

    all_queued: list[QueuedIssueItem] = []
    project_cache: dict[str, str] = {}

    for entry in entries:
        # Look up issue details
        issue = await issue_service.get_by_id(entry.issue_id)
        if issue is None:
            continue

        # Cache project name
        if entry.project_id not in project_cache:
            project = await project_service.get_by_id(entry.project_id)
            project_cache[entry.project_id] = project.name if project else ""

        all_queued.append(
            QueuedIssueItem(
                position=0,  # set below
                issue_id=entry.issue_id,
                issue_name=issue.name or "",
                issue_description=(issue.description or "")[:120],
                project_id=entry.project_id,
                project_name=project_cache.get(entry.project_id, ""),
                created_at=entry.created_at.isoformat() if entry.created_at else "",
            )
        )

    # Assign 1-based FIFO positions
    for idx, item in enumerate(all_queued, start=1):
        item.position = idx

    return QueueResponse(queued=all_queued, total=len(all_queued))


@router.get("/running", response_model=RunningResponse)
async def list_global_running(
    db: AsyncSession = Depends(get_db),
    svc: TerminalService = Depends(get_terminal_service),
):
    """Return all issues currently running (active terminals) across all projects."""
    issue_service = IssueService(db)

    terminals = svc.list_active()
    # Filter out standalone terminals (no project/issue)
    terminals = [
        t
        for t in terminals
        if t.get("project_id") and t.get("issue_id")
    ]

    # Build project name map
    project_ids = {t["project_id"] for t in terminals if t.get("project_id")}
    project_service = ProjectService(db)
    projects = await project_service.list_all(archived=False)
    project_map = {p.id: p.name for p in projects}

    items: list[RunningIssueItem] = []
    for term in terminals:
        project_id = term["project_id"]
        issue_id = term["issue_id"]

        # Get issue name + status
        issue = await issue_service.get_by_id(issue_id)
        issue_name = issue.name if issue else None
        issue_status = issue.status if issue else None

        items.append(
            RunningIssueItem(
                issue_id=issue_id,
                issue_name=issue_name,
                project_id=project_id,
                project_name=project_map.get(project_id),
                terminal_id=term["id"],
                issue_status=issue_status,
                started_at=term.get("started_at"),
            )
        )

    return RunningResponse(running=items, total=len(items))


@router.get("/status", response_model=QueueStatus)
async def get_queue_status(
    db: AsyncSession = Depends(get_db),
    svc: TerminalService = Depends(get_terminal_service),
):
    """Return aggregate queue status (counts + pause state).

    Uses QueueEntry table instead of IssueStatus.QUEUED for queued count.
    """
    from sqlalchemy import select, func as sa_func
    from app.models.queue_entry import QueueEntry, QueueEntryStatus

    settings_service = SettingsService(db)

    # Count pending QueueEntries across all projects
    result = await db.execute(
        select(sa_func.count(QueueEntry.id))
        .where(QueueEntry.status == QueueEntryStatus.PENDING)
    )
    queued_count: int = result.scalar() or 0

    running_count = sum(
        1
        for t in svc.list_active()
        if t.get("project_id") and t.get("issue_id")
    )

    # Count dispatching QueueEntries (in the process of being dispatched)
    result = await db.execute(
        select(sa_func.count(QueueEntry.id))
        .where(QueueEntry.status == QueueEntryStatus.DISPATCHING)
    )
    dispatching_count: int = result.scalar() or 0

    paused_str = await settings_service.get("work_queue_paused")
    paused = paused_str.lower() == "true" if paused_str else False

    auto_process_str = await settings_service.get("queue_auto_process")
    auto_process_enabled = auto_process_str.lower() == "true" if auto_process_str else False

    return QueueStatus(
        queued_count=queued_count,
        running_count=running_count,
        dispatching_count=dispatching_count,
        paused=paused,
        auto_process_enabled=auto_process_enabled,
    )


@router.post("/auto-process")
async def set_auto_process(
    body: SetAutoProcessRequest,
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable automatic queue processing.

    Persists the ``queue_auto_process`` setting and updates the in-memory
    state of the running ``IssueQueueService`` singleton.
    """
    svc = SettingsService(db)
    await svc.set("queue_auto_process", "true" if body.enabled else "false")
    await db.commit()

    from app.services.issue_queue_service import issue_queue_service_ref
    if issue_queue_service_ref is not None:
        await issue_queue_service_ref.set_enabled(body.enabled)

    return {"enabled": body.enabled}


# ── Individual queue operations ──────────────────────────────────────────────


class QueueAddRequest(BaseModel):
    project_id: str
    issue_id: str


class QueueRemoveRequest(BaseModel):
    project_id: str
    issue_id: str


@router.post("/add")
async def add_to_queue(
    body: QueueAddRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add an issue to the FIFO queue.

    Delegates to ``IssueQueueService.add_to_queue()`` for the
    shared validation and event emission logic.
    """
    from app.services.issue_queue_service import issue_queue_service_ref
    from app.services.issue_queue_service import _queue_add_direct

    if issue_queue_service_ref is not None:
        result = await issue_queue_service_ref.add_to_queue(db, body.project_id, body.issue_id)
        return {**result, "message": "Issue added to queue"}

    # Fallback when IssueQueueService is not initialized
    result = await _queue_add_direct(db, body.project_id, body.issue_id)
    return {**result, "message": "Issue added to queue"}
        result = await registry.add_to_queue(db, body.project_id, body.issue_id)
    except AppError as e:
        raise HTTPException(status_code=400, detail=e.message)

    return {
        **result,
        "message": "Issue added to queue",
    }


@router.post("/remove")
async def remove_from_queue(
    body: QueueRemoveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Remove an issue from the FIFO queue.

    Delegates to ``IssueQueueService.remove_from_queue()`` for the
    shared queue membership check and event emission logic.
    """
    from app.services.issue_queue_service import issue_queue_service_ref
    from app.services.issue_queue_service import _queue_remove_direct

    if issue_queue_service_ref is not None:
        result = await issue_queue_service_ref.remove_from_queue(db, body.project_id, body.issue_id)
        return {**result, "message": "Issue removed from queue"}

    # Fallback when IssueQueueService is not initialized
    result = await _queue_remove_direct(db, body.project_id, body.issue_id)
    return {**result, "message": "Issue removed from queue"}
        result = await registry.remove_from_queue(db, body.project_id, body.issue_id)
    except AppError as e:
        raise HTTPException(status_code=404, detail=e.message)

    return {
        **result,
        "message": "Issue removed from queue",
    }


@router.get("/position/{issue_id}")
async def get_queue_position(
    issue_id: str,
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the 1-based FIFO queue position for a specific issue.

    Returns ``{position, issue_id, in_queue, status}``.
    ``position`` is null when the issue is not in the queue.
    """
    from app.services.issue_queue_service import issue_queue_service_ref
    registry = issue_queue_service_ref
    if registry is None:
        raise HTTPException(
            status_code=503,
            detail="Queue service not initialized",
        )
    entries = await registry.list_queue(project_id)

    # Filter to pending entries only
    pending = [e for e in entries if e["status"] == "pending"]

    for idx, entry in enumerate(pending):
        if entry["issue_id"] == issue_id:
            return {
                "position": idx + 1,
                "issue_id": issue_id,
                "in_queue": True,
                "status": "pending",
            }

    # Check if there's any QueueEntry at all (already dispatched/failed)
    all_entries = [e for e in entries if e["issue_id"] == issue_id]
    if all_entries:
        return {
            "position": None,
            "issue_id": issue_id,
            "in_queue": False,
            "status": all_entries[0]["status"],
        }

    return {
        "position": None,
        "issue_id": issue_id,
        "in_queue": False,
        "status": "no_entry",
    }
