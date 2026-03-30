from pydantic import BaseModel


class TemplateInfo(BaseModel):
    type: str
    content: str
    is_overridden: bool


class TemplateSave(BaseModel):
    content: str
