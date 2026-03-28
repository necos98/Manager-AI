from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.project_variable import ProjectVariableCreate, ProjectVariableOut, ProjectVariableUpdate
from app.services.project_variable_service import ProjectVariableService

router = APIRouter(prefix="/api/project-variables", tags=["project-variables"])


@router.get("", response_model=list[ProjectVariableOut])
async def list_project_variables(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    return await svc.list(project_id)


@router.post("", response_model=ProjectVariableOut, status_code=201)
async def create_project_variable(
    project_id: str,
    data: ProjectVariableCreate,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    try:
        var = await svc.create(project_id, name=data.name, value=data.value, is_secret=data.is_secret)
        await db.commit()
        return var
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/{var_id}", response_model=ProjectVariableOut)
async def update_project_variable(
    var_id: int,
    data: ProjectVariableUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    try:
        var = await svc.update(var_id, **data.model_dump(exclude_unset=True))
        await db.commit()
        await db.refresh(var)
        return var
    except KeyError:
        raise HTTPException(status_code=404, detail="Variable not found")


@router.delete("/{var_id}", status_code=204)
async def delete_project_variable(
    var_id: int,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectVariableService(db)
    try:
        await svc.delete(var_id)
        await db.commit()
    except KeyError:
        raise HTTPException(status_code=404, detail="Variable not found")
