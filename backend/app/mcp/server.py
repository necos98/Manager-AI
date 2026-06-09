"""MCP server for Manager AI — Worker Edition.

Exposes a subset of tools appropriate for Claude Code (coding agent) executing
a single pipeline step. Orchestrator-level tools (agent CRUD, pipeline CRUD,
pipeline lifecycle orchestration) live in :mod:`orchestrator_server`.

Mounted at ``/mcp`` on the FastAPI app.
"""

import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.database import async_session

# ── Shared tool implementations (all session-handling logic) ────────────────
from app.mcp.shared_tools import (
    # Issue
    get_issue_details as _get_issue_details,
    get_issue_status as _get_issue_status,
    set_issue_name as _set_issue_name,
    create_issue_spec as _create_issue_spec,
    edit_issue_spec as _edit_issue_spec,
    create_issue_plan as _create_issue_plan,
    edit_issue_plan as _edit_issue_plan,
    create_plan_tasks as _create_plan_tasks,
    replace_plan_tasks as _replace_plan_tasks,
    get_plan_tasks as _get_plan_tasks,
    update_task_status as _update_task_status,
    update_task_name as _update_task_name,
    delete_task as _delete_task,
    complete_issue as _complete_issue,
    accept_issue as _accept_issue,
    cancel_issue as _cancel_issue,
    force_finish_issue as _force_finish_issue,
    get_next_issue as _get_next_issue,
    # Project (read-only)
    get_project_context as _get_project_context,
    get_project_links as _get_project_links,
    get_project_url as _get_project_url,
    # Pipeline run (step-level)
    get_active_agent as _get_active_agent,
    get_active_pipeline_run as _get_active_pipeline_run,
    send_agent_message as _send_agent_message,
    get_pipeline_messages as _get_pipeline_messages,
    finished_pipeline_step as _finished_pipeline_step,
    # Memory
    memory_create as _memory_create,
    memory_update as _memory_update,
    memory_delete as _memory_delete,
    memory_link as _memory_link,
    memory_unlink as _memory_unlink,
    # Files
    list_project_files as _list_project_files,
    read_project_file as _read_project_file,
    # Notifications
    send_notification as _send_notification,
    # Questions
    ask_user_question as _ask_user_question,
    # Plugins (read-only for worker)
    list_plugins as _list_plugins,
    get_plugin_config_tool as _get_plugin_config_tool,
)

logger = logging.getLogger(__name__)

_defaults_path = Path(__file__).parent / "default_settings.json"
_desc: dict[str, str] = json.loads(_defaults_path.read_text(encoding="utf-8"))

mcp = FastMCP(_desc["server.name"], streamable_http_path="/")


# ══════════════════════════════════════════════════════════════════════════════
# WORKER TOOLS — subset appropriate for a coding agent executing one step
# ══════════════════════════════════════════════════════════════════════════════

# ── Issue Tools ──────────────────────────────────────────────────────────────

