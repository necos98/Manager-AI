"""File-backed TaskService.

Tasks are embedded in each issue's issue.yaml. Service keeps a DB
session only for ProjectService lookup (to resolve project.path for
the issue whose tasks are being mutated).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidTransitionError, NotFoundError
from app.models.task import VALID_TASK_TRANSITIONS, TaskStatus
from app.services.project_service import ProjectService
from app.storage import issue_store
from app.storage.issue_store import TaskRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep="T", timespec="seconds")


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _project_path_for_issue(self, issue_id: str) -> str:
        projects = await ProjectService(self.session).list_all(archived=None)
        for project in projects:
            if issue_store.issue_exists(project.path, issue_id):
                return project.path
        raise NotFoundError("Issue not found")

    async def create_bulk(self, issue_id: str, tasks: list[dict]) -> list[TaskRecord]:
        path = await self._project_path_for_issue(issue_id)
        issue = issue_store.load_issue(path, issue_id)
        existing = list(issue.tasks) if issue else []
        next_order = max((t.order for t in existing), default=-1) + 1
        now = _now_iso()
        new_tasks: list[TaskRecord] = []
        for i, spec in enumerate(tasks):
            new_tasks.append(
                TaskRecord(
                    id=str(uuid.uuid4()),
                    name=spec["name"],
                    status=TaskStatus.PENDING.value,
                    order=next_order + i,
                    created_at=now,
                    updated_at=now,
                )
            )
        merged = existing + new_tasks
        issue_store.replace_tasks(path, issue_id, merged)
        return new_tasks

    async def replace_all(self, issue_id: str, tasks: list[dict]) -> list[TaskRecord]:
        path = await self._project_path_for_issue(issue_id)
        now = _now_iso()
        records = [
            TaskRecord(
                id=str(uuid.uuid4()),
                name=spec["name"],
                status=TaskStatus.PENDING.value,
                order=i,
                created_at=now,
                updated_at=now,
            )
            for i, spec in enumerate(tasks)
        ]
        issue_store.replace_tasks(path, issue_id, records)
        return records

    async def get_by_id(self, task_id: str) -> TaskRecord:
        projects = await ProjectService(self.session).list_all(archived=None)
        for project in projects:
            found = issue_store.find_task(project.path, task_id)
            if found is not None:
                return found[1]
        raise NotFoundError("Task not found")

    async def update(self, task_id: str, **kwargs) -> TaskRecord:
        projects = await ProjectService(self.session).list_all(archived=None)
        for project in projects:
            found = issue_store.find_task(project.path, task_id)
            if found is None:
                continue
            issue, task = found
            if "status" in kwargs and kwargs["status"] is not None:
                new_status = kwargs["status"]
                if isinstance(new_status, str):
                    new_status = TaskStatus(new_status)
                current = TaskStatus(task.status)
                if (current, new_status) not in VALID_TASK_TRANSITIONS:
                    raise InvalidTransitionError(
                        f"Invalid task transition from {current.value} to {new_status.value}"
                    )
                task.status = new_status.value
            if "name" in kwargs and kwargs["name"] is not None:
                task.name = kwargs["name"]
            task.updated_at = _now_iso()
            issue_store.upsert_task(project.path, issue.id, task)
            return task
        raise NotFoundError("Task not found")

    async def delete(self, task_id: str) -> bool:
        projects = await ProjectService(self.session).list_all(archived=None)
        for project in projects:
            found = issue_store.find_task(project.path, task_id)
            if found is None:
                continue
            issue, _ = found
            issue_store.remove_task(project.path, issue.id, task_id)
            return True
        raise NotFoundError("Task not found")

    async def list_by_issue(self, issue_id: str) -> list[TaskRecord]:
        path = await self._project_path_for_issue(issue_id)
        issue = issue_store.load_issue(path, issue_id)
        return list(issue.tasks) if issue else []

    async def all_completed(self, issue_id: str) -> bool:
        tasks = await self.list_by_issue(issue_id)
        if not tasks:
            return False
        return all(t.status == TaskStatus.COMPLETED.value for t in tasks)
