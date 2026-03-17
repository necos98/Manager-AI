import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _enrich_project(service: ProjectService, project) -> dict:
    """Add task_counts to a project response."""
    counts = await service.get_task_counts(project.id)
    result = ProjectResponse.model_validate(project)
    result.task_counts = counts
    return result


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description, tech_stack=data.tech_stack
    )
    await db.commit()
    return await _enrich_project(service, project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    projects = await service.list_all()
    return [await _enrich_project(service, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return await _enrich_project(service, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: uuid.UUID, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update(project_id, **data.model_dump(exclude_unset=True))
    if project is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    deleted = await service.delete(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource not found")
    await db.commit()
