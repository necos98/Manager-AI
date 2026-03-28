from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.terminal_command import TerminalCommand


class TerminalCommandService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, project_id: str | None) -> list[TerminalCommand]:
        if project_id is None:
            stmt = (
                select(TerminalCommand)
                .where(TerminalCommand.project_id.is_(None))
                .order_by(TerminalCommand.sort_order)
            )
        else:
            stmt = (
                select(TerminalCommand)
                .where(TerminalCommand.project_id == project_id)
                .order_by(TerminalCommand.sort_order)
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def resolve(self, project_id: str) -> list[TerminalCommand]:
        project_cmds = await self.list(project_id)
        if project_cmds:
            return project_cmds
        return await self.list(project_id=None)

    async def create(
        self, command: str, sort_order: int, project_id: str | None = None,
        condition: str | None = None
    ) -> TerminalCommand:
        row = TerminalCommand(
            command=command, sort_order=sort_order, project_id=project_id, condition=condition
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(
        self, cmd_id: int, command: str | None = None, sort_order: int | None = None,
        condition: str | None = None
    ) -> TerminalCommand:
        row = await self.session.get(TerminalCommand, cmd_id)
        if row is None:
            raise KeyError(f"TerminalCommand {cmd_id} not found")
        if command is not None:
            row.command = command
        if sort_order is not None:
            row.sort_order = sort_order
        if condition is not None:
            row.condition = condition
        await self.session.flush()
        return row

    async def reorder(self, commands: list[dict]) -> None:
        for item in commands:
            row = await self.session.get(TerminalCommand, item["id"])
            if row is not None:
                row.sort_order = item["sort_order"]
        await self.session.flush()

    async def delete(self, cmd_id: int) -> None:
        row = await self.session.get(TerminalCommand, cmd_id)
        if row is None:
            raise KeyError(f"TerminalCommand {cmd_id} not found")
        await self.session.delete(row)
        await self.session.flush()
