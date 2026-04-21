import os
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_path(v: str | None) -> str | None:
    if v is None:
        return v
    p = os.path.expanduser(v.strip())
    if not os.path.isabs(p):
        raise ValueError(f"path must be absolute, got: {v!r}")
    return os.path.normpath(p)


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    tech_stack: str = ""
    shell: str | None = None

    @field_validator("path")
    @classmethod
    def _norm_path(cls, v: str) -> str:
        return _normalize_path(v)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    tech_stack: str | None = None
    shell: str | None = None

    @field_validator("path")
    @classmethod
    def _norm_path(cls, v: str | None) -> str | None:
        return _normalize_path(v)


class ProjectResponse(BaseModel):
    id: str
    name: str
    path: str
    description: str
    tech_stack: str
    shell: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None
    issue_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}


class DashboardIssue(BaseModel):
    id: str
    name: str | None
    description: str
    status: str
    priority: int
    model_config = ConfigDict(from_attributes=True)


class DashboardProject(BaseModel):
    id: str
    name: str
    path: str
    active_issues: list[DashboardIssue]
    model_config = ConfigDict(from_attributes=True)
