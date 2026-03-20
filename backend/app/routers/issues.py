from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.issue import IssueStatus
from app.schemas.issue import IssueCreate, IssueResponse, IssueStatusUpdate, IssueUpdate
from app.services.issue_service import IssueService

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


@router.post("", response_model=IssueResponse, status_code=201)
async def create_issue(project_id: str, data: IssueCreate, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    issue = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return issue


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
    try:
        issue = await service.get_for_project(issue_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return issue


@router.put("/{issue_id}", response_model=IssueResponse)
async def update_issue(
    project_id: str, issue_id: str, data: IssueUpdate, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    try:
        issue = await service.update_fields(issue_id, project_id, **data.model_dump(exclude_unset=True))
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(issue)
    return issue


@router.patch("/{issue_id}/status", response_model=IssueResponse)
async def update_issue_status(
    project_id: str,
    issue_id: str,
    data: IssueStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = IssueService(db)
    try:
        issue = await service.update_status(
            issue_id, project_id, data.status, decline_feedback=data.decline_feedback
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=204)
async def delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    service = IssueService(db)
    try:
        await service.delete(issue_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
