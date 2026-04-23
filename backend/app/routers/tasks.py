from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError
from app.models.task import TaskStatus
from app.schemas.task import TaskBulkCreate, TaskResponse, TaskUpdate
from app.services.issue_service import IssueService
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/projects/{project_id}/issues/{issue_id}/tasks", tags=["tasks"])


async def _verify_issue(project_id: str, issue_id: str, db: AsyncSession):
    service = IssueService(db)
    try:
        await service.get_for_project(issue_id, project_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Issue not found")


@router.post("", response_model=list[TaskResponse], status_code=201)
async def create_tasks(
    project_id: str, issue_id: str, data: TaskBulkCreate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    tasks = await service.create_bulk(issue_id, [t.model_dump() for t in data.tasks])
    await db.commit()
    return [TaskResponse.from_record(t, issue_id=issue_id) for t in tasks]


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    tasks = await service.list_by_issue(issue_id)
    return [TaskResponse.from_record(t, issue_id=issue_id) for t in tasks]


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: str, issue_id: str, task_id: str, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    try:
        task = await service.update(task_id, **data.model_dump(exclude_unset=True))
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    all_done = False
    if task.status == TaskStatus.COMPLETED.value:
        all_done = await service.all_completed(issue_id)
    await db.commit()
    if all_done:
        from app.database import async_session
        from app.hooks.registry import HookContext, HookEvent, hook_registry
        from app.services.issue_service import IssueService as _IS
        from app.services.project_service import ProjectService
        async with async_session() as session:
            project = await ProjectService(session).get_by_id(project_id)
            fetched_issue = await _IS(session).get_by_id(issue_id)
        await hook_registry.fire(
            HookEvent.ALL_TASKS_COMPLETED,
            HookContext(
                project_id=project_id,
                issue_id=issue_id,
                event=HookEvent.ALL_TASKS_COMPLETED,
                metadata={
                    "issue_name": (fetched_issue.name or "") if fetched_issue else "",
                    "project_name": project.name if project else "",
                    "project_path": project.path if project else "",
                },
            ),
        )
    return TaskResponse.from_record(task, issue_id=issue_id)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    project_id: str, issue_id: str, task_id: str, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    try:
        await service.delete(task_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.commit()


@router.put("", response_model=list[TaskResponse])
async def replace_tasks(
    project_id: str, issue_id: str, data: TaskBulkCreate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    tasks = await service.replace_all(issue_id, [t.model_dump() for t in data.tasks])
    await db.commit()
    return [TaskResponse.from_record(t, issue_id=issue_id) for t in tasks]
