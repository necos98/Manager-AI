from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from app.hooks.registry import HookContext, HookEvent, hook_registry
from app.models.issue import VALID_TRANSITIONS, Issue, IssueStatus
from app.services.project_service import ProjectService


class IssueService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: str, description: str, priority: int = 3) -> Issue:
        issue = Issue(project_id=project_id, description=description, priority=priority)
        self.session.add(issue)
        await self.session.flush()
        return issue

    async def get_by_id(self, issue_id: str) -> Issue | None:
        return await self.session.get(Issue, issue_id)

    async def get_for_project(self, issue_id: str, project_id: str) -> Issue:
        result = await self.session.execute(
            select(Issue)
            .options(selectinload(Issue.tasks))
            .where(Issue.id == issue_id)
        )
        issue = result.scalar_one_or_none()
        if issue is None:
            raise NotFoundError("Issue not found")
        if issue.project_id != project_id:
            raise NotFoundError("Issue not found")
        return issue

    async def list_by_project(
        self, project_id: str, status: IssueStatus | None = None
    ) -> list[Issue]:
        query = select(Issue).options(selectinload(Issue.tasks)).where(Issue.project_id == project_id)
        if status is not None:
            query = query.where(Issue.status == status)
        query = query.order_by(Issue.priority.asc(), Issue.created_at.asc())
        result = await self.session.execute(query)
        return list(result.unique().scalars().all())

    async def get_next_issue(self, project_id: str) -> Issue | None:
        query = (
            select(Issue)
            .where(Issue.project_id == project_id)
            .where(Issue.status == IssueStatus.NEW)
            .order_by(Issue.priority.asc(), Issue.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        issue_id: str,
        project_id: str,
        new_status: IssueStatus,
    ) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if new_status == IssueStatus.CANCELED:
            issue.status = IssueStatus.CANCELED
            await self.session.flush()
            return issue
        if (issue.status, new_status) not in VALID_TRANSITIONS:
            raise InvalidTransitionError(f"Invalid state transition from {issue.status.value} to {new_status.value}")
        issue.status = new_status
        await self.session.flush()
        return issue

    async def update_fields(self, issue_id: str, project_id: str, **kwargs) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(issue, key, value)
        await self.session.flush()
        return issue

    async def set_name(self, issue_id: str, project_id: str, name: str) -> Issue:
        if len(name) > 500:
            raise ValidationError("Name must be 500 characters or less")
        return await self.update_fields(issue_id, project_id, name=name)

    async def complete_issue(self, issue_id: str, project_id: str, recap: str) -> Issue:
        if not recap or not recap.strip():
            raise ValidationError("Recap cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.ACCEPTED:
            raise InvalidTransitionError(f"Can only complete issues in Accepted status, got {issue.status.value}")
        # Enforce task completion
        from app.services.task_service import TaskService
        from app.models.task import TaskStatus
        task_service = TaskService(self.session)
        tasks = await task_service.list_by_issue(issue.id)
        if tasks:
            pending = [t for t in tasks if t.status != TaskStatus.COMPLETED]
            if pending:
                names = ", ".join(t.name for t in pending)
                raise ValidationError(
                    f"Cannot complete: {len(pending)} tasks not finished: {names}"
                )
        issue.recap = recap
        issue.status = IssueStatus.FINISHED
        await self.session.flush()
        # Fire hook with project context
        project_service = ProjectService(self.session)
        project = await project_service.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        await hook_registry.fire(
            HookEvent.ISSUE_COMPLETED,
            HookContext(
                project_id=project_id,
                issue_id=issue_id,
                event=HookEvent.ISSUE_COMPLETED,
                metadata={
                    "issue_name": issue.name or "",
                    "recap": issue.recap or "",
                    "project_name": project.name if project else "",
                    "project_path": project.path if project else "",
                    "project_description": project.description if project else "",
                    "tech_stack": project.tech_stack if project else "",
                },
            ),
        )
        return issue

    async def create_spec(self, issue_id: str, project_id: str, spec: str) -> Issue:
        if not spec or not spec.strip():
            raise ValidationError("Specification cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.NEW:
            raise InvalidTransitionError(
                f"Can only create spec for issues in New status, got {issue.status.value}"
            )
        issue.specification = spec
        issue.status = IssueStatus.REASONING
        await self.session.flush()
        return issue

    async def edit_spec(self, issue_id: str, project_id: str, spec: str) -> Issue:
        if not spec or not spec.strip():
            raise ValidationError("Specification cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.REASONING:
            raise InvalidTransitionError("Issue must be in Reasoning status to edit spec")
        issue.specification = spec
        await self.session.flush()
        return issue

    async def create_plan(self, issue_id: str, project_id: str, plan: str) -> Issue:
        if not plan or not plan.strip():
            raise ValidationError("Plan cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.REASONING:
            raise InvalidTransitionError(
                f"Can only create plan for issues in Reasoning status, got {issue.status.value}"
            )
        issue.plan = plan
        issue.status = IssueStatus.PLANNED
        await self.session.flush()
        return issue

    async def edit_plan(self, issue_id: str, project_id: str, plan: str) -> Issue:
        if not plan or not plan.strip():
            raise ValidationError("Plan cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise InvalidTransitionError("Issue must be in Planned status to edit plan")
        issue.plan = plan
        await self.session.flush()
        return issue

    async def accept_issue(self, issue_id: str, project_id: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise InvalidTransitionError(
                f"Can only accept issues in Planned status, got {issue.status.value}"
            )
        issue.status = IssueStatus.ACCEPTED
        await self.session.flush()
        await hook_registry.fire(
            HookEvent.ISSUE_ACCEPTED,
            HookContext(project_id=project_id, issue_id=issue_id, event=HookEvent.ISSUE_ACCEPTED),
        )
        return issue

    async def cancel_issue(self, issue_id: str, project_id: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        issue.status = IssueStatus.CANCELED
        await self.session.flush()
        await hook_registry.fire(
            HookEvent.ISSUE_CANCELLED,
            HookContext(project_id=project_id, issue_id=issue_id, event=HookEvent.ISSUE_CANCELLED),
        )
        return issue

    async def start_analysis(self, issue_id: str, project_id: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.NEW:
            raise InvalidTransitionError(
                f"Can only start analysis for issues in New status, got {issue.status.value}"
            )
        project_service = ProjectService(self.session)
        project = await project_service.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        await hook_registry.fire(
            HookEvent.ISSUE_ANALYSIS_STARTED,
            HookContext(
                project_id=project_id,
                issue_id=issue_id,
                event=HookEvent.ISSUE_ANALYSIS_STARTED,
                metadata={
                    "issue_description": issue.description,
                    "project_name": project.name if project else "",
                    "project_path": project.path if project else "",
                    "project_description": project.description if project else "",
                    "tech_stack": project.tech_stack if project else "",
                },
            ),
        )
        return issue

    async def delete(self, issue_id: str, project_id: str) -> bool:
        issue = await self.get_for_project(issue_id, project_id)
        await self.session.delete(issue)
        await self.session.flush()
        return True
