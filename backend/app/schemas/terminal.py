from datetime import datetime

from pydantic import BaseModel


class TerminalCreate(BaseModel):
    issue_id: str
    project_id: str
    run_commands: bool = True
    command: str | None = None


class LogTerminalCreate(BaseModel):
    project_id: str
    issue_id: str
    label: str = ""


class AskTerminalCreate(BaseModel):
    project_id: str


class ManageAgentTerminalCreate(BaseModel):
    pass


class TerminalResponse(BaseModel):
    id: str
    issue_id: str
    project_id: str
    project_path: str
    status: str
    created_at: datetime
    cols: int
    rows: int


class TerminalListResponse(BaseModel):
    id: str
    issue_id: str
    project_id: str
    project_path: str
    issue_name: str | None = None
    project_name: str | None = None
    status: str
    created_at: datetime
