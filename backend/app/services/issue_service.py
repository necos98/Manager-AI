from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.issue import VALID_TRANSITIONS, Issue, IssueStatus


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
            raise ValueError("Issue not found")
        if issue.project_id != project_id:
            raise PermissionError("Issue does not belong to project")
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
            .where(Issue.status.in_([IssueStatus.NEW, IssueStatus.DECLINED]))
            .order_by(
                case(
                    (Issue.status == IssueStatus.DECLINED, 0),
                    (Issue.status == IssueStatus.NEW, 1),
                ).asc(),
                Issue.priority.asc(),
                Issue.created_at.asc(),
            )
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        issue_id: str,
        project_id: str,
        new_status: IssueStatus,
        decline_feedback: str | None = None,
    ) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if new_status == IssueStatus.CANCELED:
            issue.status = IssueStatus.CANCELED
            await self.session.flush()
            return issue
        if (issue.status, new_status) not in VALID_TRANSITIONS:
            raise ValueError(f"Invalid state transition from {issue.status.value} to {new_status.value}")
        issue.status = new_status
        if new_status == IssueStatus.DECLINED and decline_feedback:
            issue.decline_feedback = decline_feedback
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
        return await self.update_fields(issue_id, project_id, name=name)

    async def complete_issue(self, issue_id: str, project_id: str, recap: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.ACCEPTED:
            raise ValueError(f"Can only complete issues in Accepted status, got {issue.status.value}")
        issue.recap = recap
        issue.status = IssueStatus.FINISHED
        await self.session.flush()
        return issue

    async def create_spec(self, issue_id: str, project_id: str, spec: str) -> Issue:
        if not spec or not spec.strip():
            raise ValueError("Specification cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status not in (IssueStatus.NEW, IssueStatus.DECLINED):
            raise ValueError(
                f"Can only create spec for issues in New or Declined status, got {issue.status.value}"
            )
        issue.specification = spec
        issue.status = IssueStatus.REASONING
        await self.session.flush()
        return issue

    async def edit_spec(self, issue_id: str, project_id: str, spec: str) -> Issue:
        if not spec or not spec.strip():
            raise ValueError("Specification cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.REASONING:
            raise ValueError("Issue must be in Reasoning status to edit spec")
        issue.specification = spec
        await self.session.flush()
        return issue

    async def create_plan(self, issue_id: str, project_id: str, plan: str) -> Issue:
        if not plan or not plan.strip():
            raise ValueError("Plan cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.REASONING:
            raise ValueError(
                f"Can only create plan for issues in Reasoning status, got {issue.status.value}"
            )
        issue.plan = plan
        issue.status = IssueStatus.PLANNED
        await self.session.flush()
        return issue

    async def edit_plan(self, issue_id: str, project_id: str, plan: str) -> Issue:
        if not plan or not plan.strip():
            raise ValueError("Plan cannot be blank")
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise ValueError("Issue must be in Planned status to edit plan")
        issue.plan = plan
        await self.session.flush()
        return issue

    async def accept_issue(self, issue_id: str, project_id: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise ValueError(
                f"Can only accept issues in Planned status, got {issue.status.value}"
            )
        issue.status = IssueStatus.ACCEPTED
        await self.session.flush()
        return issue

    async def decline_issue(self, issue_id: str, project_id: str, feedback: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        if issue.status != IssueStatus.PLANNED:
            raise ValueError(
                f"Can only decline issues in Planned status, got {issue.status.value}"
            )
        issue.status = IssueStatus.DECLINED
        issue.decline_feedback = feedback
        await self.session.flush()
        return issue

    async def cancel_issue(self, issue_id: str, project_id: str) -> Issue:
        issue = await self.get_for_project(issue_id, project_id)
        issue.status = IssueStatus.CANCELED
        await self.session.flush()
        return issue

    async def delete(self, issue_id: str, project_id: str) -> bool:
        issue = await self.get_for_project(issue_id, project_id)
        await self.session.delete(issue)
        await self.session.flush()
        return True
