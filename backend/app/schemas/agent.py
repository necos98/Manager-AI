from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role_key: str = Field(..., min_length=1, max_length=100)
    system_prompt: str = ""


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    system_prompt: str | None = None
    enabled: bool | None = None


class AgentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    role_key: str
    system_prompt: str
    enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, agent: Any) -> "AgentResponse":
        return cls(
            id=agent.id,
            project_id=agent.project_id,
            name=agent.name,
            role_key=agent.role_key,
            system_prompt=agent.system_prompt,
            enabled=bool(agent.enabled),
            created_at=_parse_dt(agent.created_at),
            updated_at=_parse_dt(agent.updated_at),
        )


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
