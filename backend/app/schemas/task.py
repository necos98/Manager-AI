from datetime import datetime

from pydantic import BaseModel, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    description: str = Field(..., min_length=1)
    priority: int = Field(default=3, ge=1, le=5)


class TaskUpdate(BaseModel):
    description: str | None = Field(None, min_length=1)
    priority: int | None = Field(None, ge=1, le=5)


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    decline_feedback: str | None = None


class TaskResponse(BaseModel):
    id: str
    project_id: str
    name: str | None
    description: str
    status: TaskStatus
    priority: int
    plan: str | None
    specification: str | None = None
    recap: str | None
    decline_feedback: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
