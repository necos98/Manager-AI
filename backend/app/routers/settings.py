from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.setting import SettingOut, SettingUpdate
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=list[SettingOut])
async def list_settings(db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    return await service.get_all()


# IMPORTANT: DELETE "" must be registered BEFORE DELETE "/{key}"
# so FastAPI matches the exact root path before the parameterized one.
@router.delete("", status_code=204)
async def reset_all_settings(db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    await service.reset_all()
    await db.commit()


@router.put("/{key}", response_model=SettingOut)
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    try:
        await service.set(key, data.value)
        await db.commit()
        return await service.get_one(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Setting not found")


@router.delete("/{key}", status_code=204)
async def reset_setting(key: str, db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    await service.reset(key)
    await db.commit()
