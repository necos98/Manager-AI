from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    parent_id: str | None = None


class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    parent_id: str | None = None


class MemoryResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    parent_id: str | None
    created_at: datetime
    updated_at: datetime
    children_count: int = 0
    links_out_count: int = 0
    links_in_count: int = 0

    @classmethod
    def from_model(cls, obj: Any, *, children_count: int = 0, links_out_count: int = 0, links_in_count: int = 0) -> "MemoryResponse":
        return cls(
            id=obj.id,
            project_id=obj.project_id,
            title=obj.title,
            description=obj.description,
            parent_id=obj.parent_id,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            children_count=children_count,
            links_out_count=links_out_count,
            links_in_count=links_in_count,
        )

    model_config = {"from_attributes": True}


class MemoryLinkResponse(BaseModel):
    from_id: str
    to_id: str
    relation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryDetail(MemoryResponse):
    parent: MemoryResponse | None = None
    children: list[MemoryResponse] = []
    links_out: list[MemoryLinkResponse] = []
    links_in: list[MemoryLinkResponse] = []


class MemorySearchHit(BaseModel):
    memory: MemoryResponse
    snippet: str
    rank: float
