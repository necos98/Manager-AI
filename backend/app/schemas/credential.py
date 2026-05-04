from pydantic import BaseModel, Field


class CredentialUpsert(BaseModel):
    role: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=2000)
    fields: dict = Field(default_factory=dict)


class CredentialResponse(BaseModel):
    id: str
    project_id: str
    role: str
    url: str
    fields: dict
    created_at: str | None = None
    updated_at: str | None = None
