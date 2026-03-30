from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting


class ProjectSettingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _key(self, project_id: str, key: str) -> str:
        return f"project:{project_id}:{key}"

    async def get(self, project_id: str, key: str, default: str = "") -> str:
        row = await self.session.get(Setting, self._key(project_id, key))
        return row.value if row else default

    async def set(self, project_id: str, key: str, value: str) -> None:
        full_key = self._key(project_id, key)
        row = await self.session.get(Setting, full_key)
        if row is None:
            self.session.add(Setting(key=full_key, value=value))
        else:
            row.value = value
        await self.session.flush()

    async def delete(self, project_id: str, key: str) -> None:
        row = await self.session.get(Setting, self._key(project_id, key))
        if row is not None:
            await self.session.delete(row)
            await self.session.flush()

    async def get_all_for_project(self, project_id: str) -> dict[str, str]:
        prefix = f"project:{project_id}:"
        result = await self.session.execute(
            select(Setting).where(Setting.key.like(f"{prefix}%"))
        )
        return {row.key[len(prefix):]: row.value for row in result.scalars().all()}
