from pydantic import BaseModel, Field


class PipelineStepCreate(BaseModel):
    agent_id: str = Field(..., min_length=1)
    order_index: int = Field(default=0, ge=0)
    terminal_command: str = ""


class PipelineStepResponse(BaseModel):
    id: str
    pipeline_id: str
    agent_id: str
    order_index: int
    terminal_command: str


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    steps: list[PipelineStepCreate] = []


class PipelineUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class PipelineResponse(BaseModel):
    id: str
    name: str
    steps: list[PipelineStepResponse] = []
    created_at: str | None = None
    updated_at: str | None = None


class StepReorderRequest(BaseModel):
    step_ids: list[str] = Field(..., min_length=1)
