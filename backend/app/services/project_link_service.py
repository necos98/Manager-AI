from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.project_link import ProjectLink


class ProjectLinkService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_project(self, project_id: str) -> list[ProjectLink]:
        result = await self.session.execute(
            select(ProjectLink)
            .options(selectinload(ProjectLink.source_project), selectinload(ProjectLink.target_project))
            .where(
                or_(
                    ProjectLink.source_project_id == project_id,
                    ProjectLink.target_project_id == project_id,
                )
            )
            .order_by(ProjectLink.created_at)
        )
        return list(result.scalars().all())

    async def create(self, source_project_id: str, target_project_id: str, description: str) -> ProjectLink:
        if source_project_id == target_project_id:
            raise ValidationError("A project cannot be linked to itself")
        if not description.strip():
            raise ValidationError("Description is required")

        link = ProjectLink(
            source_project_id=source_project_id,
            target_project_id=target_project_id,
            description=description.strip(),
        )
        self.session.add(link)
        await self.session.flush()
        return await self._get_by_id(link.id)

    async def update(self, link_id: str, project_id: str, description: str) -> ProjectLink:
        link = await self._get_by_id(link_id)
        if link.source_project_id != project_id and link.target_project_id != project_id:
            raise NotFoundError("Project link not found")
        if not description.strip():
            raise ValidationError("Description is required")
        link.description = description.strip()
        await self.session.flush()
        return await self._get_by_id(link_id)

    async def delete(self, link_id: str, project_id: str) -> None:
        link = await self._get_by_id(link_id)
        if link.source_project_id != project_id and link.target_project_id != project_id:
            raise NotFoundError("Project link not found")
        await self.session.delete(link)
        await self.session.flush()

    async def _get_by_id(self, link_id: str) -> ProjectLink:
        result = await self.session.execute(
            select(ProjectLink)
            .options(selectinload(ProjectLink.source_project), selectinload(ProjectLink.target_project))
            .where(ProjectLink.id == link_id)
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise NotFoundError("Project link not found")
        return link
