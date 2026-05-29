from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shlex
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database import get_db
from app.models.project import Project
from app.schemas.terminal import AskTerminalCreate, LogTerminalCreate, ManageAgentTerminalCreate, TerminalCreate, TerminalListResponse, TerminalResponse
from app.services.terminal_service import TerminalService, terminal_service
from app.services.terminal_command_service import TerminalCommandService
from app.services.terminal_condition import UnknownConditionError, evaluate_condition
from app.services.terminal_session import (
    TerminalSession,
    _ensure_reader,
    _save_recording,
    _sessions,
    _stop_reader,
)
from app.services.wsl_support import get_host_ip_for_wsl, is_wsl_shell, win_to_wsl_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminals", tags=["terminals"])


async def _teardown_terminal(terminal_id: str, service: TerminalService) -> None:
    """Save recording, stop reader, close WS, and kill PTY for a terminal."""
    try:
        buf = service.get_buffered_output(terminal_id)
        _save_recording(terminal_id, buf)
    except Exception:
        pass
    _stop_reader(terminal_id)
    session = _sessions.pop(terminal_id, None)
    if session is not None and session.ws is not None:
        try:
            await session.ws.close(code=1000, reason="Terminal replaced")
        except Exception:
            pass
    try:
        service.kill(terminal_id)
    except KeyError:
        pass


def get_terminal_service() -> TerminalService:
    return terminal_service


async def get_project_path(project_id: str, db: AsyncSession) -> str:
    """Look up project path from DB. Raises ValueError if not found."""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")
    return project.path


