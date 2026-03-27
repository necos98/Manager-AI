from datetime import datetime
from typing import Any, Optional
import json

from pydantic import BaseModel, ConfigDict, field_validator


class ActivityLogResponse(BaseModel):
    id: str
    project_id: str
    issue_id: Optional[str]
    event_type: str
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("details", mode="before")
    @classmethod
    def parse_details(cls, v: Any) -> dict:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}
