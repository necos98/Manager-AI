from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_link import ProjectLinkCreate, ProjectLinkResponse, ProjectLinkUpdate
from app.services.project_link_service import ProjectLinkService

router = APIRouter(prefix="/api/projects/{project_id}/links", tags=["project-links"])


def _to_response(link) -> ProjectLinkResponse:
    return ProjectLinkResponse(
        id=link.id,
        source_project_id=link.source_project_id,
        source_project_name=link.source_project.name,
        target_project_id=link.target_project_id,
        target_project_name=link.target_project.name,
        description=link.description,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


@router.get("", response_model=list[ProjectLinkResponse])
async def list_links(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    links = await svc.list_for_project(project_id)
    return [_to_response(link) for link in links]


@router.post("", response_model=ProjectLinkResponse, status_code=201)
async def create_link(project_id: str, data: ProjectLinkCreate, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    link = await svc.create(project_id, data.target_project_id, data.description)
    await db.commit()
    return _to_response(link)


@router.put("/{link_id}", response_model=ProjectLinkResponse)
async def update_link(project_id: str, link_id: str, data: ProjectLinkUpdate, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    link = await svc.update(link_id, project_id, data.description)
    await db.commit()
    return _to_response(link)


@router.delete("/{link_id}", status_code=204)
async def delete_link(project_id: str, link_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectLinkService(db)
    await svc.delete(link_id, project_id)
    await db.commit()
