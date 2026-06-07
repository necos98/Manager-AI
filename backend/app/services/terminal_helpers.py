from __future__ import annotations

import logging
import platform
import shlex

from app.config import settings as app_settings
from app.services.terminal_session import (
    TerminalSession,
    _save_recording,
    _sessions,
    _stop_reader,
)
from app.services.wsl_support import get_host_ip_for_wsl, is_wsl_shell, quote_url_for_shell, win_to_wsl_path

logger = logging.getLogger(__name__)


async def _teardown_terminal(terminal_id: str, service) -> None:
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


async def _inject_terminal_env(
    service,
    terminal_id: str,
    *,
    project_path: str,
    project_shell: str | None,
    project_id: str,
    db,
    extra_env: dict[str, str] | None = None,
) -> None:
    """Inject env vars, WSL cd, and custom project variables into a PTY.

    Shared logic between create_terminal and create_ask_terminal.
    """
    is_wsl = is_wsl_shell(project_shell)

    # WSL: cd into POSIX-translated path
    if is_wsl:
        cwd_wsl = win_to_wsl_path(project_path)
        pty = service.get_pty(terminal_id)
        pty.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

    # Inject Manager AI environment variables
    try:
        pty = service.get_pty(terminal_id)
        env_vars = {
            "MANAGER_AI_TERMINAL_ID": terminal_id,
            "MANAGER_AI_PROJECT_ID": project_id,
            **(extra_env or {}),
        }
        if is_wsl:
            _inject_env_vars(pty, env_vars, is_wsl=True)
            port = str(app_settings.backend_port)
            host_ip = get_host_ip_for_wsl()
            if host_ip:
                pty.write(
                    f'export MANAGER_AI_BASE_URL='
                    f'{quote_url_for_shell(f"http://{host_ip}:{port}", is_wsl=True)}\r\n'
                )
            else:
                pty.write(
                    f'export MANAGER_AI_BASE_URL='
                    f'{quote_url_for_shell(f"http://localhost:{port}", is_wsl=True)}\r\n'
                )
        else:
            env_vars["MANAGER_AI_BASE_URL"] = (
                f'http://localhost:{str(app_settings.backend_port)}'
            )
            _inject_env_vars(pty, env_vars, is_wsl=False)
    except Exception:
        logger.warning("Failed to inject env vars for terminal %s", terminal_id, exc_info=True)

    # Inject project custom variables
    try:
        from app.services.project_variable_service import ProjectVariableService
        var_svc = ProjectVariableService(db)
        custom_vars = await var_svc.list(project_id)
        if custom_vars:
            pty = service.get_pty(terminal_id)
            _inject_env_vars(pty, {v.name: v.value for v in custom_vars}, is_wsl=is_wsl)
    except Exception:
        logger.warning("Failed to inject custom variables for terminal %s", terminal_id, exc_info=True)


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
        pairs = (f"{k}={shlex.quote(str(v))}" for k, v in env.items())
    else:
        pairs = (f"{k}={v}" for k, v in env.items())
    line = " && ".join(f"{set_cmd} {p}" for p in pairs)
    pty.write(line + "\r\n")
