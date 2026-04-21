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
    has_value: bool = True
    is_secret: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def variable_to_out(row, reveal: bool = False) -> "ProjectVariableOut":
    """Build a ProjectVariableOut from an ORM row, masking value when the
    row is flagged as secret and `reveal` is False."""
    has_value = bool(row.value)
    masked_value = "" if (row.is_secret and not reveal) else row.value
    return ProjectVariableOut(
        id=row.id,
        project_id=row.project_id,
        name=row.name,
        value=masked_value,
        has_value=has_value,
        is_secret=row.is_secret,
        sort_order=row.sort_order,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
