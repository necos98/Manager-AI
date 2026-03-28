from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TerminalCommandCreate(BaseModel):
    command: str = Field(..., min_length=1)
    sort_order: int
    project_id: str | None = None
    condition: str | None = None
    # Note: newlines are now allowed to support multi-line command blocks


class TerminalCommandUpdate(BaseModel):
    command: str | None = Field(None, min_length=1)
    sort_order: int | None = None
    condition: Optional[str] = None


class TerminalCommandOut(BaseModel):
    id: int
    command: str
    sort_order: int
    project_id: str | None
    condition: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class TerminalCommandReorder(BaseModel):
    commands: list[ReorderItem]
