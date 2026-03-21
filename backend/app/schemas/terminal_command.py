from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TerminalCommandCreate(BaseModel):
    command: str = Field(..., min_length=1)
    sort_order: int
    project_id: str | None = None

    @field_validator("command")
    @classmethod
    def no_newlines(cls, v):
        if "\n" in v or "\r" in v:
            raise ValueError("Command must not contain newlines")
        return v


class TerminalCommandUpdate(BaseModel):
    command: str | None = Field(None, min_length=1)
    sort_order: int | None = None

    @field_validator("command")
    @classmethod
    def no_newlines(cls, v):
        if v is not None and ("\n" in v or "\r" in v):
            raise ValueError("Command must not contain newlines")
        return v


class TerminalCommandOut(BaseModel):
    id: int
    command: str
    sort_order: int
    project_id: str | None
    created_at: datetime
    updated_at: datetime


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class TerminalCommandReorder(BaseModel):
    commands: list[ReorderItem]
