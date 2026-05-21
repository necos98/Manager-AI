from datetime import datetime

from pydantic import BaseModel, Field


class CredentialsEnvUpdate(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)


class CredentialsEnvOut(BaseModel):
    variables: dict[str, str]


class CredentialPresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    variables: dict[str, str] = Field(default_factory=dict)


class CredentialPresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    variables: dict[str, str] | None = None


class CredentialPresetOut(BaseModel):
    id: str
    name: str
    variables: dict[str, str]
    has_secrets: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
