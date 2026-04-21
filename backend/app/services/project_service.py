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
        self, name: str, path: str, description: str = "", tech_stack: str = "", shell: str | None = None
    ) -> Project:
        project = Project(name=name, path=path, description=description, tech_stack=tech_stack, shell=shell)
        self.session.add(project)
        await self.session.flush()
        return project

    async def list_all(self, archived: bool | None = False) -> list[Project]:
        stmt = select(Project)
        if archived is False:
            stmt = stmt.where(Project.archived_at.is_(None))
        elif archived is True:
            stmt = stmt.where(Project.archived_at.is_not(None))
        stmt = stmt.order_by(func.lower(Project.name).asc())
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
            if value is not None:
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
        from app.models.issue import Issue, IssueStatus
        projects = await self.list_all()
        result = []
        for project in projects:
            q = (
                select(Issue)
                .where(Issue.project_id == project.id)
                .where(Issue.status.notin_([IssueStatus.FINISHED, IssueStatus.CANCELED]))
                .order_by(Issue.priority.asc(), Issue.created_at.asc())
            )
            r = await self.session.execute(q)
            active = list(r.scalars().all())
            result.append({
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "active_issues": active,
            })
        return result

    async def get_issue_counts(self, project_id: str) -> dict[str, int]:
        from sqlalchemy import func as sqlfunc, select as sqlselect

        from app.models.issue import Issue

        result = await self.session.execute(
            sqlselect(Issue.status, sqlfunc.count())
            .where(Issue.project_id == project_id)
            .group_by(Issue.status)
        )
        return {row[0].value: row[1] for row in result.all()}
