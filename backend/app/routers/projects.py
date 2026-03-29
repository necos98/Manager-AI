import json
import os
import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project import DashboardProject, ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService
from app.services.terminal_service import terminal_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _enrich_project(service: ProjectService, project) -> dict:
    """Add issue_counts to a project response."""
    counts = await service.get_issue_counts(project.id)
    result = ProjectResponse.model_validate(project)
    result.issue_counts = counts
    return result


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description,
        tech_stack=data.tech_stack, shell=data.shell
    )
    await db.commit()
    return await _enrich_project(service, project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    projects = await service.list_all()
    return [await _enrich_project(service, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    return await _enrich_project(service, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.update(project_id, **data.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(project)
    return await _enrich_project(service, project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    # Validate project exists (raises NotFoundError if not)
    await service.get_by_id(project_id)
    # Kill active terminals for this project
    for term in terminal_service.list_active(project_id=project_id):
        try:
            terminal_service.kill(term["id"])
        except KeyError:
            pass
    await service.delete(project_id)
    await db.commit()


@router.post("/{project_id}/install-manager-json", status_code=200)
async def install_manager_json(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)
    dest = os.path.join(project.path, "manager.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump({"project_id": project.id}, f, indent=2)
    return {"path": dest}


@router.post("/{project_id}/install-claude-resources", status_code=200)
async def install_claude_resources(project_id: str, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.get_by_id(project_id)

    src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "claude_resources")
    if not os.path.isdir(src):
        raise HTTPException(status_code=404, detail="claude_resources folder not found")

    dest = os.path.join(project.path, ".claude")
    os.makedirs(dest, exist_ok=True)

    copied = []
    for item in os.listdir(src):
        if item.startswith("."):
            continue
        s = os.path.join(src, item)
        d = os.path.join(dest, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
        copied.append(item)

    return {"path": dest, "copied": copied}


dashboard_router = APIRouter(tags=["dashboard"])


@dashboard_router.get("/api/dashboard", response_model=list[DashboardProject])
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    svc = ProjectService(db)
    return await svc.get_dashboard_data()
