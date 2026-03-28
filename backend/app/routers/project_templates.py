from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.prompt_template import TemplateInfo, TemplateSave
from app.services.prompt_template_service import PromptTemplateService

router = APIRouter(prefix="/api/projects/{project_id}/templates", tags=["project-templates"])


@router.get("", response_model=list[TemplateInfo])
async def list_templates(project_id: str, db: AsyncSession = Depends(get_db)):
    return await PromptTemplateService(db).list_for_project(project_id)


@router.get("/{type}", response_model=TemplateInfo)
async def get_template(project_id: str, type: str, db: AsyncSession = Depends(get_db)):
    return await PromptTemplateService(db).get_template_info(type, project_id)


@router.put("/{type}", response_model=TemplateInfo)
async def save_template_override(
    project_id: str, type: str, data: TemplateSave, db: AsyncSession = Depends(get_db)
):
    svc = PromptTemplateService(db)
    await svc.save_override(type, project_id, data.content)
    await db.commit()
    return await svc.get_template_info(type, project_id)


@router.delete("/{type}", status_code=204)
async def delete_template_override(
    project_id: str, type: str, db: AsyncSession = Depends(get_db)
):
    svc = PromptTemplateService(db)
    await svc.delete_override(type, project_id)
    await db.commit()
