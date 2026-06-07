from pydantic import BaseModel, Field


class PipelineEventRuleResponse(BaseModel):
    id: str
    pipeline_id: str
    event_type: str
    source_step_id: str
    target_step_id: str
    enabled: bool
    created_at: str | None = None
    updated_at: str | None = None


class PipelineEventRuleCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    source_step_id: str = Field(..., min_length=1)
    target_step_id: str = Field(..., min_length=1)
