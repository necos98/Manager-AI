from __future__ import annotations

import json
import os
import uuid

from app.utils.datetime import naive_utc_now
from sqlalchemy import delete as sa_delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.project import Project


class ProjectService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, name: str, path: str, description: str = "", tech_stack: str = "", shell: str | None = None, url: str | None = None
    ) -> Project:
        # Use existing project_id from manager.json if present
        project_id = None
        manager_json_path = os.path.join(path, "manager.json")
        if os.path.isfile(manager_json_path):
            try:
                with open(manager_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                existing_id = data.get("project_id")
                if existing_id and isinstance(existing_id, str):
                    project_id = existing_id
            except (json.JSONDecodeError, OSError):
                pass

        project = Project(
            id=project_id or str(uuid.uuid4()),
            name=name, path=path, description=description,
            tech_stack=tech_stack, shell=shell, url=url,
        )
        self.session.add(project)
        await self.session.flush()
        from app.services.agent_service import AgentService
        from app.services.pipeline_service import PipelineService
        await AgentService(self.session).seed_defaults()
        await PipelineService(self.session).seed_defaults()
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
            project.archived_at = naive_utc_now()
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
        # Delete project_links referencing this project (FK constraint).
        # Links are meaningless without both projects still existing.
        from app.models.project_link import ProjectLink

        links = await self.session.execute(
            select(ProjectLink).where(
                or_(
                    ProjectLink.source_project_id == project_id,
                    ProjectLink.target_project_id == project_id,
                )
            )
        )
        for link in links.scalars().all():
            await self.session.delete(link)
        await self.session.flush()
        # Use raw DELETE to bypass ORM relationship resolution.
        # The DB has legacy child tables (issues, project_files, etc.)
        # that may have schema drift from the models — loading relationships
        # would crash on missing columns like issues.finished_at.
        await self.session.execute(
            sa_delete(Project).where(Project.id == project_id)
        )
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
