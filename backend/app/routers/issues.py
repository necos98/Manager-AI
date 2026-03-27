from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import InvalidTransitionError
from app.models.issue import Issue, IssueStatus
from app.schemas.issue import IssueCreate, IssueCompleteBody, IssueResponse, IssueStatusUpdate, IssueUpdate
from app.services.issue_service import IssueService

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


async def _reload_with_tasks(db: AsyncSession, issue_id: str) -> Issue:
    result = await db.execute(
        select(Issue).options(selectinload(Issue.tasks)).where(Issue.id == issue_id)
    )
    return result.scalar_one()


@router.post("", response_model=IssueResponse, status_code=201)
async def create_issue(project_id: str, data: IssueCreate, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    issue = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.get("", response_model=list[IssueResponse])
async def list_issues(
    project_id: str,
    status: IssueStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    return await service.list_by_project(project_id, status=status)


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    return await service.get_for_project(issue_id, project_id)


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    project_id: str, issue_id: str, data: IssueUpdate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.update_fields(issue_id, project_id, **data.model_dump(exclude_unset=True))
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.patch("/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(
    project_id: str,
    issue_id: str,
    data: IssueStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    issue = await service.update_status(issue_id, project_id, data.status)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    await service.delete(issue_id, project_id)
    await db.commit()


@router.post("/{issue_id}/start-analysis", response_model=IssueResponse)
async def start_analysis(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.start_analysis(issue_id, project_id)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.post("/{issue_id}/accept", response_model=IssueResponse)
async def accept_issue(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.accept_issue(issue_id, project_id)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.post("/{issue_id}/cancel", response_model=IssueResponse)
async def cancel_issue_endpoint(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.cancel_issue(issue_id, project_id)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)


@router.post("/{issue_id}/complete", response_model=IssueResponse)
async def complete_issue(
    project_id: str, issue_id: str, data: IssueCompleteBody, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    issue = await service.complete_issue(issue_id, project_id, recap=data.recap)
    await db.commit()
    return await _reload_with_tasks(db, issue.id)
