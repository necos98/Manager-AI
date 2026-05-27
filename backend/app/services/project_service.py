from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.project import Project


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, name: str, path: str, description: str = "", tech_stack: str = "", shell: str | None = None, url: str | None = None
    ) -> Project:
        project = Project(name=name, path=path, description=description, tech_stack=tech_stack, shell=shell, url=url)
        self.session.add(project)
        await self.session.flush()
        from app.services.agent_service import AgentService
        from app.services.pipeline_service import PipelineService
        await AgentService(self.session).seed_defaults(project.id)
        await PipelineService(self.session).seed_defaults(project.id)
        return project

    async def list_all(self, archived: bool | None = False) -> list[Project]:
        stmt = select(Project)
        if archived is False:
            stmt = stmt.where(Project.archived_at.is_(None))
        elif archived is True:
            stmt = stmt.where(Project.archived_at.is_not(None))
        # archived is None → include both archived and active
        stmt = stmt.order_by(
            Project.favorited_at.is_not(None).desc(),
            Project.favorited_at.desc(),
            func.lower(Project.name).asc(),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, project_id: str) -> Project:
        project = await self.session.get(Project, project_id)
        if project is None:
            raise NotFoundError("Project not found")
        return project

    async def update(self, project_id: str, **kwargs) -> Project:
        project = await self.get_by_id(project_id)
        for key, value in kwargs.items():
            if key == "favorited_at":
                # favorited_at is special: allow setting to None (unfavorite)
                setattr(project, key, value)
            elif value is not None:
                setattr(project, key, value)
        await self.session.flush()
        return project

    async def archive(self, project_id: str) -> Project:
        project = await self.get_by_id(project_id)
        if project.archived_at is None:
            project.archived_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self.session.flush()
        return project

    async def unarchive(self, project_id: str) -> Project:
        project = await self.get_by_id(project_id)
        if project.archived_at is not None:
            project.archived_at = None
            await self.session.flush()
        return project

    async def delete(self, project_id: str) -> None:
        project = await self.get_by_id(project_id)
        await self.session.delete(project)
        await self.session.flush()

    async def get_dashboard_data(self) -> list[dict]:
        from app.models.issue import IssueStatus
        from app.storage import issue_store
        projects = await self.list_all()
        result = []
        terminal_statuses = {IssueStatus.FINISHED.value, IssueStatus.CANCELED.value}
        for project in projects:
            records = [
                r
                for r in issue_store.list_issues(project.path)
                if r.project_id == project.id and r.status not in terminal_statuses
            ]
            records.sort(key=lambda r: (r.priority, r.created_at))
            result.append({
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "active_issues": records,
            })
        return result

    async def get_issue_counts(self, project_id: str) -> dict[str, int]:
        from app.storage import issue_store

        project = await self.get_by_id(project_id)
        counts: dict[str, int] = {}
        for record in issue_store.list_issues(project.path):
            if record.project_id != project_id:
                continue
            counts[record.status] = counts.get(record.status, 0) + 1
        return counts
