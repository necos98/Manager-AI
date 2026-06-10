"""Run a single issue — spawn an agent in a terminal and let it work autonomously.

This is the simplest execution mode: create a terminal for the issue,
write the provider's ``build_run_issue_commands`` into the PTY,
and return the terminal ID. No pipeline tables, no step runs —
just fire-and-forget into an interactive agent session.

The terminal is visible in Manager AI's web UI and the agent
works autonomously from there.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppError
from app.models.issue import Issue
from app.providers.registry import AgentProviderRegistry
from app.services.event_service import event_service
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.settings_service import SettingsService
from app.services.terminal_service import terminal_service
from app.utils.datetime import iso_now

logger = logging.getLogger(__name__)


async def run_issue(
    issue_id: str,
    project_id: str,
    *,
    provider_name: str | None = None,
    session: AsyncSession,
) -> dict:
    """Spawn an agent terminal for a single issue.

    Steps:
      1. Validate the issue exists.
      2. Create a PTY terminal via ``terminal_service``.
      3. Resolve the agent provider (from settings or explicit param).
      4. Write provider commands (via ``build_run_issue_commands``) to the PTY.
      5. Emit real-time events so the web UI picks up the new terminal.
      6. Return ``{term_id, status}``.

    The caller receives the terminal ID immediately — the agent works
    autonomously inside the terminal.
    """
    # ── 1) Validate issue ────────────────────────────────────────────────
    issue_service = IssueService(session)
    try:
        issue = await issue_service.get_for_project(issue_id, project_id)
    except AppError as e:
        return {"error": str(e)}

    # ── 2) Load project (for shell / wsl settings) ───────────────────────
    project_service = ProjectService(session)
    try:
        project = await project_service.get_by_id(project_id)
    except AppError as e:
        return {"error": str(e)}

    # ── 3) Resolve provider ──────────────────────────────────────────────
    effective_provider = provider_name
    if not effective_provider:
        settings_service = SettingsService(session)
        effective_provider = await settings_service.get("agent_provider")

    try:
        provider = AgentProviderRegistry.get(effective_provider or "claude")
    except KeyError:
        return {"error": f"Unknown agent provider: {effective_provider}"}

    # ── 4) Guard: reject if issue already has an active terminal ──────────
    existing = terminal_service.list_active(project_id=project_id, issue_id=issue_id)
    if existing:
        return {"error": f"Issue {issue_id} already has an active terminal ({existing[0]['id']})"}

    # ── 5) Create terminal ───────────────────────────────────────────────
    term = terminal_service.create(
        issue_id=issue_id,
        project_id=project_id,
        project_path=project.path,
        shell=project.shell,
        wsl_distro=project.wsl_distro,
    )
    term_id = term["id"]

    # ── 5) WSL cd if needed ──────────────────────────────────────────────
    if project.shell:
        from app.services.wsl_support import is_wsl_shell, win_to_wsl_path
        if is_wsl_shell(project.shell):
            import shlex
            cwd_wsl = win_to_wsl_path(project.path)
            pty_for_cd = terminal_service.get_pty(term_id)
            if pty_for_cd is not None:
                pty_for_cd.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

    # ── 6) Write provider commands ───────────────────────────────────────
    pty = terminal_service.get_pty(term_id)
    if pty is None:
        terminal_service.kill(term_id)
        return {"error": "Failed to create PTY terminal"}

    commands = provider.build_run_issue_commands(issue_id)
    for cmd in commands:
        pty.write(cmd + "\r\n")

    # ── 7) Emit real-time events ────────────────────────────────────────
    await event_service.emit({
        "type": "terminal_created",
        "terminal_id": term_id,
        "issue_id": issue_id,
        "project_id": project_id,
    })

    await event_service.emit({
        "type": "issue_run_started",
        "project_id": project_id,
        "issue_id": issue_id,
        "terminal_id": term_id,
        "provider": effective_provider or "claude",
        "issue_name": issue.name or "",
        "timestamp": iso_now(),
    })

    # ── 8) Return ────────────────────────────────────────────────────────
    return {
        "term_id": term_id,
        "status": "started",
        "provider": effective_provider or "claude",
        "issue_id": issue_id,
        "project_id": project_id,
    }
