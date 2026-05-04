from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.issue import IssueStatus
from app.schemas.issue import (
    IssueCompleteBody,
    IssueCreate,
    IssueFeedbackCreate,
    IssueFeedbackResponse,
    IssueResponse,
    IssueStatusUpdate,
    IssueUpdate,
)
from app.services.issue_service import IssueService

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


@router.post("", response_model=IssueResponse, status_code=201)
async def create_issue(project_id: str, data: IssueCreate, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    record = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return IssueResponse.from_record(record)


@router.get("", response_model=list[IssueResponse])
async def list_issues(
    project_id: str,
    status: IssueStatus | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    records = await service.list_by_project(project_id, status=status, search=search)
    return [IssueResponse.from_record(r) for r in records]


@router.get("/{issue_id}", response_model=IssueResponse)
async def get_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    return IssueResponse.from_record(await service.get_for_project(issue_id, project_id))


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    project_id: str, issue_id: str, data: IssueUpdate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload:
        await service.set_name(issue_id, project_id, payload.pop("name"))
    if payload:
        # Schema field "spec" maps to record field "specification"
        if "spec" in payload:
            payload["specification"] = payload.pop("spec")
        record = await service.update_fields(issue_id, project_id, **payload)
    else:
        record = await service.get_for_project(issue_id, project_id)
    await db.commit()
    return IssueResponse.from_record(record)


@router.patch("/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(
    project_id: str,
    issue_id: str,
    data: IssueStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    record = await service.update_status(issue_id, project_id, data.status)
    await db.commit()
    return IssueResponse.from_record(record)


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    await service.delete(issue_id, project_id)
    await db.commit()


@router.post("/{issue_id}/accept", response_model=IssueResponse)
async def accept_issue(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    record = await service.accept_issue(issue_id, project_id)
    await db.commit()
    return IssueResponse.from_record(record)


@router.post("/{issue_id}/cancel", response_model=IssueResponse)
async def cancel_issue_endpoint(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    record = await service.cancel_issue(issue_id, project_id)
    await db.commit()
    return IssueResponse.from_record(record)


@router.post("/{issue_id}/complete", response_model=IssueResponse)
async def complete_issue(
    project_id: str, issue_id: str, data: IssueCompleteBody, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    record = await service.complete_issue(issue_id, project_id, recap=data.recap)
    await db.commit()
    return IssueResponse.from_record(record)


@router.get("/{issue_id}/feedback", response_model=list[IssueFeedbackResponse])
async def list_feedback(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    records = await service.list_feedback(issue_id, project_id)
    return [IssueFeedbackResponse.from_record(r) for r in records]


@router.post("/{issue_id}/feedback", response_model=IssueFeedbackResponse, status_code=201)
async def add_feedback(
    project_id: str, issue_id: str, data: IssueFeedbackCreate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    fb = await service.add_feedback(issue_id, project_id, data.content)
    await db.commit()
    return IssueFeedbackResponse.from_record(fb)
