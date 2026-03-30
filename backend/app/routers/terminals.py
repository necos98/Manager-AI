from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database import get_db
from app.models.project import Project
from app.schemas.terminal import AskTerminalCreate, TerminalCreate, TerminalListResponse, TerminalResponse
from app.services.terminal_service import TerminalService, terminal_service
from app.services.terminal_command_service import TerminalCommandService

logger = logging.getLogger(__name__)


def _evaluate_condition(condition: str | None, issue_status: str) -> bool:
    """Evaluate a startup command condition. Returns True if the command should run."""
    if not condition:
        return True
    parts = condition.strip().split()
    if len(parts) == 3 and parts[0] == "$issue_status" and parts[1] == "==":
        return issue_status == parts[2]
    # Unknown condition syntax → always run (safe default)
    return True


def _save_recording(terminal_id: str, content: str) -> None:
    """Write terminal output buffer to a file in the recordings directory."""
    if not content:
        return
    try:
        rec_dir = Path(app_settings.recordings_path)
        rec_dir.mkdir(parents=True, exist_ok=True)
        (rec_dir / f"{terminal_id}.txt").write_text(content, encoding="utf-8")
    except Exception:
        logger.warning("Failed to save recording for terminal %s", terminal_id, exc_info=True)

router = APIRouter(prefix="/api/terminals", tags=["terminals"])

# Dedicated thread pool for blocking PTY reads so they don't starve
# the default asyncio executor used by DB queries, HTTP, etc.
_pty_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="pty-read")

# --- Persistent reader infrastructure ---
# One reader task per terminal keeps reading PTY output and buffering it
# regardless of whether a WebSocket client is connected.
_terminal_readers: dict[str, asyncio.Task] = {}
# Currently connected WebSocket per terminal (at most one)
_terminal_ws: dict[str, WebSocket] = {}


async def _terminal_reader(terminal_id: str, service: TerminalService) -> None:
    """Persistent reader: buffers PTY output and forwards to a connected WebSocket."""
    loop = asyncio.get_running_loop()
    try:
        pty = service.get_pty(terminal_id)
    except KeyError:
        return
    try:
        while True:
            data = await loop.run_in_executor(
                _pty_executor, lambda: pty.read(blocking=True)
            )
            if not data:
                # PTY EOF — process exited
                buf = service.get_buffered_output(terminal_id)
                _save_recording(terminal_id, buf)
                service.mark_closed(terminal_id)
                ws = _terminal_ws.pop(terminal_id, None)
                if ws:
                    try:
                        await ws.close(code=1000, reason="Terminal session ended")
                    except Exception:
                        pass
                break
            service.append_output(terminal_id, data)
            ws = _terminal_ws.get(terminal_id)
            if ws:
                try:
                    await ws.send_text(data)
                except Exception:
                    # WebSocket gone — stop forwarding, but keep buffering
                    _terminal_ws.pop(terminal_id, None)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.warning("Terminal reader error for %s", terminal_id, exc_info=True)
    finally:
        _terminal_readers.pop(terminal_id, None)


def _ensure_reader(terminal_id: str, service: TerminalService) -> None:
    """Start the persistent reader if it's not already running."""
    existing = _terminal_readers.get(terminal_id)
    if existing and not existing.done():
        return
    _terminal_readers[terminal_id] = asyncio.create_task(
        _terminal_reader(terminal_id, service)
    )


def _stop_reader(terminal_id: str) -> None:
    """Cancel the persistent reader for a terminal."""
    task = _terminal_readers.pop(terminal_id, None)
    if task and not task.done():
        task.cancel()


def get_terminal_service() -> TerminalService:
    return terminal_service


