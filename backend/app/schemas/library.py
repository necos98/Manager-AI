from pydantic import BaseModel


class SkillMeta(BaseModel):
    name: str
    category: str
    description: str
    built_in: bool
    type: str  # "skill" | "agent"


class SkillCreate(BaseModel):
    name: str
    category: str
    description: str
    content: str


class SkillDetail(SkillMeta):
    content: str


class SkillContentUpdate(BaseModel):
    content: str


class ProjectSkillOut(BaseModel):
    id: int
    project_id: str
    name: str
    type: str
    assigned_at: str
    file_synced: bool = False


class ProjectSkillAssign(BaseModel):
    name: str
    type: str  # "skill" | "agent"
