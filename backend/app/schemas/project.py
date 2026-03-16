import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    path: str
    description: str
    created_at: datetime
    updated_at: datetime
    task_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
