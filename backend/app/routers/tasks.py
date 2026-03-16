import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/projects/{project_id}/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(project_id: uuid.UUID, data: TaskCreate, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.create(project_id=project_id, description=data.description, priority=data.priority)
    await db.commit()
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: uuid.UUID,
    status: TaskStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.list_by_project(project_id, status=status)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(project_id: uuid.UUID, task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    try:
        task = await service.get_for_project(task_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    project_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    service = TaskService(db)
    try:
        task = await service.update_fields(task_id, project_id, **data.model_dump(exclude_unset=True))
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    data: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    try:
        task = await service.update_status(
            task_id, project_id, data.status, decline_feedback=data.decline_feedback
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(project_id: uuid.UUID, task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    try:
        await service.delete(task_id, project_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Resource not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await db.commit()
