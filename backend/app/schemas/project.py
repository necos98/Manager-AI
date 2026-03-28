from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    tech_stack: str = ""
    shell: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    tech_stack: str | None = None
    shell: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    path: str
    description: str
    tech_stack: str
    shell: str | None = None
    created_at: datetime
    updated_at: datetime
    issue_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
