from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.activity import ActivityLogResponse
from app.services.activity_service import ActivityService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects/{project_id}/activity", tags=["activity"])


@router.get("", response_model=list[ActivityLogResponse])
async def list_activity(
    project_id: str,
    issue_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    project_service = ProjectService(db)
    await project_service.get_by_id(project_id)  # raises NotFoundError → 404 via global handler
    activity_service = ActivityService(db)
    return await activity_service.list_for_project(
        project_id, issue_id=issue_id, limit=limit, offset=offset
    )
