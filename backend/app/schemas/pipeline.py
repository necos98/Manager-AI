from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.pipeline import AgentStepStatus, PipelineRunStatus


class PipelineStep(BaseModel):
    agent_id: str
    order: int


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    steps: list[PipelineStep] = Field(default_factory=list)
    is_default: bool = False
    trigger_type: str = "issue_accepted"


class PipelineUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    steps: list[PipelineStep] | None = None
    is_default: bool | None = None
    trigger_type: str | None = None


class PipelineResponse(BaseModel):
    id: str
    project_id: str
    name: str
    steps: list[PipelineStep]
    is_default: bool
    trigger_type: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PipelineRunResponse(BaseModel):
    id: str
    pipeline_id: str
    issue_id: str | None
    trigger_type: str
    status: PipelineRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentStepRunResponse(BaseModel):
    id: str
    pipeline_run_id: str
    agent_id: str
    agent_name: str
    agent_role: str
    step_order: int
    status: AgentStepStatus
    summary: str | None = None
    error: str | None = None
    terminal_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PipelineRunFullResponse(BaseModel):
    run: PipelineRunResponse
    steps: list[AgentStepRunResponse]
