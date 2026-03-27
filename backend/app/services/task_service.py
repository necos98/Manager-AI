from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import VALID_TASK_TRANSITIONS, Task, TaskStatus


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_bulk(self, issue_id: str, tasks: list[dict]) -> list[Task]:
        created = []
        for i, t in enumerate(tasks):
            task = Task(issue_id=issue_id, name=t["name"], order=i)
            self.session.add(task)
            created.append(task)
        await self.session.flush()
        return created

    async def replace_all(self, issue_id: str, tasks: list[dict]) -> list[Task]:
        await self.session.execute(
            delete(Task).where(Task.issue_id == issue_id)
        )
        return await self.create_bulk(issue_id, tasks)

    async def get_by_id(self, task_id: str) -> Task:
        task = await self.session.get(Task, task_id)
        if task is None:
            raise ValueError("Task not found")
        return task

    async def update(self, task_id: str, **kwargs) -> Task:
        task = await self.get_by_id(task_id)
        if "status" in kwargs and kwargs["status"] is not None:
            new_status = kwargs["status"]
            if isinstance(new_status, str):
                new_status = TaskStatus(new_status)
            if (task.status, new_status) not in VALID_TASK_TRANSITIONS:
                raise ValueError(f"Invalid task transition from {task.status.value} to {new_status.value}")
            task.status = new_status
        if "name" in kwargs and kwargs["name"] is not None:
            task.name = kwargs["name"]
        await self.session.flush()
        return task

    async def delete(self, task_id: str) -> bool:
        task = await self.get_by_id(task_id)
        await self.session.delete(task)
        await self.session.flush()
        return True

    async def list_by_issue(self, issue_id: str) -> list[Task]:
        result = await self.session.execute(
            select(Task).where(Task.issue_id == issue_id).order_by(Task.order.asc())
        )
        return list(result.scalars().all())
