import uuid

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import VALID_TRANSITIONS, Task, TaskStatus


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, project_id: uuid.UUID, description: str, priority: int = 3) -> Task:
        task = Task(project_id=project_id, description=description, priority=priority)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return await self.session.get(Task, task_id)

    async def _get_task_for_project(self, task_id: uuid.UUID, project_id: uuid.UUID) -> Task:
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError("Task not found")
        if task.project_id != project_id:
            raise PermissionError("Task does not belong to project")
        return task

    async def list_by_project(
        self, project_id: uuid.UUID, status: TaskStatus | None = None
    ) -> list[Task]:
        query = select(Task).where(Task.project_id == project_id)
        if status is not None:
            query = query.where(Task.status == status)
        query = query.order_by(Task.priority.asc(), Task.created_at.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_next_task(self, project_id: uuid.UUID) -> Task | None:
        query = (
            select(Task)
            .where(Task.project_id == project_id)
            .where(Task.status.in_([TaskStatus.NEW, TaskStatus.DECLINED]))
            .order_by(
                case(
                    (Task.status == TaskStatus.DECLINED, 0),
                    (Task.status == TaskStatus.NEW, 1),
                ).asc(),
                Task.priority.asc(),
                Task.created_at.asc(),
            )
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        task_id: uuid.UUID,
        project_id: uuid.UUID,
        new_status: TaskStatus,
        decline_feedback: str | None = None,
    ) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
        if new_status == TaskStatus.CANCELED:
            task.status = TaskStatus.CANCELED
            await self.session.flush()
            return task
        if (task.status, new_status) not in VALID_TRANSITIONS:
            raise ValueError(f"Invalid state transition from {task.status.value} to {new_status.value}")
        task.status = new_status
        if new_status == TaskStatus.DECLINED and decline_feedback:
            task.decline_feedback = decline_feedback
        await self.session.flush()
        return task

    async def update_fields(self, task_id: uuid.UUID, project_id: uuid.UUID, **kwargs) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(task, key, value)
        await self.session.flush()
        return task

    async def set_name(self, task_id: uuid.UUID, project_id: uuid.UUID, name: str) -> Task:
        return await self.update_fields(task_id, project_id, name=name)

    async def save_plan(self, task_id: uuid.UUID, project_id: uuid.UUID, plan: str) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
        if task.status not in (TaskStatus.NEW, TaskStatus.DECLINED):
            raise ValueError(f"Can only save plan for tasks in New or Declined status, got {task.status.value}")
        task.plan = plan
        task.status = TaskStatus.PLANNED
        await self.session.flush()
        return task

    async def complete_task(self, task_id: uuid.UUID, project_id: uuid.UUID, recap: str) -> Task:
        task = await self._get_task_for_project(task_id, project_id)
        if task.status != TaskStatus.ACCEPTED:
            raise ValueError(f"Can only complete tasks in Accepted status, got {task.status.value}")
        task.recap = recap
        task.status = TaskStatus.FINISHED
        await self.session.flush()
        return task

    async def delete(self, task_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        task = await self._get_task_for_project(task_id, project_id)
        await self.session.delete(task)
        await self.session.flush()
        return True
