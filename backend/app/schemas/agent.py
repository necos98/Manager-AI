from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=1)
    model: str | None = None
    allowed_tools: list[str] | None = None


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    system_prompt: str | None = None
    model: str | None = None
    allowed_tools: list[str] | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    system_prompt: str
    model: str | None = None
    allowed_tools: list[str] | None = None
    created_at: str | None = None
    updated_at: str | None = None
