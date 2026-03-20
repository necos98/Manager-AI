from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TaskBulkCreate(BaseModel):
    tasks: list[TaskCreate] = Field(..., min_length=1)


class TaskUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    status: TaskStatus | None = None


class TaskResponse(BaseModel):
    id: str
    issue_id: str
    name: str
    status: TaskStatus
    order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
