from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.setting import SettingOut, SettingUpdate
from app.services.settings_service import SettingsService
from app.services.telegram_service import telegram_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _reconfigure_telegram(service: SettingsService) -> None:
    """Re-read the three telegram settings from DB and apply them."""
    try:
        bot_token = await service.get("telegram.bot_token")
    except KeyError:
        bot_token = ""
    try:
        chat_id = await service.get("telegram.chat_id")
    except KeyError:
        chat_id = ""
    try:
        enabled_str = await service.get("telegram.notifications_enabled")
        notifications_enabled = enabled_str == "true"
    except KeyError:
        notifications_enabled = False

    telegram_service.configure(
        bot_token=bot_token,
        chat_id=chat_id,
        enabled=notifications_enabled,
    )


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


@router.get("/{key}", response_model=SettingOut)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    try:
        return await service.get_one(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Setting not found")


@router.put("/{key}", response_model=SettingOut)
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    try:
        await service.set(key, data.value)
        await db.commit()

        # If a Telegram setting was changed, reload all three values
        # into the singleton so the change takes effect immediately.
        if key.startswith("telegram."):
            await _reconfigure_telegram(service)

        return await service.get_one(key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Setting not found")


@router.delete("/{key}", status_code=204)
async def reset_setting(key: str, db: AsyncSession = Depends(get_db)):
    service = SettingsService(db)
    await service.reset(key)
    await db.commit()
