from pydantic import BaseModel, Field


class SettingOut(BaseModel):
    key: str
    value: str           # active value (DB if customized, else default)
    default: str         # original value from default_settings.json
    is_customized: bool  # True if a DB row exists for this key

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    value: str = Field(..., min_length=1)
