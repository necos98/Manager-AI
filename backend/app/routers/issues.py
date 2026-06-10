from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.issue import IssueStatus
from app.schemas.issue import (
    IssueCompleteBody,
    IssueCreate,
    IssueForceFinishBody,
    IssueFeedbackCreate,
    IssueFeedbackResponse,
    IssueResponse,
    IssueStatusUpdate,
    IssueUpdate,
)
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.event_service import event_service

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


@router.post("", response_model=IssueResponse, status_code=201)
async def create_issue(project_id: str, data: IssueCreate, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    record = await service.create(project_id=project_id, description=data.description, priority=data.priority, category=data.category, tags=data.tags)
    if data.source_issue_id:
        from app.models.issue_relation import RelationType
        from app.services.issue_relation_service import IssueRelationService
        rel_service = IssueRelationService(db)
        await rel_service.add_relation(record.id, data.source_issue_id, RelationType.RELATED)
    await db.commit()
    return IssueResponse.from_record(record)


@router.get("", response_model=list[IssueResponse])
async def list_issues(
    project_id: str,
    status: IssueStatus | None = Query(None),
    search: str | None = Query(None),
    tag: str | None = Query(None),
    limit: int | None = Query(None),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    records = await service.list_by_project(project_id, status=status, search=search, tag=tag, limit=limit, offset=offset)
    return [IssueResponse.from_record(r) for r in records]


@router.get("/tags", response_model=list[str])
async def list_project_tags(project_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    return await service.get_project_tags(project_id)


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
    """Soft-delete an issue. Can be restored within the undo window."""
    service = IssueService(db)
    await service.delete(issue_id, project_id)
    await db.commit()


@router.post("/{issue_id}/restore", response_model=IssueResponse)
async def restore_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted issue."""
    service = IssueService(db)
    record = await service.restore(issue_id, project_id)
    await db.commit()
    return IssueResponse.from_record(record)


@router.delete("/{issue_id}/permanent", status_code=204)
async def permanently_delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently delete an issue (no undo)."""
    service = IssueService(db)
    await service.permanently_delete(issue_id, project_id)
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
    from app.utils.datetime import iso_now

    service = IssueService(db)
    record = await service.complete_issue(issue_id, project_id, recap=data.recap)
    await db.commit()

    project = await ProjectService(db).get_by_id(project_id)
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": IssueStatus.FINISHED.value,
        "project_id": project_id,
        "project_name": project.name if project else "",
        "issue_id": issue_id,
        "issue_name": record.name or "Untitled",
        "description": record.description or "",
        "recap": record.recap or "",
        "timestamp": iso_now(),
    })

    return IssueResponse.from_record(record)


@router.post("/{issue_id}/force-finish", response_model=IssueResponse)
async def force_finish_issue_endpoint(
    project_id: str, issue_id: str, data: IssueForceFinishBody | None = None, db: AsyncSession = Depends(get_db)
):
    from app.utils.datetime import iso_now

    service = IssueService(db)
    record = await service.force_finish_issue(issue_id, project_id, recap=data.recap if data else None)
    await db.commit()

    project = await ProjectService(db).get_by_id(project_id)
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": IssueStatus.FINISHED.value,
        "project_id": project_id,
        "project_name": project.name if project else "",
        "issue_id": issue_id,
        "issue_name": record.name or "Untitled",
        "description": record.description or "",
        "recap": record.recap or "",
        "timestamp": iso_now(),
    })

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
