from datetime import datetime

from pydantic import BaseModel, Field


class ProjectVariableCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    value: str
    is_secret: bool = False


class ProjectVariableUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    value: str | None = None
    is_secret: bool | None = None


class ProjectVariableOut(BaseModel):
    id: int
    project_id: str
    name: str
    value: str
    is_secret: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
