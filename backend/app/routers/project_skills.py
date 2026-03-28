from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.library import ProjectSkillAssign, ProjectSkillOut
from app.services.project_service import ProjectService
from app.services.skill_library_service import SkillLibraryService

router = APIRouter(prefix="/api/projects/{project_id}/skills", tags=["project-skills"])


def _skill_file_synced(project_path: str | None, name: str, type: str) -> bool:
    if not project_path:
        return False
    from pathlib import Path
    subdir = "skills" if type == "skill" else "agents"
    return (Path(project_path) / ".claude" / subdir / f"{name}.md").exists()


@router.get("", response_model=list[ProjectSkillOut])
async def list_project_skills(project_id: str, db: AsyncSession = Depends(get_db)):
    project = await ProjectService(db).get_by_id(project_id)
    svc = SkillLibraryService(db)
    skills = await svc.list_assigned(project_id)
    return [
        ProjectSkillOut(
            id=s.id,
            project_id=s.project_id,
            name=s.name,
            type=s.type,
            assigned_at=s.assigned_at.isoformat(),
            file_synced=_skill_file_synced(project.path, s.name, s.type),
        )
        for s in skills
    ]


@router.post("", response_model=ProjectSkillOut, status_code=201)
async def assign_skill(
    project_id: str, data: ProjectSkillAssign, db: AsyncSession = Depends(get_db)
):
    project = await ProjectService(db).get_by_id(project_id)
    svc = SkillLibraryService(db)
    skill = await svc.assign(project_id, project.path, data.name, data.type)
    await db.commit()
    return ProjectSkillOut(
        id=skill.id,
        project_id=skill.project_id,
        name=skill.name,
        type=skill.type,
        assigned_at=skill.assigned_at.isoformat(),
        file_synced=_skill_file_synced(project.path, skill.name, skill.type),
    )


@router.delete("/{type}/{name}", status_code=204)
async def unassign_skill(
    project_id: str, type: str, name: str, db: AsyncSession = Depends(get_db)
):
    project = await ProjectService(db).get_by_id(project_id)
    svc = SkillLibraryService(db)
    await svc.unassign(project_id, project.path, name, type)
    await db.commit()
