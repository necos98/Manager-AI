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


# ── Wrapper helpers ──────────────────────────────────────────────────────────


def _db_tool(fn):
    """Wrap a shared_tool function that takes ``session`` as first argument.

    Creates an async_session, passes it to ``fn``, and returns the JSON dict.
    """
    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            return await fn(session, *args, **kwargs)
    # Preserve the original function's name for introspection
    wrapper.__name__ = fn.__name__
    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# WORKER TOOLS — subset appropriate for a coding agent executing one step
# ══════════════════════════════════════════════════════════════════════════════

# ── Issue Tools ──────────────────────────────────────────────────────────────

@mcp.tool(description=_desc["tool.get_issue_details.description"])
async def get_issue_details(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_issue_details(session, project_id, issue_id)


@mcp.tool(description=_desc["tool.get_issue_status.description"])
async def get_issue_status(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_issue_status(session, project_id, issue_id)


@mcp.tool(description=_desc["tool.set_issue_name.description"])
async def set_issue_name(project_id: str, issue_id: str, name: str) -> dict:
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
async def get_project_context(project_id: str) -> dict:
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

# ── Plugin tools ────────────────────────────────────────────────────────────


from app.mcp.catalog import catalog_loader
from app.mcp.plugin_manager import plugin_manager
from app.mcp.plugin_config import load_plugins, get_plugin_config, PluginsFile


@mcp.tool(description=_desc["tool.list_plugins.description"])
async def list_plugins(project_id: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}

    statuses = plugin_manager.get_status(project_id)
    config = load_plugins(project.path) if project else PluginsFile()

    plugins = []
    for key, cat in catalog_loader.plugins.items():
        proj_cfg = config.plugins.get(key)
        running = next((s for s in statuses if s["name"] == key), None)
        plugins.append({
            "name": key,
            "display_name": cat.name,
            "description": cat.description,
            "enabled": proj_cfg.enabled if proj_cfg else False,
            "connected": running["connected"] if running else False,
            "tool_count": running["tool_count"] if running else 0,
            "access_level": cat.access_level.value,
            "catalog": True,
        })

    return {
        "plugins": plugins,
        "catalog_available": [
            k for k in catalog_loader.plugins
            if k not in config.plugins or not config.plugins[k].enabled
        ],
    }


@mcp.tool(description=_desc["tool.get_plugin_config.description"])
async def get_plugin_config(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
    proj_cfg = get_plugin_config(project.path, plugin_name)
    if proj_cfg is None:
        return {"error": f"Plugin {plugin_name} not found"}
    cat = catalog_loader.get(plugin_name)
    return {
        "name": plugin_name,
        "display_name": cat.name if cat else plugin_name,
        "description": cat.description if cat else "",
        "enabled": proj_cfg.enabled,
        "transport": cat.transport.value if cat else "unknown",
        "command": cat.command if cat and cat.transport.value == "stdio" else None,
        "args": cat.args if cat and cat.transport.value == "stdio" else None,
        "url": cat.url if cat and cat.transport.value == "http" else None,
        "config_keys": list(proj_cfg.config.keys()),
        "access_level": cat.access_level.value if cat else "unknown",
        "timeout": cat.timeout if cat else 30,
        "catalog": cat is not None,
    }


@mcp.tool(description=_desc["tool.enable_plugin.description"])
async def enable_plugin(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
    cat = catalog_loader.get(plugin_name)
    if cat is None:
        return {"error": f"Plugin '{plugin_name}' not found in catalog. Available: {list(catalog_loader.plugins.keys())}"}
    success = await plugin_manager.enable_plugin(
        project_id, project.path, plugin_name, mcp
    )
    return {"success": success}


@mcp.tool(description=_desc["tool.disable_plugin.description"])
async def disable_plugin(project_id: str, plugin_name: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
    success = await plugin_manager.disable_plugin(
        project_id, project.path, plugin_name, mcp
    )
    return {"success": success}


# ── Question tools ───────────────────────────────────────────────────────────

from app.services.question_service import QuestionService, question_store


@mcp.tool(description=_desc["tool.ask_user_question.description"])
async def ask_user_question(issue_id: str, question: str, options: list[str] | None = None, timeout_seconds: int = 300) -> dict:
    if not question.strip():
        return {"error": "Question text cannot be empty"}
    if timeout_seconds < 5 or timeout_seconds > 3600:
        return {"error": "Timeout must be between 5 and 3600 seconds"}

    async with async_session() as session:
        issue_service = IssueService(session)
        issue = await issue_service.get_by_id(issue_id)
        if issue is None:
            return {"error": "Issue not found"}
        project_id = issue.project_id

        qsvc = QuestionService(session)
        q = await qsvc.create(
            project_id=project_id,
            issue_id=issue_id,
            question=question,
            options=options,
        )

        await event_service.emit({
            "type": "question_asked",
            "question_id": q.id,
            "project_id": project_id,
            "issue_id": issue_id,
            "question": q.question,
            "options": q.options,
            "timestamp": iso_now(),
        })

        issue_name = _issue_display_name(issue) or "Untitled issue"
        project = await ProjectService(session).get_by_id(project_id)
        project_name = project.name if project else ""
        await event_service.emit({
            "type": "notification",
            "title": "New question from AI",
            "message": q.question,
            "project_id": project_id,
            "issue_id": issue_id,
            "issue_name": issue_name,
            "project_name": project_name,
            "timestamp": iso_now(),
        })

    event = question_store.wait(q.id)
    if event is None:
        return {"error": "Question not found in store"}

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        async with async_session() as session:
            await QuestionService(session).timeout(q.id)
        await event_service.emit({
            "type": "question_answered",
            "question_id": q.id,
            "project_id": project_id,
            "issue_id": issue_id,
            "status": "timed_out",
            "timestamp": iso_now(),
        })
        return {"timed_out": True, "question_id": q.id}

    updated = question_store.get(q.id)
    return {
        "question_id": q.id,
        "answer": updated.answer if updated else None,
        "selected_option": updated.selected_option if updated else None,
        "timed_out": False,
    }


# ── Agent tools ────────────────────────────────────────────────────────────


@mcp.tool(description=_desc["tool.create_agent.description"])
@mcp_tool_wrapper
async def create_agent(session, name: str, intent: str = "", model: str | None = None, allowed_tools: list[str] | None = None, provider: str | None = None) -> dict:
    svc = AgentService(session)
    agent = await svc.create(
        name=name,
        model=model,
        allowed_tools=allowed_tools,
        intent=intent,
        provider=provider,
    )
    await session.commit()
    return _serialize_agent(agent)


@mcp.tool(description=_desc["tool.list_agents.description"])
async def list_agents() -> dict:
    async with async_session() as session:
        svc = AgentService(session)
        agents = await svc.list_all()
        return {
            "agents": [_serialize_agent(a) for a in agents]
        }


@mcp.tool(description=_desc["tool.get_agent.description"])
@mcp_tool_wrapper
async def get_agent(session, agent_id: str) -> dict:
    svc = AgentService(session)
    agent = await svc.get_by_id(agent_id)
    return _serialize_agent(agent)


@mcp.tool(description=_desc["tool.update_agent.description"])
@mcp_tool_wrapper
async def update_agent(session, agent_id: str, name: str | None = None, intent: str | None = None, model: str | None = None, allowed_tools: list[str] | None = None, provider: str | None = None) -> dict:
    svc = AgentService(session)
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if intent is not None:
        kwargs["intent"] = intent
    if model is not None:
        kwargs["model"] = model
    if allowed_tools is not None:
        kwargs["allowed_tools"] = allowed_tools
    if provider is not None:
        kwargs["provider"] = provider
    agent = await svc.update(agent_id, **kwargs)
    await session.commit()
    return _serialize_agent(agent)


@mcp.tool(description=_desc["tool.delete_agent.description"])
@mcp_tool_wrapper
async def delete_agent(session, agent_id: str) -> dict:
    svc = AgentService(session)
    await svc.delete(agent_id)
    await session.commit()
    return {"deleted": True}


# ── Pipeline tools ────────────────────────────────────────────────────────


@mcp.tool(description=_desc["tool.create_pipeline.description"])
@mcp_tool_wrapper
async def create_pipeline(session, name: str, steps: list[dict]) -> dict:
    svc = PipelineService(session)
    pipeline = await svc.create_pipeline(name)
    for step_data in steps:
        await svc.add_step(
            pipeline_id=pipeline.id,
            agent_id=step_data["agent_id"],
            order_index=step_data.get("order_index", 0),
        )
    await session.commit()
    pipeline = await svc.get_pipeline(pipeline.id)
    return _serialize_pipeline(pipeline)


@mcp.tool(description=_desc["tool.list_pipelines.description"])
async def list_pipelines() -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        pipelines = await svc.list_all()
        return {
            "pipelines": [_serialize_pipeline(p) for p in pipelines]
        }


@mcp.tool(description=_desc["tool.get_pipeline.description"])
@mcp_tool_wrapper
async def get_pipeline(session, pipeline_id: str) -> dict:
    svc = PipelineService(session)
    pipeline = await svc.get_pipeline(pipeline_id)
    return _serialize_pipeline(pipeline)


@mcp.tool(description=_desc["tool.update_pipeline.description"])
@mcp_tool_wrapper
async def update_pipeline(session, pipeline_id: str, name: str) -> dict:
    svc = PipelineService(session)
    await svc.update_pipeline(pipeline_id, name)
    await session.commit()
    pipeline = await svc.get_pipeline(pipeline_id)
    return _serialize_pipeline(pipeline)


@mcp.tool(description=_desc["tool.delete_pipeline.description"])
@mcp_tool_wrapper
async def delete_pipeline(session, pipeline_id: str) -> dict:
    svc = PipelineService(session)
    await svc.delete_pipeline(pipeline_id)
    await session.commit()
    return {"deleted": True}


@mcp.tool(description=_desc["tool.add_step.description"])
@mcp_tool_wrapper
async def add_step(session, pipeline_id: str, agent_id: str, order_index: int = 0) -> dict:
    svc = PipelineService(session)
    await svc.add_step(pipeline_id, agent_id, order_index)
    await session.commit()
    pipeline = await svc.get_pipeline(pipeline_id)
    return _serialize_pipeline(pipeline)


@mcp.tool(description=_desc["tool.remove_step.description"])
async def remove_step(step_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        try:
            await svc.remove_step(step_id)
            await session.commit()
            return {"deleted": True}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.reorder_steps.description"])
@mcp_tool_wrapper
async def reorder_steps(session, pipeline_id: str, step_ids: list[str]) -> dict:
    svc = PipelineService(session)
    await svc.reorder_steps(pipeline_id, step_ids)
    await session.commit()
    pipeline = await svc.get_pipeline(pipeline_id)
    return _serialize_pipeline(pipeline)


# ── Pipeline event rule tools ──────────────────────────────────────


@mcp.tool(description=_desc["tool.add_pipeline_event_rule.description"])
async def add_pipeline_event_rule(
    pipeline_id: str,
    event_type: str,
    source_step_id: str,
    target_step_id: str,
) -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        try:
            rule = await svc.add_event_rule(
                pipeline_id=pipeline_id,
                event_type=event_type,
                source_step_id=source_step_id,
                target_step_id=target_step_id,
            )
            await session.commit()
            return {
                "id": rule.id,
                "pipeline_id": rule.pipeline_id,
                "event_type": rule.event_type,
                "source_step_id": rule.source_step_id,
                "target_step_id": rule.target_step_id,
                "enabled": rule.enabled,
            }
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.remove_pipeline_event_rule.description"])
async def remove_pipeline_event_rule(rule_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        try:
            await svc.remove_event_rule(rule_id)
            await session.commit()
            return {"deleted": True}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.list_pipeline_event_rules.description"])
async def list_pipeline_event_rules(pipeline_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineService(session)
        rules = await svc.list_event_rules(pipeline_id)
        return {
            "rules": [
                {
                    "id": r.id,
                    "pipeline_id": r.pipeline_id,
                    "event_type": r.event_type,
                    "source_step_id": r.source_step_id,
                    "target_step_id": r.target_step_id,
                    "enabled": r.enabled,
                }
                for r in rules
            ]
        }


# ── Pipeline run tools ────────────────────────────────────────────────────


@mcp.tool(description=_desc["tool.run_pipeline.description"])
async def run_pipeline(project_id: str, pipeline_id: str, issue_id: str,
                       orchestrated: bool = False) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
        svc = PipelineRunService(session, session_factory=async_session)
        try:
            result = await svc.start(
                pipeline_id=pipeline_id,
                issue_id=issue_id,
                project_id=project_id,
                project_path=project.path,
                orchestrated=orchestrated,
            )
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.get_pipeline_run_status.description"])
async def get_pipeline_run_status(run_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        try:
            return await svc.get_run(run_id)
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.get_active_agent.description"])
async def get_active_agent(issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_active_agent(session, issue_id)


@mcp.tool(description=_desc["tool.get_active_pipeline_run.description"])
async def get_active_pipeline_run(issue_id: str) -> dict:
    async with async_session() as session:
        return await _get_active_pipeline_run(session, issue_id)


@mcp.tool(description=_desc["tool.send_agent_message.description"])
async def send_agent_message(run_id: str, sender_agent_name: str, content: str) -> dict:
    async with async_session() as session:
        return await _send_agent_message(session, run_id, sender_agent_name, content)


@mcp.tool(description=_desc["tool.get_pipeline_messages.description"])
async def get_pipeline_messages(run_id: str) -> dict:
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
