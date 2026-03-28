from pydantic import BaseModel


class ProjectSettingSet(BaseModel):
    value: str


class ProjectSettingOut(BaseModel):
    key: str
    value: str
