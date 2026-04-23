from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from app.models.issue_relation import RelationType


class IssueRelationCreate(BaseModel):
    target_id: str
    relation_type: RelationType


class IssueRelationResponse(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    created_at: datetime

    @classmethod
    def from_record(cls, *, source_id: str, target_id: str, relation_type: str, created_at: Any) -> "IssueRelationResponse":
        return cls(
            id=make_relation_id(source_id, target_id, relation_type),
            source_id=source_id,
            target_id=target_id,
            relation_type=RelationType(relation_type),
            created_at=_parse_dt(created_at),
        )


def make_relation_id(source_id: str, target_id: str, relation_type: str) -> str:
    """Deterministic id for a file-backed relation (source + target + type)."""
    digest = hashlib.sha1(f"{source_id}|{target_id}|{relation_type}".encode("utf-8")).hexdigest()
    return digest[:16]


def parse_relation_id(relation_id: str, candidates: list[tuple[str, str, str]]) -> tuple[str, str, str] | None:
    """Reverse-lookup: given an id and the set of candidate (source, target, type)
    tuples, return the matching tuple or None."""
    for source, target, rtype in candidates:
        if make_relation_id(source, target, rtype) == relation_id:
            return source, target, rtype
    return None


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min
    return datetime.fromisoformat(str(value))
