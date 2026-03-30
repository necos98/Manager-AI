from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.issue_relation import RelationType


class IssueRelationCreate(BaseModel):
    target_id: str
    relation_type: RelationType


class IssueRelationResponse(BaseModel):
    id: int
    source_id: str
    target_id: str
    relation_type: RelationType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
