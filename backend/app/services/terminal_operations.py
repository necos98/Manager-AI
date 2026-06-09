"""Terminal management operations — business logic extracted from the router."""

from __future__ import annotations

import logging
import os
import platform
import re
import shlex
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.providers.registry import AgentProviderRegistry
from app.models.project import Project
from app.services.terminal_helpers import _inject_terminal_env, _teardown_terminal
from app.services.terminal_service import TerminalService
from app.services.terminal_condition import UnknownConditionError, evaluate_condition
from app.services.terminal_command_service import TerminalCommandService
from app.services.terminal_session import (
    _ensure_reader,
    _save_recording,
    _sessions,
    _stop_reader,
    TerminalSession,
)
from app.services.wsl_support import is_wsl_shell, win_to_wsl_path

logger = logging.getLogger(__name__)


async def get_project_path(project_id: str, db: AsyncSession) -> str:
    """Look up project path from DB. Raises ValueError if not found."""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")
    return project.path


async def _create_terminal_base(
    db: AsyncSession,
    service: TerminalService,
    *,
    project_id: str,
    issue_id: str = "",
    project_path: str | None = None,
    shell: str | None = None,
    wsl_distro: str | None = None,
    reap_project_id: str | None = None,
    reap_issue_id: str = "",
    extra_env: dict[str, str] | None = None,
) -> tuple[dict, str, str | None, bool]:
    """Create a PTY terminal with shared setup: path resolution, shell/WSL,
    terminal reap, PTY creation, env injection.

    Returns (terminal_dict, resolved_project_path, project_shell, is_wsl).
    """
    # ── Resolve project path ────────────────────────────────────────
    if project_path is not None:
        resolved_path = project_path
    else:
        try:
            resolved_path = await get_project_path(project_id, db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if not os.path.isdir(resolved_path):
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {resolved_path}",
        )

    # ── Resolve shell / WSL (load from DB if not provided) ──────────
    if shell is None or wsl_distro is None:
        project_obj = await db.get(Project, project_id) if project_id else None
        if shell is None:
            shell = project_obj.shell if project_obj else None
        if wsl_distro is None:
            wsl_distro = project_obj.wsl_distro if project_obj else None

    # ── Reap existing terminals if requested ─────────────────────────
    if reap_project_id is not None:
        for existing in service.list_active(
            project_id=reap_project_id, issue_id=reap_issue_id,
        ):
            await _teardown_terminal(existing["id"], service)

    # ── Create PTY ──────────────────────────────────────────────────
    try:
        terminal = service.create(
            issue_id=issue_id,
            project_id=project_id,
            project_path=resolved_path,
            shell=shell,
            wsl_distro=wsl_distro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from app.logging_config import ErrorLoggerService

        ErrorLoggerService.log_exception(e)
        raise HTTPException(
            status_code=500, detail=f"Failed to spawn terminal: {e}"
        )

    # ── Inject env vars ─────────────────────────────────────────────
    is_wsl = is_wsl_shell(shell)
    await _inject_terminal_env(
        service,
        terminal["id"],
        project_path=resolved_path,
        project_shell=shell,
        project_id=project_id,
        db=db,
        extra_env=extra_env,
    )

    return terminal, resolved_path, shell, is_wsl


async def create_terminal(
    data, db: AsyncSession, service: TerminalService
) -> dict:
    """Create a PTY terminal, inject env vars and startup commands."""
    terminal, project_path, project_shell, is_wsl = await _create_terminal_base(
        db, service,
        project_id=data.project_id,
        issue_id=data.issue_id,
        extra_env={"MANAGER_AI_ISSUE_ID": data.issue_id},
    )

    if data.run_commands:
        try:
            from app.services.issue_service import IssueService

            issue = await IssueService(db).get_by_id(data.issue_id)
            issue_status = issue.status if issue else ""

            replacements = {
                "$issue_id": data.issue_id,
                "$project_id": data.project_id,
                "$project_path": win_to_wsl_path(project_path)
                if is_wsl
                else project_path,
            }

            logger.info(
                "create_terminal: run_commands=%s, command=%s",
                data.run_commands,
                data.command,
            )
            if data.command:
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
                # Quando il provider gestirà il run-issue (data.issue_id presente),
                # non scrivere terminal commands dal DB — evita conflitti
                # (es. utente con comando claude configurato che parte prima del provider)
                if data.issue_id:
                    logger.info(
                        "Skipping DB terminal commands for terminal %s "
                        "(provider will inject run-issue command)",
                        terminal["id"],
                    )
                else:
                    cmd_svc = TerminalCommandService(db)
                    commands = await cmd_svc.resolve(data.project_id)
                    if commands:
                        pty = service.get_pty(terminal["id"])
                        condition_vars = {
                            "issue_status": issue_status,
                            "issue_id": data.issue_id,
                            "project_id": data.project_id,
                        }
                        for c in commands:
                            try:
                                passes = evaluate_condition(
                                    c.condition, condition_vars
                                )
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
            logger.warning(
                "Failed to inject startup commands for terminal %s",
                terminal["id"],
                exc_info=True,
            )

    # ── Inietta il comando run-issue dal provider ─────────────────────
    if data.issue_id and not data.command:
        try:
            from app.services.settings_service import SettingsService

            settings_svc = SettingsService(db)
            provider_name = await settings_svc.get("agent_provider")
            provider = AgentProviderRegistry.get(provider_name)
            cmds = provider.build_run_issue_commands(data.issue_id)

            is_wsl = is_wsl_shell(project_shell)
            replacements = {
                "$issue_id": data.issue_id,
                "$project_id": data.project_id,
                "$project_path": win_to_wsl_path(project_path)
                if is_wsl
                else project_path,
            }
            pty = service.get_pty(terminal["id"])
            for cmd in cmds:
                resolved = cmd
                for var, val in replacements.items():
                    resolved = resolved.replace(var, val)
                logger.info(
                    "Injecting run-issue command (provider=%s): %s",
                    provider_name,
                    resolved,
                )
                pty.write(resolved + "\r\n")
        except Exception:
            logger.warning(
                "Failed to inject run-issue command for terminal %s",
                terminal["id"],
                exc_info=True,
            )

    return terminal


async def create_ask_terminal(
    data, db: AsyncSession, service: TerminalService
) -> dict:
    """Create an Ask & Brainstorming terminal, reaping any prior one."""
    terminal, project_path, project_shell, is_wsl = await _create_terminal_base(
        db, service,
        project_id=data.project_id,
        issue_id="",
        reap_project_id=data.project_id,
        reap_issue_id="",
    )

    try:
        from app.services.settings_service import SettingsService

        settings_svc = SettingsService(db)
        provider_name = await settings_svc.get("agent_provider")
        provider = AgentProviderRegistry.get(provider_name)
        cmds = provider.build_ask_brainstorm_commands(data.project_id)

        variables = {
            "$project_id": data.project_id,
            "$project_path": win_to_wsl_path(project_path)
            if is_wsl
            else project_path,
        }
        pty = service.get_pty(terminal["id"])
        for cmd in cmds:
            resolved = cmd
            for var, val in variables.items():
                resolved = resolved.replace(var, val)
            logger.info("Ask terminal %s command: %s", terminal["id"], resolved)
            pty.write(resolved + "\r\n")
    except Exception:
        logger.warning(
            "Failed to inject ask command for terminal %s",
            terminal["id"],
            exc_info=True,
        )

    return terminal


async def create_manage_agent_terminal(
    data, db: AsyncSession, service: TerminalService
) -> dict:
    """Create a Manage Agent terminal."""
    # Calcola project_path (unico per manage-agent — non dal DB)
    project_path = str(
        Path(app_settings.database_url).parent.parent.resolve()
    )
    if not os.path.isdir(project_path):
        project_path = str(
            Path(__file__).resolve().parent.parent.parent
        )

    # Fetch agent intent before creating terminal
    agent_intent = ""
    if data.agent_id:
        try:
            from app.services.agent_service import AgentService

            agent_svc = AgentService(db)
            agent = await agent_svc.get_by_id(data.agent_id)
            agent_intent = agent.intent
        except Exception:
            logger.warning(
                "Failed to fetch agent %s for terminal",
                data.agent_id,
                exc_info=True,
            )

    terminal, project_path, project_shell, is_wsl = await _create_terminal_base(
        db, service,
        project_id="",
        issue_id="",
        project_path=project_path,
        reap_project_id="",
        reap_issue_id="",
    )

    # ── Env vars specifiche manage-agent (via PTY) ──────────────────
    try:
        pty = service.get_pty(terminal["id"])
        port = str(app_settings.backend_port)
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
            pairs = (
                f"{k}={shlex.quote(str(v))}"
                for k, v in env_vars.items()
            )
            line = " && ".join(f"export {p}" for p in pairs)
        pty.write(line + "\r\n")
    except Exception:
        logger.warning(
            "Failed to inject env vars for manage-agent terminal %s",
            terminal["id"],
            exc_info=True,
        )

    try:
        from app.services.settings_service import SettingsService

        settings_svc = SettingsService(db)
        provider_name = await settings_svc.get("agent_provider")
        provider = AgentProviderRegistry.get(provider_name)
        cmds = provider.build_manage_agent_commands(
            agent_intent if data.agent_id else ""
        )
        pty = service.get_pty(terminal["id"])
        for cmd in cmds:
            logger.info(
                "Manage-agent terminal %s command: %s", terminal["id"], cmd
            )
            pty.write(cmd + "\r\n")
    except Exception:
        logger.warning(
            "Failed to inject manage-agent command for terminal %s",
            terminal["id"],
            exc_info=True,
        )

    return terminal


async def create_hermes_terminal(
    data, service: TerminalService
) -> dict:
    """Create a Hermes CLI terminal (system-level, no project/issue)."""
    project_path = str(
        Path(app_settings.database_url).parent.parent.resolve()
    )
    if not os.path.isdir(project_path):
        project_path = str(
            Path(__file__).resolve().parent.parent.parent
        )

    try:
        terminal = service.create(
            issue_id="",
            project_id="",
            project_path=project_path,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to spawn terminal: {e}"
        )

    # Write the Hermes command into the PTY
    try:
        pty = service.get_pty(terminal["id"])
        for line in data.command.split("\n"):
            line = line.strip()
            if line:
                pty.write(line + "\r\n")
    except Exception:
        logger.warning(
            "Failed to inject Hermes command for terminal %s",
            terminal["id"],
            exc_info=True,
        )

    return terminal


async def create_log_terminal(
    data, db: AsyncSession, service: TerminalService
) -> dict:
    """Create a log-only terminal."""
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
    _sessions[terminal["id"]] = TerminalSession()
    _ensure_reader(terminal["id"], service)
    return terminal


async def list_ask_terminals(
    project_id: str, db: AsyncSession, service: TerminalService
) -> list[dict]:
    """Return active Ask & Brainstorming terminals (issue_id == '') for a project."""
    terminals = service.list_active(project_id=project_id, issue_id="")
    for term in terminals:
        project = await db.get(Project, term["project_id"])
        term["project_name"] = project.name if project else None
        term["issue_name"] = None
    return terminals


def list_manage_agent_terminals(
    service: TerminalService,
) -> list[dict]:
    """Return active Manage Agent terminals (project_id == '' and issue_id == '')."""
    return service.list_active(project_id="", issue_id="")


async def terminal_config(db: AsyncSession) -> dict:
    """Return terminal configuration including soft limit."""
    from app.services.settings_service import SettingsService

    svc = SettingsService(db)
    try:
        limit = int(await svc.get("terminal_soft_limit"))
    except (KeyError, ValueError):
        limit = 5
    return {"soft_limit": limit}


async def list_terminals(
    project_id: str | None,
    issue_id: str | None,
    db: AsyncSession,
    service: TerminalService,
) -> list[dict]:
    """List active terminals with project and issue names."""
    from app.services.issue_service import IssueService

    terminals = service.list_active(
        project_id=project_id, issue_id=issue_id
    )
    terminals = [
        t
        for t in terminals
        if not (t["project_id"] == "" and t["issue_id"] == "")
    ]
    issue_svc = IssueService(db)

    project_ids = {
        t["project_id"] for t in terminals if t["project_id"]
    }
    if project_ids:
        project_rows = await db.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        project_map = {p.id: p for p in project_rows.scalars().all()}
    else:
        project_map = {}

    for term in terminals:
        proj = project_map.get(term["project_id"])
        term["project_name"] = proj.name if proj else None
        issue = await issue_svc.get_by_id(term["issue_id"])
        term["issue_name"] = (
            (issue.name or issue.description[:50]) if issue else None
        )
    return terminals


def terminal_count(service: TerminalService) -> dict:
    """Return count of active terminals."""
    return {"count": service.active_count()}


async def get_terminal_recording(
    terminal_id: str, service: TerminalService
) -> PlainTextResponse:
    """Return terminal recording (live buffer or saved file)."""
    if not re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        terminal_id,
    ):
        raise HTTPException(status_code=400, detail="Invalid terminal ID")

    live_buf = service.get_buffered_output(terminal_id)
    if live_buf:
        return PlainTextResponse(
            live_buf,
            headers={
                "Content-Disposition": f'attachment; filename="{terminal_id}.txt"'
            },
        )

    rec_path = Path(app_settings.recordings_path) / f"{terminal_id}.txt"
    if rec_path.exists():
        return PlainTextResponse(
            rec_path.read_text(encoding="utf-8"),
            headers={
                "Content-Disposition": f'attachment; filename="{terminal_id}.txt"'
            },
        )

    raise HTTPException(
        status_code=404, detail="No recording found for this terminal"
    )


async def delete_terminal(
    terminal_id: str, service: TerminalService
) -> None:
    """Save recording, stop reader, close WS, and kill terminal."""
    buf = service.get_buffered_output(terminal_id)
    _save_recording(terminal_id, buf)
    _stop_reader(terminal_id)
    session = _sessions.pop(terminal_id, None)
    if session is not None and session.ws is not None:
        try:
            await session.ws.close(code=1000, reason="Terminal killed")
        except Exception:
            pass
    try:
        service.kill(terminal_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
