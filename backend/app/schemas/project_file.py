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
    extraction_status: str = "pending"
    extraction_error: str | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, obj: Any, *, project_id: str | None = None) -> "ProjectFileResponse":
        # Support both ORM (ProjectFile) and dataclass (FileRecord) shapes.
        meta = getattr(obj, "file_metadata", None)
        if meta is None:
            meta = getattr(obj, "metadata", None)
        pid = project_id if project_id is not None else getattr(obj, "project_id", "")
        return cls(
            id=obj.id,
            project_id=pid,
            original_name=obj.original_name,
            stored_name=obj.stored_name,
            file_type=obj.file_type,
            file_size=obj.file_size,
            mime_type=obj.mime_type,
            metadata=meta,
            extraction_status=getattr(obj, "extraction_status", "pending") or "pending",
            extraction_error=getattr(obj, "extraction_error", None),
            created_at=_coerce_dt(obj.created_at),
        )

    model_config = {"from_attributes": True}


def _coerce_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min
    return datetime.fromisoformat(str(value))
