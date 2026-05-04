from __future__ import annotations

from datetime import datetime
from typing import Any

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

    @classmethod
    def from_record(cls, record: Any, *, issue_id: str) -> "TaskResponse":
        return cls(
            id=record.id,
            issue_id=issue_id,
            name=record.name,
            status=TaskStatus(record.status),
            order=record.order,
            created_at=_parse_dt(record.created_at),
            updated_at=_parse_dt(record.updated_at),
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min
    return datetime.fromisoformat(str(value))
