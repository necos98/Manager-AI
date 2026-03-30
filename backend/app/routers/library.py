from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.library import SkillContentUpdate, SkillCreate, SkillDetail, SkillMeta
from app.services.skill_library_service import SkillLibraryService

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("/skills", response_model=list[SkillMeta])
async def list_skills(db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).list_available("skill")


@router.get("/agents", response_model=list[SkillMeta])
async def list_agents(db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).list_available("agent")


@router.get("/skills/{name}", response_model=SkillDetail)
async def get_skill(name: str, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).get_content(name, "skill")


@router.get("/agents/{name}", response_model=SkillDetail)
async def get_agent(name: str, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).get_content(name, "agent")


@router.post("/skills", response_model=SkillMeta, status_code=201)
async def create_skill(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).create(data, "skill")


@router.post("/agents", response_model=SkillMeta, status_code=201)
async def create_agent(data: SkillCreate, db: AsyncSession = Depends(get_db)):
    return SkillLibraryService(db).create(data, "agent")


@router.put("/skills/{name}", status_code=204)
async def update_skill(name: str, data: SkillContentUpdate, db: AsyncSession = Depends(get_db)):
    SkillLibraryService(db).update_content(name, "skill", data.content)


@router.put("/agents/{name}", status_code=204)
async def update_agent(name: str, data: SkillContentUpdate, db: AsyncSession = Depends(get_db)):
    SkillLibraryService(db).update_content(name, "agent", data.content)
