from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    intent: str | None = None
    model: str | None = None
    provider: str | None = Field(None, max_length=50)
    allowed_tools: list[str] | None = None


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    intent: str | None = None
    model: str | None = None
    provider: str | None = Field(None, max_length=50)
    allowed_tools: list[str] | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    intent: str = ""
    model: str | None = None
    provider: str | None = None
    allowed_tools: list[str] | None = None
    created_at: str | None = None
    updated_at: str | None = None
