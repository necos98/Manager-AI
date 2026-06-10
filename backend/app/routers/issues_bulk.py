"""Router per operazioni bulk sulle issue (status, tags, delete, priority, category)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.issue import (
    BulkCategoryUpdate,
    BulkDeleteRequest,
    BulkPriorityUpdate,
    BulkResponse,
    BulkStatusUpdate,
    BulkTagsUpdate,
)
from app.services.activity_service import ActivityService
from app.services.issue_service import IssueService

router = APIRouter(prefix="/api/projects/{project_id}/issues/bulk", tags=["issues-bulk"])


@router.patch("/status", response_model=BulkResponse)
async def bulk_update_status(
    project_id: str,
    data: BulkStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    result = await service.bulk_update_status(project_id, data.issue_ids, data.status)
    await db.commit()
    await ActivityService(db).log(
        project_id=project_id,
        event_type="bulk_status_update",
        details={"count": result["updated"], "errors": result["errors"]},
    )
    return BulkResponse(updated=result["updated"], errors=result["errors"])


@router.patch("/tags", response_model=BulkResponse)
async def bulk_update_tags(
    project_id: str,
    data: BulkTagsUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    result = await service.bulk_update_tags(project_id, data.issue_ids, data.tags, data.mode)
    await db.commit()
    await ActivityService(db).log(
        project_id=project_id,
        event_type="bulk_tags_update",
        details={"count": result["updated"], "mode": data.mode, "errors": result["errors"]},
    )
    return BulkResponse(updated=result["updated"], errors=result["errors"])


@router.post("/delete", response_model=BulkResponse)
async def bulk_delete_issues(
    project_id: str,
    data: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    result = await service.bulk_delete(project_id, data.issue_ids)
    await db.commit()
    await ActivityService(db).log(
        project_id=project_id,
        event_type="bulk_delete",
        details={"count": result["deleted"], "errors": result["errors"]},
    )
    return BulkResponse(deleted=result["deleted"], errors=result["errors"])


@router.patch("/priority", response_model=BulkResponse)
async def bulk_update_priority(
    project_id: str,
    data: BulkPriorityUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    result = await service.bulk_update_priority(project_id, data.issue_ids, data.priority)
    await db.commit()
    await ActivityService(db).log(
        project_id=project_id,
        event_type="bulk_priority_update",
        details={"count": result["updated"], "priority": data.priority, "errors": result["errors"]},
    )
    return BulkResponse(updated=result["updated"], errors=result["errors"])


@router.patch("/category", response_model=BulkResponse)
async def bulk_update_category(
    project_id: str,
    data: BulkCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    result = await service.bulk_update_category(project_id, data.issue_ids, data.category)
    await db.commit()
    await ActivityService(db).log(
        project_id=project_id,
        event_type="bulk_category_update",
        details={"count": result["updated"], "category": data.category, "errors": result["errors"]},
    )
    return BulkResponse(updated=result["updated"], errors=result["errors"])