def _inject_env_vars(
    pty,
    env: dict[str, str],
    *,
    is_wsl: bool,
) -> None:
    """Write env exports to the PTY using the shell dialect.

    - is_wsl=True  -> bash ``export`` (runs inside WSL).
    - is_wsl=False -> Windows ``set`` on Windows host, ``export`` on Linux/macOS host.
    """
    if is_wsl:
        set_cmd = "export"
    else:
        set_cmd = "set" if platform.system() == "Windows" else "export"
    if set_cmd == "export":
        # bash — shell-quote values so spaces and metacharacters stay literal
        pairs = (f"{k}={shlex.quote(str(v))}" for k, v in env.items())
    else:
        # cmd.exe — no quoting; values with spaces are already unsupported here
        pairs = (f"{k}={v}" for k, v in env.items())
    line = " && ".join(f"{set_cmd} {p}" for p in pairs)
    pty.write(line + "\r\n")


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
    project_wsl_distro = project_obj.wsl_distro if project_obj else None

    try:
        terminal = service.create(
            issue_id=data.issue_id,
            project_id=data.project_id,
            project_path=project_path,
            shell=project_shell,
            wsl_distro=project_wsl_distro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    # Determine if this terminal is running inside WSL
    is_wsl = is_wsl_shell(project_shell)

    # If WSL: cd into the POSIX-translated path before injecting env vars
    if is_wsl:
        cwd_wsl = win_to_wsl_path(project_path)
        pty = service.get_pty(terminal["id"])
        pty.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

    # Inject Manager AI environment variables into the terminal
    try:
        pty = service.get_pty(terminal["id"])
        env_vars = {
            "MANAGER_AI_TERMINAL_ID": terminal["id"],
            "MANAGER_AI_ISSUE_ID": data.issue_id,
            "MANAGER_AI_PROJECT_ID": data.project_id,
        }
        if is_wsl:
            _inject_env_vars(pty, env_vars, is_wsl=True)
            port = os.environ.get("BACKEND_PORT", "8000")
            host_ip = get_host_ip_for_wsl()
            if host_ip:
                pty.write(
                    f'export MANAGER_AI_BASE_URL='
                    f'"http://{host_ip}:{port}"\r\n'
                )
            else:
                pty.write(
                    f'export MANAGER_AI_BASE_URL='
                    f'"http://localhost:{port}"\r\n'
                )
        else:
            env_vars["MANAGER_AI_BASE_URL"] = (
                f'http://localhost:{os.environ.get("BACKEND_PORT", "8000")}'
            )
            _inject_env_vars(pty, env_vars, is_wsl=False)
    except Exception:
        logger.warning("Failed to inject env vars for terminal %s", terminal["id"], exc_info=True)

    # Inject project custom variables into the terminal
    try:
        from app.services.project_variable_service import ProjectVariableService
        var_svc = ProjectVariableService(db)
        custom_vars = await var_svc.list(data.project_id)
        if custom_vars:
            pty = service.get_pty(terminal["id"])
            _inject_env_vars(pty, {v.name: v.value for v in custom_vars}, is_wsl=is_wsl)
    except Exception:
        logger.warning("Failed to inject custom variables for terminal %s", terminal["id"], exc_info=True)

    # Inject startup commands into the PTY
    if data.run_commands:
        try:
            from app.services.issue_service import IssueService
            issue = await IssueService(db).get_by_id(data.issue_id)
            issue_status = issue.status if issue else ""

            # Resolve dynamic variables in commands
            replacements = {
                "$issue_id": data.issue_id,
                "$project_id": data.project_id,
                "$project_path": win_to_wsl_path(project_path) if is_wsl else project_path,
            }

            logger.info("create_terminal: run_commands=%s, command=%s", data.run_commands, data.command)
            if data.command:
                # Custom command override (e.g., pipeline run)
                cmd_text = data.command
                for var, val in replacements.items():
                    cmd_text = cmd_text.replace(var, val)
                logger.info("Injecting custom command: %s", cmd_text)
                pty = service.get_pty(terminal["id"])
                for line in cmd_text.split("\n"):
                    line = line.strip()
                    if line:
                        pty.write(line + "\r\n")
            else:
                cmd_service = TerminalCommandService(db)
                commands = await cmd_service.resolve(data.project_id)
                if commands:
                    pty = service.get_pty(terminal["id"])
                    condition_vars = {
                        "issue_status": issue_status,
                        "issue_id": data.issue_id,
                        "project_id": data.project_id,
                    }
                    for c in commands:
                        try:
                            passes = evaluate_condition(c.condition, condition_vars)
                        except UnknownConditionError as exc:
                            logger.warning(
                                "Skipping terminal command %s: %s", c.id, exc
                            )
                            continue
                        if not passes:
                            continue
                        cmd_text = c.command
                        for var, val in replacements.items():
                            cmd_text = cmd_text.replace(var, val)
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

    # Enforce single active ask&brainstorming terminal per project:
    # tear down any existing ones before spawning a new initialized session.
    for existing in service.list_active(project_id=data.project_id, issue_id=""):
        await _teardown_terminal(existing["id"], service)

    # Fetch project shell config
    project_obj = await db.get(Project, data.project_id)
    project_shell = project_obj.shell if project_obj else None
    project_wsl_distro = project_obj.wsl_distro if project_obj else None

    try:
        terminal = service.create(
            issue_id="",
            project_id=data.project_id,
            project_path=project_path,
            shell=project_shell,
            wsl_distro=project_wsl_distro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    # Determine if this terminal is running inside WSL
    is_wsl = is_wsl_shell(project_shell)

    # If WSL: cd into the POSIX-translated path before injecting env vars
    if is_wsl:
        cwd_wsl = win_to_wsl_path(project_path)
        pty = service.get_pty(terminal["id"])
        pty.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

    # Inject Manager AI environment variables
    try:
        pty = service.get_pty(terminal["id"])
        env_vars = {
            "MANAGER_AI_TERMINAL_ID": terminal["id"],
            "MANAGER_AI_PROJECT_ID": data.project_id,
        }
        if is_wsl:
            _inject_env_vars(pty, env_vars, is_wsl=True)
            port = os.environ.get("BACKEND_PORT", "8000")
            host_ip = get_host_ip_for_wsl()
            if host_ip:
                pty.write(
                    f'export MANAGER_AI_BASE_URL='
                    f'"http://{host_ip}:{port}"\r\n'
                )
            else:
                pty.write(
                    f'export MANAGER_AI_BASE_URL='
                    f'"http://localhost:{port}"\r\n'
                )
        else:
            env_vars["MANAGER_AI_BASE_URL"] = (
                f'http://localhost:{os.environ.get("BACKEND_PORT", "8000")}'
            )
            _inject_env_vars(pty, env_vars, is_wsl=False)
    except Exception:
        logger.warning("Failed to inject env vars for ask terminal %s", terminal["id"], exc_info=True)

    # Inject project custom variables
    try:
        from app.services.project_variable_service import ProjectVariableService
        var_svc = ProjectVariableService(db)
        custom_vars = await var_svc.list(data.project_id)
        if custom_vars:
            pty = service.get_pty(terminal["id"])
            _inject_env_vars(pty, {v.name: v.value for v in custom_vars}, is_wsl=is_wsl)
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
            "$project_path": win_to_wsl_path(project_path) if is_wsl else project_path,
        }
        for var, val in variables.items():
            cmd = cmd.replace(var, val)
        logger.info("Ask terminal %s command: %s", terminal["id"], cmd)
        pty = service.get_pty(terminal["id"])
        pty.write(cmd + "\r\n")
    except Exception:
        logger.warning("Failed to inject ask command for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)


@router.post("/manage-agent", response_model=TerminalResponse, status_code=201)
async def create_manage_agent_terminal(
    data: ManageAgentTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    from app.config import settings as app_config

    project_path = str(Path(app_config.database_url).parent.parent.resolve())
    if not os.path.isdir(project_path):
        project_path = str(Path(__file__).resolve().parent.parent.parent)

    # Tear down any existing manage-agent terminals
    # Note: list_active() returns _to_response() dicts which exclude "pty" field,
    # so we tear down unconditionally for manage-agent terminals (always have PTY).
    for existing in service.list_active(project_id="", issue_id=""):
        await _teardown_terminal(existing["id"], service)

    try:
        terminal = service.create(
            issue_id="",
            project_id="",
            project_path=project_path,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    # If agent_id provided, fetch agent for context injection
    agent_intent = ""
    if data.agent_id:
        try:
            from app.services.agent_service import AgentService
            agent_svc = AgentService(db)
            agent = await agent_svc.get_by_id(data.agent_id)
            agent_intent = agent.intent
        except Exception:
            logger.warning("Failed to fetch agent %s for terminal", data.agent_id, exc_info=True)

    # Inject env vars
    try:
        pty = service.get_pty(terminal["id"])
        port = os.environ.get("BACKEND_PORT", "8000")
        env_vars = {
            "MANAGER_AI_TERMINAL_ID": terminal["id"],
            "MANAGER_AI_BASE_URL": f"http://localhost:{port}",
        }
        if data.agent_id:
            env_vars["MANAGER_AI_AGENT_ID"] = data.agent_id
            env_vars["MANAGER_AI_AGENT_INTENT"] = agent_intent
        if platform.system() == "Windows":
            pairs = (f"{k}={v}" for k, v in env_vars.items())
            line = " && ".join(f"set {p}" for p in pairs)
        else:
            pairs = (f"{k}={shlex.quote(str(v))}" for k, v in env_vars.items())
            line = " && ".join(f"export {p}" for p in pairs)
        pty.write(line + "\r\n")
    except Exception:
        logger.warning("Failed to inject env vars for manage-agent terminal %s", terminal["id"], exc_info=True)

    # Read and inject the manage_agent_command from settings
    try:
        from app.services.settings_service import SettingsService
        settings_svc = SettingsService(db)
        cmd = await settings_svc.get("manage_agent_command")
        skip_perms = await settings_svc.get("claude.skip_permissions") == "true"
        if skip_perms and cmd.startswith("claude "):
            cmd = "claude --dangerously-skip-permissions " + cmd[len("claude "):]
        # If agent-specific terminal, append agent intent as startup instruction
        if data.agent_id and agent_intent:
            cmd += f" \"{agent_intent}\""
        logger.info("Manage-agent terminal %s command: %s", terminal["id"], cmd)
        pty = service.get_pty(terminal["id"])
        pty.write(cmd + "\r\n")
    except Exception:
        logger.warning("Failed to inject manage-agent command for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)


@router.post("/log", response_model=TerminalResponse, status_code=201)
async def create_log_terminal(
    data: LogTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        project_path = await get_project_path(data.project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    terminal = await service.create_log(
        project_id=data.project_id,
        issue_id=data.issue_id,
        project_path=project_path,
        label=data.label,
    )
    # Create a TerminalSession so the reader has a home for its state.
    _sessions[terminal["id"]] = TerminalSession()
    _ensure_reader(terminal["id"], service)
    return TerminalResponse(**terminal)


# NOTE: /config, /count, and /ask MUST be defined before /{terminal_id} routes
# to avoid FastAPI matching them as path parameters.
@router.get("/ask", response_model=list[TerminalListResponse])
async def list_ask_terminals(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    """Return active Ask & Brainstorming terminals (issue_id == '') for a project."""
    from app.models.project import Project

    terminals = service.list_active(project_id=project_id, issue_id="")
    for term in terminals:
        project = await db.get(Project, term["project_id"])
        term["project_name"] = project.name if project else None
        term["issue_name"] = None
    return terminals


@router.get("/manage-agent", response_model=list[TerminalListResponse])
async def list_manage_agent_terminals(
    service: TerminalService = Depends(get_terminal_service),
):
    """Return active Manage Agent terminals (project_id == '' and issue_id == '')."""
    return service.list_active(project_id="", issue_id="")


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
    from app.services.issue_service import IssueService

    terminals = service.list_active(project_id=project_id, issue_id=issue_id)
    # Filter out manage-agent terminals (project_id="" AND issue_id="") from global view
    # These are section-internal terminals for AGENTS, Pipelines, etc., not project terminals
    terminals = [t for t in terminals if not (t["project_id"] == "" and t["issue_id"] == "")]
    issue_svc = IssueService(db)
    for term in terminals:
        project = await db.get(Project, term["project_id"])
        issue = await issue_svc.get_by_id(term["issue_id"])
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
    buf = service.get_buffered_output(terminal_id)
    _save_recording(terminal_id, buf)
    # Stop background reader and disconnect WebSocket before killing
    _stop_reader(terminal_id)
    session = _sessions.pop(terminal_id, None)
    if session is not None and session.ws is not None:
        try:
            await session.ws.close(code=1000, reason="Terminal killed")
        except Exception:
            pass
    service.kill(terminal_id)


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
    elif pty is None:
        await websocket.send_text("\x1b[90mConnected to agent output stream...\x1b[0m\r\n")

    # Get or create the TerminalSession and register this WS on it.
    # The WS endpoint is the sole owner of ws.close() -- the reader
    # only sets pty_dead so we can exit the receive loop cleanly.
    session = _sessions.get(terminal_id)
    if session is None:
        session = TerminalSession()
        _sessions[terminal_id] = session
    # Reset death flag on reconnect so the loop doesn't exit immediately.
    session.pty_dead.clear()
    session.pty_died_naturally = False
    session.ws = websocket
    _ensure_reader(terminal_id, service)

    # WebSocket -> PTY input loop
    try:
        while True:
            # Check if the PTY died while we were waiting
            if session.pty_dead.is_set():
                break

            message = await websocket.receive_text()
            if message.startswith('{"type":"resize"'):
                try:
                    msg = json.loads(message)
                    if msg.get("type") == "resize":
                        service.resize(terminal_id, msg["cols"], msg["rows"])
                        continue
                except (json.JSONDecodeError, KeyError):
                    pass
            if pty is not None:
                pty.write(message)
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception:
        logger.warning("ws_to_pty error for terminal %s", terminal_id, exc_info=True)
    finally:
        # Cleanup: close the WS gracefully (this is the ONLY place that closes it).
        pty_ended_naturally = session is not None and session.pty_died_naturally
        if session is not None:
            session.ws = None
        # If the PTY died naturally, close with a meaningful code so the
        # frontend can distinguish "session ended" from a network blip.
        close_code = 1000 if pty_ended_naturally else 1001
        try:
            await websocket.close(code=close_code, reason="Terminal session ended")
        except Exception:
            pass
