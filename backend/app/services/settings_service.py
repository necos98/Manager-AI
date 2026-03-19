import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.schemas.setting import SettingOut

_DEFAULTS_PATH = Path(__file__).parent.parent / "mcp" / "default_settings.json"
_DEFAULTS: dict[str, str] = json.loads(_DEFAULTS_PATH.read_text(encoding="utf-8"))


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str) -> str:
        """Returns DB value if row exists, otherwise the JSON default.
        Raises KeyError if key is not in default_settings.json."""
        if key not in _DEFAULTS:
            raise KeyError(f"Unknown setting key: {key!r}")
        row = await self.session.get(Setting, key)
        if row is not None:
            return row.value
        return _DEFAULTS[key]

    async def get_one(self, key: str) -> SettingOut:
        """Returns a single SettingOut. Raises KeyError if key not in JSON."""
        if key not in _DEFAULTS:
            raise KeyError(f"Unknown setting key: {key!r}")
        row = await self.session.get(Setting, key)
        default = _DEFAULTS[key]
        is_customized = row is not None
        return SettingOut(
            key=key,
            value=row.value if is_customized else default,
            default=default,
            is_customized=is_customized,
        )

    async def get_all(self) -> list[SettingOut]:
        """Returns all settings from JSON, merging DB overrides.
        DB rows with keys not in JSON are ignored."""
        result = await self.session.execute(select(Setting))
        db_rows = {row.key: row.value for row in result.scalars().all()}
        return [
            SettingOut(
                key=key,
                value=db_rows[key] if key in db_rows else default,
                default=default,
                is_customized=key in db_rows,
            )
            for key, default in _DEFAULTS.items()
        ]

    async def set(self, key: str, value: str) -> Setting:
        """Upserts a setting row. Raises KeyError if key not in JSON."""
        if key not in _DEFAULTS:
            raise KeyError(f"Unknown setting key: {key!r}")
        row = await self.session.get(Setting, key)
        if row is None:
            row = Setting(key=key, value=value)
            self.session.add(row)
        else:
            row.value = value
        await self.session.flush()
        return row

    async def reset(self, key: str) -> None:
        """Deletes the DB row for this key. Idempotent."""
        row = await self.session.get(Setting, key)
        if row is not None:
            await self.session.delete(row)
            await self.session.flush()

    async def reset_all(self) -> None:
        """Deletes all rows from the settings table via ORM-level deletes."""
        result = await self.session.execute(select(Setting))
        for row in result.scalars().all():
            await self.session.delete(row)
        await self.session.flush()
