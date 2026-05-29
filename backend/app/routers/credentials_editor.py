from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.credential_preset import (
    CredentialPresetCreate,
    CredentialPresetOut,
    CredentialPresetUpdate,
    CredentialsEnvUpdate,
)
from app.services.credential_editor_service import CredentialEditorService as SVC

router = APIRouter(prefix="/api/credentials-editor", tags=["credentials-editor"])


@router.get("")
async def read_env():
    svc = SVC.__new__(SVC)
    return {"variables": svc.read_env()}


@router.put("")
async def write_env(data: CredentialsEnvUpdate):
    svc = SVC.__new__(SVC)
    return {"variables": svc.write_env(data.variables)}


@router.get("/presets", response_model=list[CredentialPresetOut])
async def list_presets(db: AsyncSession = Depends(get_db)):
    svc = SVC(db)
    presets = await svc.list_presets()
    return [svc.decode_preset(p) for p in presets]


@router.post("/presets", response_model=CredentialPresetOut, status_code=201)
async def create_preset(data: CredentialPresetCreate, db: AsyncSession = Depends(get_db)):
    svc = SVC(db)
    preset = await svc.create_preset(data.name, data.variables)
    await db.commit()
    return svc.decode_preset(preset)


@router.put("/presets/{preset_id}", response_model=CredentialPresetOut)
async def update_preset(preset_id: str, data: CredentialPresetUpdate, db: AsyncSession = Depends(get_db)):
    svc = SVC(db)
    preset = await svc.update_preset(preset_id, data.name, data.variables)
    await db.commit()
    return svc.decode_preset(preset)


@router.delete("/presets/{preset_id}", status_code=204)
async def delete_preset(preset_id: str, db: AsyncSession = Depends(get_db)):
    svc = SVC(db)
    await svc.delete_preset(preset_id)
    await db.commit()


@router.post("/presets/{preset_id}/apply")
async def apply_preset(preset_id: str, db: AsyncSession = Depends(get_db)):
    svc = SVC(db)
    variables = await svc.apply_preset(preset_id)
    await db.commit()
    return {"variables": variables}
