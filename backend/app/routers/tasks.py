from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskBulkCreate, TaskResponse, TaskUpdate
from app.services.issue_service import IssueService
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/projects/{project_id}/issues/{issue_id}/tasks", tags=["tasks"])


async def _verify_issue(project_id: str, issue_id: str, db: AsyncSession):
    service = IssueService(db)
    try:
        await service.get_for_project(issue_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Issue not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("", response_model=list[TaskResponse], status_code=201)
async def create_tasks(
    project_id: str, issue_id: str, data: TaskBulkCreate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    tasks = await service.create_bulk(issue_id, [t.model_dump() for t in data.tasks])
    await db.commit()
    for t in tasks:
        await db.refresh(t)
    return tasks


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    return await service.list_by_issue(issue_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: str, issue_id: str, task_id: str, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    try:
        task = await service.update(task_id, **data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    all_done = False
    if task.status.value == "Completed":
        all_done = await service.all_completed(issue_id)
    await db.commit()
    await db.refresh(task)
    if all_done:
        from app.database import async_session
        from app.hooks.registry import HookContext, HookEvent, hook_registry
        from app.services.project_service import ProjectService
        async with async_session() as session:
            project = await ProjectService(session).get_by_id(project_id)
        await hook_registry.fire(
            HookEvent.ALL_TASKS_COMPLETED,
            HookContext(
                project_id=project_id,
                issue_id=issue_id,
                event=HookEvent.ALL_TASKS_COMPLETED,
                metadata={
                    "project_name": project.name if project else "",
                    "project_path": project.path if project else "",
                },
            ),
        )
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    project_id: str, issue_id: str, task_id: str, db: AsyncSession = Depends(get_db)
):
    await _verify_issue(project_id, issue_id, db)
    service = TaskService(db)
    try:
        await service.delete(task_id)
    except ValueError:
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
    for t in tasks:
        await db.refresh(t)
    return tasks
