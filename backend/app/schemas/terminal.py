from datetime import datetime

from pydantic import BaseModel


class TerminalCreate(BaseModel):
    task_id: str
    project_id: str


class TerminalResponse(BaseModel):
    id: str
    task_id: str
    project_id: str
    project_path: str
    status: str
    created_at: datetime
    cols: int
    rows: int


class TerminalListResponse(BaseModel):
    id: str
    task_id: str
    project_id: str
    project_path: str
    task_name: str | None = None
    project_name: str | None = None
    status: str
    created_at: datetime
