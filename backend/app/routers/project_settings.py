from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_setting import ProjectSettingOut, ProjectSettingSet
from app.services.project_setting_service import ProjectSettingService

router = APIRouter(prefix="/api/projects/{project_id}/settings", tags=["project-settings"])


@router.get("", response_model=dict[str, str])
async def get_project_settings(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectSettingService(db)
    return await svc.get_all_for_project(project_id)


@router.put("/{key}", response_model=ProjectSettingOut)
async def set_project_setting(
    project_id: str, key: str, data: ProjectSettingSet, db: AsyncSession = Depends(get_db)
):
    svc = ProjectSettingService(db)
    await svc.set(project_id, key, data.value)
    await db.commit()
    return ProjectSettingOut(key=key, value=data.value)


@router.delete("/{key}", status_code=204)
async def delete_project_setting(
    project_id: str, key: str, db: AsyncSession = Depends(get_db)
):
    svc = ProjectSettingService(db)
    await svc.delete(project_id, key)
    await db.commit()
