from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentMessageCreate(BaseModel):
    issue_id: str
    content: str = Field(..., min_length=1)
    message_type: str = "context"


class AgentMessageResponse(BaseModel):
    id: str
    issue_id: str
    agent_name: str
    agent_role: str
    content: str
    message_type: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
