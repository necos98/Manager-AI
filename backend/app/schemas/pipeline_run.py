from pydantic import BaseModel, Field


class PipelineRunStart(BaseModel):
    pipeline_id: str = Field(..., min_length=1)
    issue_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)


class PipelineStepRunResponse(BaseModel):
    id: str
    pipeline_run_id: str
    pipeline_step_id: str
    agent_name: str
    status: str
    terminal_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class PipelineRunResponse(BaseModel):
    id: str
    pipeline_id: str
    pipeline_name: str = ""
    issue_id: str
    status: str
    current_step_index: int
    steps: list[PipelineStepRunResponse] = []
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str | None = None


class ActivePipelineRunResponse(BaseModel):
    pipeline_name: str
    status: str


class PipelineMessageCreate(BaseModel):
    sender_agent_name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class PipelineMessageResponse(BaseModel):
    id: str
    pipeline_run_id: str
    sender_agent_name: str
    content: str
    created_at: str | None = None


class StartStepRequest(BaseModel):
    run_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)


class StartStepResponse(BaseModel):
    term_id: str
    agent_name: str
    agent_intent: str = ""
    step_index: int
    step_run_id: str


class AdvancePipelineResponse(BaseModel):
    status: str
    next_step_index: int | None = None
    pipeline_finished: bool = False


class PipelineControlResponse(BaseModel):
    status: str
