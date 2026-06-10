"""MCP server for Manager AI — Orchestrator Edition.

Exposes a curated set of tools for Hermes (the orchestrator AI agent):
Issues (CRUD), Agents (CRUD), Pipelines (CRUD + Steps + Event Rules),
Pipeline Runs (execution lifecycle), read-only Project queries, and
Project Context.

Mounted at ``/mcp-orchestrator/`` on the FastAPI app.
"""

import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.database import async_session

# ── Shared tool implementations ──────────────────────────────────────────────
from app.mcp.shared_tools import (
    # Issue
    get_issue_details as _get_issue_details,
    get_issue_status as _get_issue_status,
    list_issues as _list_issues,
    get_issue_statuses as _get_issue_statuses,
    create_issue as _create_issue,
    set_issue_name as _set_issue_name,
    delete_issue as _delete_issue,
    # Project (essentials only)
    get_project_context as _get_project_context,
    # Agents
    create_agent as _create_agent,
    list_agents as _list_agents,
    get_agent as _get_agent,
    update_agent as _update_agent,
    delete_agent as _delete_agent,
    # Pipelines
    create_pipeline as _create_pipeline,
    list_pipelines_tool as _list_pipelines_tool,
    get_pipeline_tool as _get_pipeline_tool,
    update_pipeline_tool as _update_pipeline_tool,
    delete_pipeline_tool as _delete_pipeline_tool,
    add_step as _add_step,
    remove_step as _remove_step,
    reorder_steps as _reorder_steps,
    # Pipeline event rules
    add_pipeline_event_rule as _add_pipeline_event_rule,
    remove_pipeline_event_rule as _remove_pipeline_event_rule,
    list_pipeline_event_rules_tool as _list_pipeline_event_rules_tool,
    update_pipeline_event_rule_tool as _update_pipeline_event_rule_tool,
    # Pipeline runs
    run_pipeline as _run_pipeline,
    run_issue as _run_issue,
    get_pipeline_run_status as _get_pipeline_run_status,
    get_active_agent as _get_active_agent,
    get_active_pipeline_run as _get_active_pipeline_run,
    send_agent_message as _send_agent_message,
    get_pipeline_messages as _get_pipeline_messages,
    pause_pipeline as _pause_pipeline,
    resume_pipeline as _resume_pipeline,
    cancel_pipeline as _cancel_pipeline,
    # Projects (read-only essentials)
    list_projects as _list_projects,
    get_project as _get_project,
    # Plugins
    enable_plugin_tool as _enable_plugin_tool,
    disable_plugin_tool as _disable_plugin_tool,
    # Memory search
    memory_search as _memory_search,
    # Issue Queue
    queue_add as _queue_add,
    queue_list as _queue_list,
    queue_remove as _queue_remove,
    queue_position as _queue_position,
)

logger = logging.getLogger(__name__)

_defaults_path = Path(__file__).parent / "default_settings.json"
_desc: dict[str, str] = json.loads(_defaults_path.read_text(encoding="utf-8"))

# Use a distinct server name so clients can tell which MCP they connected to
orchestrator_mcp = FastMCP("Manager AI Orchestrator", streamable_http_path="/", stateless=True)


# ══════════════════════════════════════════════════════════════════════════════
# TOOLS — Orchestrator Edition
# ══════════════════════════════════════════════════════════════════════════════

