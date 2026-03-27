from datetime import datetime

from pydantic import BaseModel, Field

from app.models.issue import IssueStatus
from app.schemas.task import TaskResponse


class IssueCreate(BaseModel):
    description: str = Field(..., min_length=1)
    priority: int = Field(default=3, ge=1, le=5)


class IssueUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, min_length=1)
    priority: int | None = Field(None, ge=1, le=5)


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueCompleteBody(BaseModel):
    recap: str = Field(..., min_length=1)


class IssueResponse(BaseModel):
    id: str
    project_id: str
    name: str | None
    description: str
    status: IssueStatus
    priority: int
    plan: str | None
    specification: str | None = None
    recap: str | None
    tasks: list[TaskResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IssueFeedbackCreate(BaseModel):
    content: str = Field(..., min_length=1)


class IssueFeedbackResponse(BaseModel):
    id: str
    issue_id: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
