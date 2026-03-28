from __future__ import annotations

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
async def list_template_variables(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    vars_list = list(TEMPLATE_VARIABLES)
    if project_id:
        from app.services.project_variable_service import ProjectVariableService
        svc = ProjectVariableService(db)
        custom = await svc.list(project_id)
        for v in custom:
            display = "••••••••" if v.is_secret else v.value
            vars_list.append({
                "name": f"${v.name}",
                "description": f"Custom variable (value: {display})",
            })
    return vars_list


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
    cmd = await service.create(data.command, data.sort_order, data.project_id, condition=data.condition)
    await db.commit()
    return cmd


PREDEFINED_TEMPLATES = [
    {
        "name": "Python venv setup",
        "command": "python -m venv venv\nsource venv/bin/activate\npip install -r requirements.txt",
    },
    {
        "name": "Node install + test",
        "command": "npm install\nnpm test",
    },
    {
        "name": "Run tests",
        "command": "python -m pytest -v",
    },
    {
        "name": "Git status",
        "command": "git status && git log --oneline -10",
    },
    {
        "name": "Docker build",
        "command": "docker build -t app .\ndocker run --rm app",
    },
]


@router.get("/templates")
async def list_command_templates():
    """Return predefined command templates for quick insertion."""
    return PREDEFINED_TEMPLATES


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
        kwargs: dict = {"command": data.command, "sort_order": data.sort_order}
        if "condition" in data.model_fields_set:
            kwargs["condition"] = data.condition
        cmd = await service.update(cmd_id, **kwargs)
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
