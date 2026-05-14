from datetime import datetime

from pydantic import BaseModel


class ProjectLinkCreate(BaseModel):
    target_project_id: str
    description: str


class ProjectLinkUpdate(BaseModel):
    description: str


class ProjectLinkResponse(BaseModel):
    id: str
    source_project_id: str
    source_project_name: str
    target_project_id: str
    target_project_name: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
