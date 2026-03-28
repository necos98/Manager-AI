from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project_variable import ProjectVariable


class ProjectVariableService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, project_id: str) -> list[ProjectVariable]:
        result = await self.session.execute(
            select(ProjectVariable)
            .where(ProjectVariable.project_id == project_id)
            .order_by(ProjectVariable.sort_order, ProjectVariable.id)
        )
        return list(result.scalars().all())

    async def create(
        self, project_id: str, name: str, value: str, is_secret: bool = False
    ) -> ProjectVariable:
        existing = await self.session.execute(
            select(ProjectVariable)
            .where(ProjectVariable.project_id == project_id)
            .where(ProjectVariable.name == name)
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"Variable '{name}' already exists for this project")

        row = ProjectVariable(
            project_id=project_id, name=name, value=value, is_secret=is_secret
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(self, var_id: int, **kwargs) -> ProjectVariable:
        row = await self.session.get(ProjectVariable, var_id)
        if row is None:
            raise KeyError(f"ProjectVariable {var_id} not found")
        for key, val in kwargs.items():
            if val is not None:
                setattr(row, key, val)
        await self.session.flush()
        return row

    async def delete(self, var_id: int) -> None:
        row = await self.session.get(ProjectVariable, var_id)
        if row is None:
            raise KeyError(f"ProjectVariable {var_id} not found")
        await self.session.delete(row)
        await self.session.flush()