@mcp.tool(description=_desc["tool.get_issue_details.description"])
async def worker_get_issue_details(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_issue_details(session, project_id, issue_id)


@mcp.tool(description=_desc["tool.get_issue_status.description"])
async def worker_get_issue_status(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_issue_status(session, project_id, issue_id)


@mcp.tool(description=_desc["tool.set_issue_name.description"])
async def worker_set_issue_name(project_id: str, issue_id: str, name: str) -> dict:
    async with async_session() as session:
        return await _set_issue_name(session, project_id, issue_id, name)


@mcp.tool(description=_desc["tool.create_issue_spec.description"])
async def create_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        return await _create_issue_spec(session, project_id, issue_id, spec)


@mcp.tool(description=_desc["tool.edit_issue_spec.description"])
async def edit_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        return await _edit_issue_spec(session, project_id, issue_id, spec)


@mcp.tool(description=_desc["tool.create_issue_plan.description"])
async def create_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        return await _create_issue_plan(session, project_id, issue_id, plan)


@mcp.tool(description=_desc["tool.edit_issue_plan.description"])
async def edit_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        return await _edit_issue_plan(session, project_id, issue_id, plan)


@mcp.tool(description=_desc["tool.create_plan_tasks.description"])
async def create_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        return await _create_plan_tasks(session, issue_id, tasks)


@mcp.tool(description=_desc["tool.replace_plan_tasks.description"])
async def replace_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        return await _replace_plan_tasks(session, issue_id, tasks)


@mcp.tool(description=_desc["tool.get_plan_tasks.description"])
async def get_plan_tasks(issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_plan_tasks(session, issue_id)


@mcp.tool(description=_desc["tool.update_task_status.description"])
async def update_task_status(task_id: str, status: str) -> dict:
    async with async_session() as session:
        return await _update_task_status(session, task_id, status)


@mcp.tool(description=_desc["tool.update_task_name.description"])
async def update_task_name(task_id: str, name: str) -> dict:
    async with async_session() as session:
        return await _update_task_name(session, task_id, name)


@mcp.tool(description=_desc["tool.delete_task.description"])
async def delete_task(task_id: str) -> dict:
    async with async_session() as session:
        return await _delete_task(session, task_id)


@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        return await _complete_issue(session, project_id, issue_id, recap)


@mcp.tool(description=_desc["tool.accept_issue.description"])
async def accept_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _accept_issue(session, project_id, issue_id)


@mcp.tool(description=_desc["tool.cancel_issue.description"])
async def cancel_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _cancel_issue(session, project_id, issue_id)


@mcp.tool(description=_desc["tool.force_finish_issue.description"])
async def force_finish_issue(project_id: str, issue_id: str, recap: str | None = None) -> dict:
    async with async_session() as session:
        return await _force_finish_issue(session, project_id, issue_id, recap)


@mcp.tool(description=_desc["tool.get_next_issue.description"])
async def get_next_issue(project_id: str) -> dict:
    async with async_session() as session:
        return await _get_next_issue(session, project_id)


# ── Project Context Tools (read-only for worker) ────────────────────────────

@mcp.tool(description=_desc["tool.get_project_context.description"])
async def worker_get_project_context(project_id: str) -> dict:
    async with async_session() as session:
        return await _get_project_context(session, project_id)


@mcp.tool(description=_desc["tool.get_project_links.description"])
async def get_project_links(project_id: str) -> dict:
    async with async_session() as session:
        return await _get_project_links(session, project_id)


@mcp.tool(description=_desc["tool.get_project_url.description"])
async def get_project_url(project_id: str) -> dict:
    async with async_session() as session:
        return await _get_project_url(session, project_id)


# ── Pipeline Run Tools (step-level) ─────────────────────────────────────────

@mcp.tool(description=_desc["tool.get_active_agent.description"])
async def worker_get_active_agent(issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_active_agent(session, issue_id)


@mcp.tool(description=_desc["tool.get_active_pipeline_run.description"])
async def worker_get_active_pipeline_run(issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_active_pipeline_run(session, issue_id)


@mcp.tool(description=_desc["tool.send_agent_message.description"])
async def worker_send_agent_message(run_id: str, sender_agent_name: str, content: str) -> dict:
    async with async_session() as session:
        return await _send_agent_message(session, run_id, sender_agent_name, content)


@mcp.tool(description=_desc["tool.get_pipeline_messages.description"])
async def worker_get_pipeline_messages(run_id: str) -> dict:
    async with async_session() as session:
        return await _get_pipeline_messages(session, run_id)


@mcp.tool(description=_desc["tool.finished_pipeline_step.description"])
async def finished_pipeline_step(
    issue_id: str,
    summary: str,
    rejected: bool = False,
    rejection_reason: str | None = None,
    target_step_index: int | None = None,
) -> dict:
    async with async_session() as session:
        return await _finished_pipeline_step(
            session, issue_id, summary,
            rejected=rejected,
            rejection_reason=rejection_reason,
            target_step_index=target_step_index,
        )


# ── Memory Tools ─────────────────────────────────────────────────────────────

@mcp.tool(description=_desc["tool.memory_create.description"])
async def memory_create(project_id: str, title: str, description: str = "", parent_id: str | None = None) -> dict:
    async with async_session() as session:
        return await _memory_create(session, project_id, title, description, parent_id)


@mcp.tool(description=_desc["tool.memory_update.description"])
async def memory_update(memory_id: str, title: str | None = None, description: str | None = None, parent_id: str | None = None, parent_id_clear: bool = False) -> dict:
    async with async_session() as session:
        return await _memory_update(session, memory_id, title=title, description=description, parent_id=parent_id, parent_id_clear=parent_id_clear)


@mcp.tool(description=_desc["tool.memory_delete.description"])
async def memory_delete(memory_id: str) -> dict:
    async with async_session() as session:
        return await _memory_delete(session, memory_id)


@mcp.tool(description=_desc["tool.memory_link.description"])
async def memory_link(from_id: str, to_id: str, relation: str = "") -> dict:
    async with async_session() as session:
        return await _memory_link(session, from_id, to_id, relation)


@mcp.tool(description=_desc["tool.memory_unlink.description"])
async def memory_unlink(from_id: str, to_id: str, relation: str = "") -> dict:
    async with async_session() as session:
        return await _memory_unlink(session, from_id, to_id, relation)


# ── Project File Tools ───────────────────────────────────────────────────────

@mcp.tool(description=_desc["tool.list_project_files.description"])
async def list_project_files(project_id: str) -> dict:
    async with async_session() as session:
        return await _list_project_files(session, project_id)


@mcp.tool(description=_desc["tool.read_project_file.description"])
async def read_project_file(project_id: str, file_id: str, offset: int = 0, max_chars: int = 50000) -> dict:
    async with async_session() as session:
        return await _read_project_file(session, project_id, file_id, offset, max_chars)


# ── Notification Tool ────────────────────────────────────────────────────────

@mcp.tool(description=_desc["tool.send_notification.description"])
async def send_notification(project_id: str, issue_id: str, title: str, message: str = "") -> dict:
    async with async_session() as session:
        return await _send_notification(session, project_id, issue_id, title, message)


# ── Question Tool ────────────────────────────────────────────────────────────

@mcp.tool(description=_desc["tool.ask_user_question.description"])
async def ask_user_question(issue_id: str, question: str, options: list[str] | None = None, timeout_seconds: int = 300) -> dict:
    async with async_session() as session:
        return await _ask_user_question(session, issue_id, question, options=options, timeout_seconds=timeout_seconds)


# ── Plugin Tools (read-only for worker) ──────────────────────────────────────

@mcp.tool(description=_desc["tool.list_plugins.description"])
async def list_plugins(project_id: str) -> dict:
    async with async_session() as session:
        return await _list_plugins(session, project_id)


@mcp.tool(description=_desc["tool.get_plugin_config.description"])
async def get_plugin_config(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        return await _get_plugin_config_tool(session, project_id, plugin_name)
