from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ProjectFileResponse(BaseModel):
    id: str
    project_id: str
    original_name: str
    stored_name: str
    file_type: str
    file_size: int
    mime_type: str
    metadata: dict[str, Any] | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, obj: Any) -> "ProjectFileResponse":
        return cls(
            id=obj.id,
            project_id=obj.project_id,
            original_name=obj.original_name,
            stored_name=obj.stored_name,
            file_type=obj.file_type,
            file_size=obj.file_size,
            mime_type=obj.mime_type,
            metadata=obj.file_metadata,
            created_at=obj.created_at,
        )

    model_config = {"from_attributes": True}
