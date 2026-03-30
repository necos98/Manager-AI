from datetime import datetime

from pydantic import BaseModel, Field

from app.models.issue import IssueStatus
from app.schemas.task import TaskResponse

_DESCRIPTION_MAX = 50_000
_RECAP_MAX = 50_000
_SPEC_MAX = 500_000
_PLAN_MAX = 500_000


class IssueCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=_DESCRIPTION_MAX)
    priority: int = Field(default=3, ge=1, le=5)


class IssueUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, min_length=1, max_length=_DESCRIPTION_MAX)
    priority: int | None = Field(None, ge=1, le=5)
    spec: str | None = Field(None, max_length=_SPEC_MAX)
    plan: str | None = Field(None, max_length=_PLAN_MAX)


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueCompleteBody(BaseModel):
    recap: str = Field(..., min_length=1, max_length=_RECAP_MAX)


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
