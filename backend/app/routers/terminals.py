import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.terminal import TerminalCreate, TerminalListResponse, TerminalResponse
from app.services.terminal_service import TerminalService
from app.services.terminal_command_service import TerminalCommandService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminals", tags=["terminals"])

# Dedicated thread pool for blocking PTY reads so they don't starve
# the default asyncio executor used by DB queries, HTTP, etc.
_pty_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="pty-read")

# Singleton service instance
_terminal_service = TerminalService()


def get_terminal_service() -> TerminalService:
    return _terminal_service


async def get_project_path(project_id: str, db: AsyncSession) -> str:
    """Look up project path from DB. Raises ValueError if not found."""
    from app.models.project import Project

    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")
    return project.path


@router.post("", response_model=TerminalResponse, status_code=201)
async def create_terminal(
    data: TerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        project_path = await get_project_path(data.project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.isdir(project_path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project_path}")

    try:
        terminal = service.create(
            issue_id=data.issue_id,
            project_id=data.project_id,
            project_path=project_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    # Inject Manager AI environment variables into the terminal
    try:
        pty = service.get_pty(terminal["id"])
        env_vars = {
            "MANAGER_AI_TERMINAL_ID": terminal["id"],
            "MANAGER_AI_ISSUE_ID": data.issue_id,
            "MANAGER_AI_PROJECT_ID": data.project_id,
            "MANAGER_AI_BASE_URL": f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}",
        }
        env_commands = " && ".join(f"set {k}={v}" for k, v in env_vars.items())
        pty.write(env_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject env vars for terminal %s", terminal["id"], exc_info=True)

    # Inject startup commands into the PTY
    try:
        cmd_service = TerminalCommandService(db)
        commands = await cmd_service.resolve(data.project_id)
        if commands:
            pty = service.get_pty(terminal["id"])
            # Resolve dynamic variables in commands
            # Variable names are defined in terminal_commands.TEMPLATE_VARIABLES
            variables = {
                "$issue_id": data.issue_id,
                "$project_id": data.project_id,
                "$project_path": project_path,
            }
            resolved = []
            for c in commands:
                cmd = c.command
                for var, val in variables.items():
                    cmd = cmd.replace(var, val)
                resolved.append(cmd)
            cmd_string = " && ".join(resolved) + "\r\n"
            pty.write(cmd_string)
    except Exception:
        logger.warning("Failed to inject startup commands for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)


# NOTE: /config and /count MUST be defined before /{terminal_id} routes
# to avoid FastAPI matching them as path parameters.
@router.get("/config")
async def terminal_config(
    db: AsyncSession = Depends(get_db),
):
    """Return terminal configuration including soft limit."""
    from app.services.settings_service import SettingsService
    svc = SettingsService(db)
    try:
        limit = int(await svc.get("terminal_soft_limit"))
    except (KeyError, ValueError):
        limit = 5
    return {"soft_limit": limit}


@router.get("", response_model=list[TerminalListResponse])
async def list_terminals(
    project_id: str | None = Query(None),
    issue_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    from app.models.project import Project
    from app.models.issue import Issue

    terminals = service.list_active(project_id=project_id, issue_id=issue_id)
    # Enrich with issue/project names
    for term in terminals:
        project = await db.get(Project, term["project_id"])
        issue = await db.get(Issue, term["issue_id"])
        term["project_name"] = project.name if project else None
        term["issue_name"] = (issue.name or issue.description[:50]) if issue else None
    return terminals


@router.get("/count")
async def terminal_count(
    service: TerminalService = Depends(get_terminal_service),
):
    return {"count": service.active_count()}


@router.delete("/{terminal_id}", status_code=204)
async def delete_terminal(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        service.kill(terminal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Terminal not found")


@router.websocket("/{terminal_id}/ws")
async def terminal_ws(
    terminal_id: str,
    websocket: WebSocket,
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        service.get(terminal_id)
    except KeyError:
        await websocket.close(code=4004, reason="Terminal not found")
        return

    await websocket.accept()
    pty = service.get_pty(terminal_id)

    # Replay buffered output so reconnecting clients see previous content
    buffered = service.get_buffered_output(terminal_id)
    if buffered:
        await websocket.send_text(buffered)

    async def pty_to_ws():
        """Read from PTY, send to WebSocket."""
        loop = asyncio.get_running_loop()
        try:
            while True:
                data = await loop.run_in_executor(
                    _pty_executor, lambda: pty.read(blocking=True)
                )
                if not data:
                    service.mark_closed(terminal_id)
                    await websocket.close(code=1000, reason="Terminal session ended")
                    break
                service.append_output(terminal_id, data)
                await websocket.send_text(data)
        except (WebSocketDisconnect, RuntimeError):
            pass
        except Exception:
            logger.warning("pty_to_ws error for terminal %s", terminal_id, exc_info=True)

    async def ws_to_pty():
        """Read from WebSocket, write to PTY."""
        try:
            while True:
                message = await websocket.receive_text()
                if message.startswith('{"type":"resize"'):
                    try:
                        msg = json.loads(message)
                        if msg.get("type") == "resize":
                            service.resize(terminal_id, msg["cols"], msg["rows"])
                            continue
                    except (json.JSONDecodeError, KeyError):
                        pass
                pty.write(message)
        except (WebSocketDisconnect, RuntimeError):
            pass
        except Exception:
            logger.warning("ws_to_pty error for terminal %s", terminal_id, exc_info=True)

    pty_read_task = asyncio.create_task(pty_to_ws())
    ws_read_task = asyncio.create_task(ws_to_pty())

    try:
        done, pending = await asyncio.wait(
            [pty_read_task, ws_read_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception:
        pty_read_task.cancel()
        ws_read_task.cancel()
