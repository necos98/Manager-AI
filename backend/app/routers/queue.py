"""
Global queue status endpoints — aggregated across all projects.

- GET /api/queue         — all QUEUED issues (global FIFO)
- GET /api/queue/running — all issues with active terminals
- GET /api/queue/status  — aggregate counts + pause state
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.issue import IssueStatus
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
    paused: bool


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
    """Return all QUEUED issues across all non-archived projects, ordered by created_at ASC."""
    issue_service = IssueService(db)
    project_service = ProjectService(db)

    projects = await project_service.list_all(archived=False)

    all_queued: list[QueuedIssueItem] = []

    for project in projects:
        issues = await issue_service.list_by_project(
            project.id,
            status=IssueStatus.QUEUED,
        )
        for issue in issues:
            all_queued.append(
                QueuedIssueItem(
                    position=0,  # set below
                    issue_id=issue.id,
                    issue_name=issue.name or "",
                    issue_description=(issue.description or "")[:120],
                    project_id=project.id,
                    project_name=project.name,
                    created_at=issue.created_at,
                )
            )

    # Sort globally by created_at ASC (FIFO)
    all_queued.sort(key=lambda i: i.created_at)

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
                terminal_id=term["terminal_id"],
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
    """Return aggregate queue status (counts + pause state)."""
    issue_service = IssueService(db)
    project_service = ProjectService(db)
    settings_service = SettingsService(db)

    projects = await project_service.list_all(archived=False)

    queued_count = 0
    for project in projects:
        issues = await issue_service.list_by_project(
            project.id,
            status=IssueStatus.QUEUED,
        )
        queued_count += len(issues)

    running_count = sum(
        1
        for t in svc.list_active()
        if t.get("project_id") and t.get("issue_id")
    )

    paused_str = await settings_service.get("work_queue_paused")
    paused = paused_str.lower() == "true" if paused_str else False

    return QueueStatus(
        queued_count=queued_count,
        running_count=running_count,
        paused=paused,
    )
