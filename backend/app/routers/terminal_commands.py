from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.terminal_command import (
    TerminalCommandCreate,
    TerminalCommandOut,
    TerminalCommandReorder,
    TerminalCommandUpdate,
)
from app.services.terminal_command_service import TerminalCommandService

router = APIRouter(prefix="/api/terminal-commands", tags=["terminal-commands"])

# Single source of truth for available template variables
TEMPLATE_VARIABLES = [
    {"name": "$issue_id", "description": "ID of the issue the terminal is opened for"},
    {"name": "$project_id", "description": "ID of the project"},
    {"name": "$project_path", "description": "Filesystem path of the project"},
]


@router.get("/variables")
async def list_template_variables():
    return TEMPLATE_VARIABLES


@router.get("", response_model=list[TerminalCommandOut])
async def list_terminal_commands(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    return await service.list(project_id)


@router.post("", response_model=TerminalCommandOut, status_code=201)
async def create_terminal_command(
    data: TerminalCommandCreate,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    cmd = await service.create(data.command, data.sort_order, data.project_id)
    await db.commit()
    return cmd


# NOTE: /reorder MUST be before /{cmd_id} to avoid "reorder" matching as an id
@router.put("/reorder", response_model=list[TerminalCommandOut])
async def reorder_terminal_commands(
    data: TerminalCommandReorder,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    await service.reorder([item.model_dump() for item in data.commands])
    await db.commit()
    if data.commands:
        from app.models.terminal_command import TerminalCommand
        first = await db.get(TerminalCommand, data.commands[0].id)
        return await service.list(first.project_id if first else None)
    return []


@router.put("/{cmd_id}", response_model=TerminalCommandOut)
async def update_terminal_command(
    cmd_id: int,
    data: TerminalCommandUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    try:
        cmd = await service.update(cmd_id, command=data.command, sort_order=data.sort_order)
        await db.commit()
        await db.refresh(cmd)
        return cmd
    except KeyError:
        raise HTTPException(status_code=404, detail="Command not found")


@router.delete("/{cmd_id}", status_code=204)
async def delete_terminal_command(
    cmd_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = TerminalCommandService(db)
    try:
        await service.delete(cmd_id)
        await db.commit()
    except KeyError:
        raise HTTPException(status_code=404, detail="Command not found")
