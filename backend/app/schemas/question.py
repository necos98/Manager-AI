from datetime import datetime

from pydantic import BaseModel


class QuestionCreate(BaseModel):
    project_id: str
    issue_id: str
    question: str
    options: list[str] | None = None


class QuestionAnswer(BaseModel):
    answer: str
    selected_option: str | None = None


class QuestionResponse(BaseModel):
    id: str
    project_id: str
    issue_id: str
    question: str
    options: list[str] | None
    status: str
    answer: str | None
    selected_option: str | None
    created_at: datetime | None
    answered_at: datetime | None

    model_config = {"from_attributes": True}
