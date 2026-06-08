"""MCP server for Manager AI — Orchestrator Edition.

Exposes a curated set of tools for Hermes (the orchestrator AI agent):
Issues (CRUD), Agents (CRUD), Pipelines (CRUD + Steps + Event Rules),
Pipeline Runs (execution lifecycle), read-only Project queries, and
Project Context.

Mounted at ``/mcp-orchestrator`` on the FastAPI app.
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
    create_issue as _create_issue,
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
    get_pipeline_run_status as _get_pipeline_run_status,
    get_active_agent as _get_active_agent,
    get_active_pipeline_run as _get_active_pipeline_run,
    send_agent_message as _send_agent_message,
    get_pipeline_messages as _get_pipeline_messages,
    finished_pipeline_step as _finished_pipeline_step,
    start_pipeline_step as _start_pipeline_step,
    advance_pipeline as _advance_pipeline,
    pause_pipeline as _pause_pipeline,
    resume_pipeline as _resume_pipeline,
    # Projects (read-only essentials)
    list_projects as _list_projects,
    get_project as _get_project,
)

logger = logging.getLogger(__name__)

_defaults_path = Path(__file__).parent / "default_settings.json"
_desc: dict[str, str] = json.loads(_defaults_path.read_text(encoding="utf-8"))

# Use a distinct server name so clients can tell which MCP they connected to
orchestrator_mcp = FastMCP("Manager AI Orchestrator", streamable_http_path="/")


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


@orchestrator_mcp.tool(description=_desc["tool.create_issue.description"])
async def create_issue(project_id: str, description: str, priority: int = 3) -> dict:
    async with async_session() as session:
        return await _create_issue(session, project_id, description, priority)


@orchestrator_mcp.tool(description="Permanently delete an issue. Irreversible.")
async def delete_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _delete_issue(session, project_id, issue_id)


# ── 2) Project Context Tools ─────────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.get_project_context.description"])
async def get_project_context(project_id: str) -> dict:
    async with async_session() as session:
        return await _get_project_context(session, project_id)


# ── 3) Agent Tools ────────────────────────────────────────────────────────────


@orchestrator_mcp.tool(description=_desc["tool.create_agent.description"])
async def create_agent(name: str, intent: str = "", model: str | None = None, allowed_tools: list[str] | None = None, provider: str | None = None) -> dict:
    async with async_session() as session:
        return await _create_agent(session, name, intent=intent, model=model, allowed_tools=allowed_tools, provider=provider)


@orchestrator_mcp.tool(description=_desc["tool.list_agents.description"])
async def list_agents() -> dict:
    async with async_session() as session:
        return await _list_agents(session)


@orchestrator_mcp.tool(description=_desc["tool.get_agent.description"])
async def get_agent(agent_id: str) -> dict:
    async with async_session() as session:
        return await _get_agent(session, agent_id)


@orchestrator_mcp.tool(description=_desc["tool.update_agent.description"])
async def update_agent(agent_id: str, name: str | None = None, intent: str | None = None, model: str | None = None, allowed_tools: list[str] | None = None, provider: str | None = None) -> dict:
    async with async_session() as session:
        return await _update_agent(session, agent_id, name=name, intent=intent, model=model, allowed_tools=allowed_tools, provider=provider)


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
async def run_pipeline(project_id: str, pipeline_id: str, issue_id: str, orchestrated: bool = False) -> dict:
    async with async_session() as session:
        return await _run_pipeline(session, project_id, pipeline_id, issue_id, orchestrated)


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


@orchestrator_mcp.tool(description=_desc["tool.finished_pipeline_step.description"])
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


@orchestrator_mcp.tool(description=_desc["tool.start_pipeline_step.description"])
async def start_pipeline_step(run_id: str, project_id: str) -> dict:
    async with async_session() as session:
        return await _start_pipeline_step(session, run_id, project_id)


@orchestrator_mcp.tool(description=_desc["tool.advance_pipeline.description"])
async def advance_pipeline(run_id: str) -> dict:
    async with async_session() as session:
        return await _advance_pipeline(session, run_id)


@orchestrator_mcp.tool(description=_desc["tool.pause_pipeline.description"])
async def pause_pipeline(run_id: str) -> dict:
    async with async_session() as session:
        return await _pause_pipeline(session, run_id)


@orchestrator_mcp.tool(description=_desc["tool.resume_pipeline.description"])
async def resume_pipeline(run_id: str) -> dict:
    async with async_session() as session:
        return await _resume_pipeline(session, run_id)


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