# ── 1) Issue Tools ────────────────────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.get_issue_details.description"])
async def get_issue_details(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_issue_details(session, project_id, issue_id)


@orchestrator_mcp.tool(description=_desc["tool.get_issue_status.description"])
async def get_issue_status(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_issue_status(session, project_id, issue_id)


@orchestrator_mcp.tool(description=_desc["tool.list_issues.description"])
async def list_issues(
    project_id: str,
    status: str | None = None,
    search: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    async with async_session() as session:
        return await _list_issues(session, project_id, status=status, search=search, tag=tag, limit=limit, offset=offset)


@orchestrator_mcp.tool(description=_desc["tool.get_issue_statuses.description"])
async def get_issue_statuses() -> dict:
    return await _get_issue_statuses()


@orchestrator_mcp.tool(description=_desc["tool.create_issue.description"])
async def create_issue(project_id: str, description: str, priority: int = 3) -> dict:
    async with async_session() as session:
        return await _create_issue(session, project_id, description, priority)


@orchestrator_mcp.tool(description="Permanently delete an issue. Irreversible.")
async def delete_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _delete_issue(session, project_id, issue_id)


@orchestrator_mcp.tool(description=_desc["tool.set_issue_name.description"])
async def set_issue_name(project_id: str, issue_id: str, name: str) -> dict:
    async with async_session() as session:
        return await _set_issue_name(session, project_id, issue_id, name)


# ── 2) Project Context Tools ─────────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.get_project_context.description"])
async def get_project_context(project_id: str) -> dict:
    async with async_session() as session:
        return await _get_project_context(session, project_id)


# ── 3) Agent Tools ────────────────────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.create_agent.description"])
async def create_agent(name: str, intent: str = "", model: str | None = None, allowed_tools: list[str] | None = None) -> dict:
    async with async_session() as session:
        return await _create_agent(session, name, intent=intent, model=model, allowed_tools=allowed_tools)


@orchestrator_mcp.tool(description=_desc["tool.list_agents.description"])
async def list_agents() -> dict:
    async with async_session() as session:
        return await _list_agents(session)


@orchestrator_mcp.tool(description=_desc["tool.get_agent.description"])
async def get_agent(agent_id: str) -> dict:
    async with async_session() as session:
        return await _get_agent(session, agent_id)


@orchestrator_mcp.tool(description=_desc["tool.update_agent.description"])
async def update_agent(agent_id: str, name: str | None = None, intent: str | None = None, model: str | None = None, allowed_tools: list[str] | None = None) -> dict:
    async with async_session() as session:
        return await _update_agent(session, agent_id, name=name, intent=intent, model=model, allowed_tools=allowed_tools)


@orchestrator_mcp.tool(description=_desc["tool.delete_agent.description"])
async def delete_agent(agent_id: str) -> dict:
    async with async_session() as session:
        return await _delete_agent(session, agent_id)


# ── 4) Pipeline Management Tools ─────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.create_pipeline.description"])
async def create_pipeline(name: str, steps: list[dict]) -> dict:
    async with async_session() as session:
        return await _create_pipeline(session, name, steps)


@orchestrator_mcp.tool(description=_desc["tool.list_pipelines.description"])
async def list_pipelines() -> dict:
    async with async_session() as session:
        return await _list_pipelines_tool(session)


@orchestrator_mcp.tool(description=_desc["tool.get_pipeline.description"])
async def get_pipeline(pipeline_id: str) -> dict:
    async with async_session() as session:
        return await _get_pipeline_tool(session, pipeline_id)


@orchestrator_mcp.tool(description=_desc["tool.update_pipeline.description"])
async def update_pipeline(pipeline_id: str, name: str) -> dict:
    async with async_session() as session:
        return await _update_pipeline_tool(session, pipeline_id, name)


@orchestrator_mcp.tool(description=_desc["tool.delete_pipeline.description"])
async def delete_pipeline(pipeline_id: str) -> dict:
    async with async_session() as session:
        return await _delete_pipeline_tool(session, pipeline_id)


@orchestrator_mcp.tool(description=_desc["tool.add_step.description"])
async def add_step(pipeline_id: str, agent_id: str, order_index: int = 0) -> dict:
    async with async_session() as session:
        return await _add_step(session, pipeline_id, agent_id, order_index)


@orchestrator_mcp.tool(description=_desc["tool.remove_step.description"])
async def remove_step(step_id: str) -> dict:
    async with async_session() as session:
        return await _remove_step(session, step_id)


@orchestrator_mcp.tool(description=_desc["tool.reorder_steps.description"])
async def reorder_steps(pipeline_id: str, step_ids: list[str]) -> dict:
    async with async_session() as session:
        return await _reorder_steps(session, pipeline_id, step_ids)


# ── 4.1) Pipeline Event Rule Tools ─────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.add_pipeline_event_rule.description"])
async def add_pipeline_event_rule(
    pipeline_id: str,
    event_type: str,
    source_step_id: str,
    target_step_id: str,
    action_type: str = "redirect",
    action_params: dict | None = None,
) -> dict:
    async with async_session() as session:
        return await _add_pipeline_event_rule(
            session, pipeline_id, event_type,
            source_step_id, target_step_id,
            action_type, action_params,
        )


@orchestrator_mcp.tool(description=_desc["tool.remove_pipeline_event_rule.description"])
async def remove_pipeline_event_rule(rule_id: str) -> dict:
    async with async_session() as session:
        return await _remove_pipeline_event_rule(session, rule_id)


@orchestrator_mcp.tool(description=_desc["tool.list_pipeline_event_rules.description"])
async def list_pipeline_event_rules(pipeline_id: str) -> dict:
    async with async_session() as session:
        return await _list_pipeline_event_rules_tool(session, pipeline_id)


@orchestrator_mcp.tool(description=_desc["tool.update_pipeline_event_rule.description"])
async def update_pipeline_event_rule(
    rule_id: str,
    event_type: str | None = None,
    source_step_id: str | None = None,
    target_step_id: str | None = None,
    action_type: str | None = None,
    action_params: dict | None = None,
    enabled: bool | None = None,
) -> dict:
    async with async_session() as session:
        return await _update_pipeline_event_rule_tool(
            session, rule_id, event_type,
            source_step_id, target_step_id,
            action_type, action_params, enabled,
        )


# ── 5) Pipeline Run Tools ─────────────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.run_pipeline.description"])
async def run_pipeline(project_id: str, pipeline_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _run_pipeline(session, project_id, pipeline_id, issue_id)


@orchestrator_mcp.tool(
    description="Run a single issue directly — spawn a terminal with the configured agent provider and let it work autonomously. "
                "No pipeline, no multi-agent orchestration. Just fire the agent at the issue. "
                "Parameters: project_id (required), issue_id (required), provider_name (optional — defaults to the configured agent_provider). "
                "Returns: {term_id, status, provider, issue_id, project_id}. "
                "The terminal is visible in the Manager AI web UI."
)
async def run_issue(project_id: str, issue_id: str, provider_name: str | None = None) -> dict:
    async with async_session() as session:
        return await _run_issue(session, project_id, issue_id, provider_name=provider_name)


@orchestrator_mcp.tool(description=_desc["tool.get_pipeline_run_status.description"])
async def get_pipeline_run_status(run_id: str) -> dict:
    async with async_session() as session:
        return await _get_pipeline_run_status(session, run_id)


@orchestrator_mcp.tool(description=_desc["tool.get_active_agent.description"])
async def get_active_agent(issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_active_agent(session, issue_id)


@orchestrator_mcp.tool(description=_desc["tool.get_active_pipeline_run.description"])
async def get_active_pipeline_run(issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_active_pipeline_run(session, issue_id)


@orchestrator_mcp.tool(description=_desc["tool.send_agent_message.description"])
async def send_agent_message(run_id: str, sender_agent_name: str, content: str) -> dict:
    async with async_session() as session:
        return await _send_agent_message(session, run_id, sender_agent_name, content)


@orchestrator_mcp.tool(description=_desc["tool.get_pipeline_messages.description"])
async def get_pipeline_messages(run_id: str) -> dict:
    async with async_session() as session:
        return await _get_pipeline_messages(session, run_id)


@orchestrator_mcp.tool(description=_desc["tool.pause_pipeline.description"])
async def pause_pipeline(run_id: str) -> dict:
    async with async_session() as session:
        return await _pause_pipeline(session, run_id)


@orchestrator_mcp.tool(description=_desc["tool.resume_pipeline.description"])
async def resume_pipeline(run_id: str) -> dict:
    async with async_session() as session:
        return await _resume_pipeline(session, run_id)


@orchestrator_mcp.tool(description=_desc["tool.cancel_pipeline.description"])
async def cancel_pipeline(run_id: str) -> dict:
    async with async_session() as session:
        return await _cancel_pipeline(session, run_id)


# ── 6) Project Tools (read-only) ─────────────────────────────────────────────


@orchestrator_mcp.tool(
    description="List all projects. Pass archived=True to include archived projects. "
                "Returns each project's id, name, path, description, tech_stack, "
                "issue_counts, and archived_at status."
)
async def list_projects(archived: bool = False) -> dict:
    async with async_session() as session:
        return await _list_projects(session, archived)


@orchestrator_mcp.tool(
    description="Get detailed information about a single project, including issue counts by status."
)
async def get_project(project_id: str) -> dict:
    async with async_session() as session:
        return await _get_project(session, project_id)


# ── 6.5) Memory Search Tool ────────────────────────────────────────────────────


@orchestrator_mcp.tool(
    description="Full-text search across a project's memory titles "
                "and descriptions. Returns matches with snippet and rank."
)
async def memory_search(project_id: str, query: str, limit: int = 20) -> dict:
    async with async_session() as session:
        return await _memory_search(session, project_id, query, limit)


# ── 7) Plugin Tools ────────────────────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.enable_plugin.description"])
async def enable_plugin(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        return await _enable_plugin_tool(session, project_id, plugin_name)


@orchestrator_mcp.tool(description=_desc["tool.disable_plugin.description"])
async def disable_plugin(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        return await _disable_plugin_tool(session, project_id, plugin_name)


# ── 8) Issue Queue Tools ──────────────────────────────────────────────────────


@orchestrator_mcp.tool(
    description="Add an issue to the FIFO queue. "
    "Validates that the issue is in NEW or ACCEPTED status. "
    "The issue retains its original status — QueueEntry is the authoritative record. "
                "Parameters: project_id (required), issue_id (required). "
                "Returns: {id, project_id, status}."
)
async def queue_add(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _queue_add(session, project_id, issue_id)


@orchestrator_mcp.tool(
    description="List all QUEUED issues with their position (1-based FIFO order). "
                "Uses the persistent QueueEntry table. "
                "Parameters: project_id (required). "
                "Returns: {queued: [{position, issue_id, issue_name, description, created_at}], total}."
)
async def queue_list(project_id: str) -> dict:
    async with async_session() as session:
        return await _queue_list(session, project_id)


@orchestrator_mcp.tool(
    description="Remove an issue from the queue. "
                "The issue retains its original status — membership is tracked via QueueEntry. "
                "Parameters: project_id (required), issue_id (required). "
                "Returns: {id, project_id, status}."
)
async def queue_remove(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _queue_remove(session, project_id, issue_id)


@orchestrator_mcp.tool(
    description="Get the 1-based position of a pending issue in the FIFO queue. "
                "Returns null position if the issue has no pending QueueEntry. "
                "Parameters: project_id (required), issue_id (required). "
                "Returns: {position, issue_id, total} or {position: null, issue_id, status}."
)
async def queue_position(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _queue_position(session, project_id, issue_id)
