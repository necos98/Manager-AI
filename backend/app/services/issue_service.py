"""File-backed IssueService.

Reads/writes .manager_ai/ layout instead of the DB. Keeps the DB
session only for ProjectService lookups (to resolve project.path),
ActivityService log writes, and hook firing context.

Returns IssueRecord/FeedbackRecord dataclasses. Callers translate to
Pydantic schemas via `schemas.issue.IssueResponse.from_record`.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidTransitionError, NotFoundError, ValidationError
from app.hooks.registry import HookContext, HookEvent, hook_registry
from app.models.issue import VALID_TRANSITIONS, IssueStatus
from app.models.task import TaskStatus
from app.services.activity_service import ActivityService
from app.services.project_service import ProjectService
from app.storage import issue_store
from app.storage.issue_store import (
    FeedbackRecord,
    IssueRecord,
    RelationRecord,
    TaskRecord,
)

# Per-issue locks for complete_issue race guard.
_issue_completion_locks: dict[str, asyncio.Lock] = {}


def _now_iso() -> str:
    # Microsecond resolution so sequential writes remain strictly ordered.
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep="T", timespec="microseconds")


class IssueService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _resolve_path(self, project_id: str) -> str:
        project = await ProjectService(self.session).get_by_id(project_id)
        return project.path

    async def create(self, project_id: str, description: str, priority: int = 3) -> IssueRecord:
        project = await ProjectService(self.session).get_by_id(project_id)
        now = _now_iso()
        record = IssueRecord(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=None,
            status=IssueStatus.NEW.value,
            priority=priority,
            description=description,
            specification=None,
            plan=None,
            recap=None,
            created_at=now,
            updated_at=now,
            tasks=[],
            relations=[],
        )
        issue_store.create_issue(project.path, record)
        await hook_registry.fire(
            HookEvent.ISSUE_CREATED,
            HookContext(
                project_id=project_id,
                issue_id=record.id,
                event=HookEvent.ISSUE_CREATED,
                metadata={
                    "issue_description": description,
                    "project_name": project.name,
                    "project_path": project.path,
                    "project_description": project.description,
                    "tech_stack": project.tech_stack,
                },
            ),
        )
        return record

    async def get_by_id(self, issue_id: str) -> IssueRecord | None:
        """Scan across all projects — needed when project_id unknown."""
        for project in await ProjectService(self.session).list_all(archived=None):
            rec = issue_store.load_issue(project.path, issue_id)
            if rec is not None:
                return rec
        return None

    async def get_for_project(self, issue_id: str, project_id: str) -> IssueRecord:
        path = await self._resolve_path(project_id)
        rec = issue_store.load_issue(path, issue_id)
        if rec is None or rec.project_id != project_id:
            raise NotFoundError("Issue not found")
        return rec

    async def list_by_project(
        self,
        project_id: str,
        status: IssueStatus | None = None,
        search: str | None = None,
    ) -> list[IssueRecord]:
        path = await self._resolve_path(project_id)
        records = issue_store.list_issues_full(path)
        records = [r for r in records if r.project_id == project_id]
        if status is not None:
            target = status.value if isinstance(status, IssueStatus) else str(status)
            records = [r for r in records if r.status == target]
        if search:
            term = search.lower()
            records = [
                r
                for r in records
                if term in (r.description or "").lower() or term in (r.name or "").lower()
            ]
        records.sort(key=lambda r: (r.priority, r.created_at))
        return records

    async def get_next_issue(self, project_id: str) -> IssueRecord | None:
        path = await self._resolve_path(project_id)
        records = [r for r in issue_store.list_issues_full(path) if r.project_id == project_id]
        accepted = sorted(
            [r for r in records if r.status == IssueStatus.ACCEPTED.value],
            key=lambda r: (r.priority, r.created_at),
        )
        if accepted:
            return accepted[0]
        new = sorted(
            [r for r in records if r.status == IssueStatus.NEW.value],
            key=lambda r: (r.priority, r.created_at),
        )
        return new[0] if new else None

    async def update_status(
        self,
        issue_id: str,
        project_id: str,
        new_status: IssueStatus,
    ) -> IssueRecord:
        rec = await self.get_for_project(issue_id, project_id)
        target = new_status.value if isinstance(new_status, IssueStatus) else str(new_status)
        current = IssueStatus(rec.status)
        desired = IssueStatus(target)
        if desired == IssueStatus.CANCELED:
            rec.status = desired.value
            rec.updated_at = _now_iso()
            issue_store.update_issue(await self._resolve_path(project_id), rec)
            return rec
        if (current, desired) not in VALID_TRANSITIONS:
            raise InvalidTransitionError(
                f"Invalid state transition from {current.value} to {desired.value}"
            )
        rec.status = desired.value
        rec.updated_at = _now_iso()
        issue_store.update_issue(await self._resolve_path(project_id), rec)
        return rec

    async def update_fields(self, issue_id: str, project_id: str, **kwargs: Any) -> IssueRecord:
        rec = await self.get_for_project(issue_id, project_id)
        for key, value in kwargs.items():
            if value is None:
                continue
            if key == "status":
                rec.status = value.value if isinstance(value, IssueStatus) else str(value)
            elif hasattr(rec, key):
                setattr(rec, key, value)
        rec.updated_at = _now_iso()
        issue_store.update_issue(await self._resolve_path(project_id), rec)
        return rec

    async def set_name(self, issue_id: str, project_id: str, name: str) -> IssueRecord:
        if len(name) > 500:
            raise ValidationError("Name must be 500 characters or less")
        return await self.update_fields(issue_id, project_id, name=name)

    async def create_spec(self, issue_id: str, project_id: str, spec: str) -> IssueRecord:
        if not spec or not spec.strip():
            raise ValidationError("Specification cannot be blank")
        rec = await self.get_for_project(issue_id, project_id)
        if rec.status != IssueStatus.NEW.value:
            raise InvalidTransitionError(
                f"Can only create spec for issues in New status, got {rec.status}"
            )
        rec.specification = spec
        rec.status = IssueStatus.REASONING.value
        rec.updated_at = _now_iso()
        issue_store.update_issue(await self._resolve_path(project_id), rec)
        await ActivityService(self.session).log(
            project_id=project_id,
            issue_id=issue_id,
            event_type="spec_created",
            details={"issue_name": rec.name or ""},
        )
        return rec

    async def edit_spec(self, issue_id: str, project_id: str, spec: str) -> IssueRecord:
        if not spec or not spec.strip():
            raise ValidationError("Specification cannot be blank")
        rec = await self.get_for_project(issue_id, project_id)
        if rec.status != IssueStatus.REASONING.value:
            raise InvalidTransitionError("Issue must be in Reasoning status to edit spec")
        rec.specification = spec
        rec.updated_at = _now_iso()
        issue_store.update_issue(await self._resolve_path(project_id), rec)
        return rec

    async def create_plan(self, issue_id: str, project_id: str, plan: str) -> IssueRecord:
        if not plan or not plan.strip():
            raise ValidationError("Plan cannot be blank")
        rec = await self.get_for_project(issue_id, project_id)
        if rec.status != IssueStatus.REASONING.value:
            raise InvalidTransitionError(
                f"Can only create plan for issues in Reasoning status, got {rec.status}"
            )
        rec.plan = plan
        rec.status = IssueStatus.PLANNED.value
        rec.updated_at = _now_iso()
        issue_store.update_issue(await self._resolve_path(project_id), rec)
        await ActivityService(self.session).log(
            project_id=project_id,
            issue_id=issue_id,
            event_type="plan_created",
            details={"issue_name": rec.name or ""},
        )
        return rec

    async def edit_plan(self, issue_id: str, project_id: str, plan: str) -> IssueRecord:
        if not plan or not plan.strip():
            raise ValidationError("Plan cannot be blank")
        rec = await self.get_for_project(issue_id, project_id)
        if rec.status != IssueStatus.PLANNED.value:
            raise InvalidTransitionError("Issue must be in Planned status to edit plan")
        rec.plan = plan
        rec.updated_at = _now_iso()
        issue_store.update_issue(await self._resolve_path(project_id), rec)
        return rec

    async def accept_issue(self, issue_id: str, project_id: str) -> IssueRecord:
        rec = await self.get_for_project(issue_id, project_id)
        if rec.status != IssueStatus.PLANNED.value:
            raise InvalidTransitionError(
                f"Can only accept issues in Planned status, got {rec.status}"
            )
        rec.status = IssueStatus.ACCEPTED.value
        rec.updated_at = _now_iso()
        path = await self._resolve_path(project_id)
        issue_store.update_issue(path, rec)
        await ActivityService(self.session).log(
            project_id=project_id,
            issue_id=issue_id,
            event_type="issue_accepted",
            details={"issue_name": rec.name or ""},
        )
        project = await ProjectService(self.session).get_by_id(project_id)
        await hook_registry.fire(
            HookEvent.ISSUE_ACCEPTED,
            HookContext(
                project_id=project_id,
                issue_id=issue_id,
                event=HookEvent.ISSUE_ACCEPTED,
                metadata={
                    "issue_name": rec.name or (rec.description or "")[:50] or "Untitled",
                    "issue_description": rec.description or "",
                    "specification": rec.specification or "",
                    "plan": rec.plan or "",
                    "project_name": project.name,
                    "project_path": project.path,
                    "project_description": project.description,
                    "tech_stack": project.tech_stack,
                },
            ),
        )
        return rec

    async def cancel_issue(self, issue_id: str, project_id: str) -> IssueRecord:
        rec = await self.get_for_project(issue_id, project_id)
        rec.status = IssueStatus.CANCELED.value
        rec.updated_at = _now_iso()
        issue_store.update_issue(await self._resolve_path(project_id), rec)
        await ActivityService(self.session).log(
            project_id=project_id,
            issue_id=issue_id,
            event_type="issue_canceled",
            details={"issue_name": rec.name or ""},
        )
        project = await ProjectService(self.session).get_by_id(project_id)
        await hook_registry.fire(
            HookEvent.ISSUE_CANCELLED,
            HookContext(
                project_id=project_id,
                issue_id=issue_id,
                event=HookEvent.ISSUE_CANCELLED,
                metadata={
                    "issue_name": rec.name or (rec.description or "")[:50] or "Untitled",
                    "project_name": project.name,
                },
            ),
        )
        return rec

    async def complete_issue(self, issue_id: str, project_id: str, recap: str) -> IssueRecord:
        if not recap or not recap.strip():
            raise ValidationError("Recap cannot be blank")
        lock = _issue_completion_locks.setdefault(issue_id, asyncio.Lock())
        async with lock:
            rec = await self.get_for_project(issue_id, project_id)
            if rec.status != IssueStatus.ACCEPTED.value:
                raise InvalidTransitionError(
                    f"Can only complete issues in Accepted status, got {rec.status}"
                )
            pending = [t for t in rec.tasks if t.status != TaskStatus.COMPLETED.value]
            if rec.tasks and pending:
                names = ", ".join(t.name for t in pending)
                raise ValidationError(
                    f"Cannot complete: {len(pending)} tasks not finished: {names}"
                )
            rec.recap = recap
            rec.status = IssueStatus.FINISHED.value
            rec.updated_at = _now_iso()
            path = await self._resolve_path(project_id)
            issue_store.update_issue(path, rec)
            await ActivityService(self.session).log(
                project_id=project_id,
                issue_id=issue_id,
                event_type="issue_completed",
                details={"issue_name": rec.name or "", "recap_preview": (recap or "")[:100]},
            )
            project = await ProjectService(self.session).get_by_id(project_id)
            await self.session.commit()  # flush activity log
            await hook_registry.fire(
                HookEvent.ISSUE_COMPLETED,
                HookContext(
                    project_id=project_id,
                    issue_id=issue_id,
                    event=HookEvent.ISSUE_COMPLETED,
                    metadata={
                        "issue_name": rec.name or "",
                        "recap": rec.recap or "",
                        "project_name": project.name,
                        "project_path": project.path,
                        "project_description": project.description,
                        "tech_stack": project.tech_stack,
                    },
                ),
            )
            return rec

    async def delete(self, issue_id: str, project_id: str) -> bool:
        path = await self._resolve_path(project_id)
        if not issue_store.issue_exists(path, issue_id):
            return False
        issue_store.delete_issue(path, issue_id)
        return True

    async def add_feedback(self, issue_id: str, project_id: str, content: str) -> FeedbackRecord:
        await self.get_for_project(issue_id, project_id)  # validates ownership
        fb = FeedbackRecord(
            id=str(uuid.uuid4()),
            issue_id=issue_id,
            content=content,
            created_at=_now_iso(),
        )
        issue_store.add_feedback(await self._resolve_path(project_id), issue_id, fb)
        return fb

    async def list_feedback(self, issue_id: str, project_id: str) -> list[FeedbackRecord]:
        await self.get_for_project(issue_id, project_id)
        return issue_store.load_feedback(await self._resolve_path(project_id), issue_id)