async def get_project_path(project_id: str, db: AsyncSession) -> str:
    """Look up project path from DB. Raises ValueError if not found."""
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

    # Fetch project shell config
    project_obj = await db.get(Project, data.project_id)
    project_shell = project_obj.shell if project_obj else None

    try:
        terminal = service.create(
            issue_id=data.issue_id,
            project_id=data.project_id,
            project_path=project_path,
            shell=project_shell,
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
            "MANAGER_AI_BASE_URL": os.environ.get("MANAGER_AI_BASE_URL", f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}"),
        }
        set_cmd = "set" if platform.system() == "Windows" else "export"
        env_commands = " && ".join(f"{set_cmd} {k}={v}" for k, v in env_vars.items())
        pty.write(env_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject env vars for terminal %s", terminal["id"], exc_info=True)

    # Inject project custom variables into the terminal
    try:
        from app.services.project_variable_service import ProjectVariableService
        var_svc = ProjectVariableService(db)
        custom_vars = await var_svc.list(data.project_id)
        if custom_vars:
            pty = service.get_pty(terminal["id"])
            set_cmd = "set" if platform.system() == "Windows" else "export"
            var_commands = " && ".join(f"{set_cmd} {v.name}={v.value}" for v in custom_vars)
            pty.write(var_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject custom variables for terminal %s", terminal["id"], exc_info=True)

    # Inject startup commands into the PTY
    if data.run_commands:
        try:
            from app.models.issue import Issue
            issue = await db.get(Issue, data.issue_id)
            issue_status = issue.status.value if issue else ""

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
                for c in commands:
                    if not _evaluate_condition(c.condition, issue_status):
                        continue
                    cmd_text = c.command
                    for var, val in variables.items():
                        cmd_text = cmd_text.replace(var, val)
                    # Support multi-line: send each non-empty line as a separate command
                    for line in cmd_text.split("\n"):
                        line = line.strip()
                        if line:
                            pty.write(line + "\r\n")
        except Exception:
            logger.warning("Failed to inject startup commands for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)


@router.post("/ask", response_model=TerminalResponse, status_code=201)
async def create_ask_terminal(
    data: AskTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        project_path = await get_project_path(data.project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.isdir(project_path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project_path}")

    # Fetch project shell config
    project_obj = await db.get(Project, data.project_id)
    project_shell = project_obj.shell if project_obj else None

    try:
        terminal = service.create(
            issue_id="",
            project_id=data.project_id,
            project_path=project_path,
            shell=project_shell,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    # Inject Manager AI environment variables
    try:
        pty = service.get_pty(terminal["id"])
        env_vars = {
            "MANAGER_AI_TERMINAL_ID": terminal["id"],
            "MANAGER_AI_PROJECT_ID": data.project_id,
            "MANAGER_AI_BASE_URL": f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}",
        }
        set_cmd = "set" if platform.system() == "Windows" else "export"
        env_commands = " && ".join(f"{set_cmd} {k}={v}" for k, v in env_vars.items())
        pty.write(env_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject env vars for ask terminal %s", terminal["id"], exc_info=True)

    # Inject project custom variables
    try:
        from app.services.project_variable_service import ProjectVariableService
        var_svc = ProjectVariableService(db)
        custom_vars = await var_svc.list(data.project_id)
        if custom_vars:
            pty = service.get_pty(terminal["id"])
            set_cmd = "set" if platform.system() == "Windows" else "export"
            var_commands = " && ".join(f"{set_cmd} {v.name}={v.value}" for v in custom_vars)
            pty.write(var_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject custom vars for ask terminal %s", terminal["id"], exc_info=True)

    # Read and inject the ask_brainstorm_command from settings
    try:
        from app.services.settings_service import SettingsService
        settings_svc = SettingsService(db)
        cmd = await settings_svc.get("ask_brainstorm_command")
        skip_perms = await settings_svc.get("claude.skip_permissions") == "true"
        if skip_perms and cmd.startswith("claude "):
            cmd = "claude --dangerously-skip-permissions " + cmd[len("claude "):]
        variables = {
            "$project_id": data.project_id,
            "$project_path": project_path,
        }
        for var, val in variables.items():
            cmd = cmd.replace(var, val)
        pty = service.get_pty(terminal["id"])
        pty.write(cmd + "\r\n")
    except Exception:
        logger.warning("Failed to inject ask command for terminal %s", terminal["id"], exc_info=True)

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


@router.get("/{terminal_id}/recording")
async def get_terminal_recording(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    import re
    from fastapi.responses import PlainTextResponse

    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", terminal_id):
        raise HTTPException(status_code=400, detail="Invalid terminal ID")

    # Try live buffer first (terminal still active)
    live_buf = service.get_buffered_output(terminal_id)
    if live_buf:
        return PlainTextResponse(
            live_buf,
            headers={"Content-Disposition": f'attachment; filename="{terminal_id}.txt"'},
        )

    # Try saved recording file
    rec_path = Path(app_settings.recordings_path) / f"{terminal_id}.txt"
    if rec_path.exists():
        return PlainTextResponse(
            rec_path.read_text(encoding="utf-8"),
            headers={"Content-Disposition": f'attachment; filename="{terminal_id}.txt"'},
        )

    raise HTTPException(status_code=404, detail="No recording found for this terminal")


@router.delete("/{terminal_id}", status_code=204)
async def delete_terminal(
    terminal_id: str,
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        buf = service.get_buffered_output(terminal_id)
        _save_recording(terminal_id, buf)
        # Stop background reader and disconnect WebSocket before killing
        _stop_reader(terminal_id)
        ws = _terminal_ws.pop(terminal_id, None)
        if ws:
            try:
                await ws.close(code=1000, reason="Terminal killed")
            except Exception:
                pass
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

    # Register this WS and ensure the persistent reader is running
    _terminal_ws[terminal_id] = websocket
    _ensure_reader(terminal_id, service)

    # WebSocket → PTY input loop
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
    finally:
        # Unregister WS but keep the terminal and reader alive
        if _terminal_ws.get(terminal_id) is websocket:
            _terminal_ws.pop(terminal_id, None)
