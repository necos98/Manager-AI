import asyncio
import logging
import json
from pathlib import Path
import functools

from mcp.server.fastmcp import FastMCP


from app.utils.datetime import iso_now, now
from sqlalchemy import select

from app.database import async_session
from app.exceptions import AppError
from app.services.agent_service import AgentService
from app.services.event_service import event_service
from app.services.issue_service import IssueService
from app.services.pipeline_run_service import PipelineRunService, set_step_completed
from app.services.pipeline_service import PipelineService
from app.services.project_service import ProjectService
from app.models.issue import IssueStatus
from app.models.task import TaskStatus
from app.services.task_service import TaskService
from app.services.settings_service import SettingsService

_defaults_path = Path(__file__).parent / "default_settings.json"
_desc = json.loads(_defaults_path.read_text(encoding="utf-8"))

mcp = FastMCP(_desc["server.name"], streamable_http_path="/")

logger = logging.getLogger(__name__)


def _issue_display_name(issue, max_len: int = 50) -> str:
    return issue.name or (issue.description or "")[:max_len] or ""


def _serialize_agent(agent) -> dict:
    return {
        "id": agent.id,
        "name": agent.name,
        "provider": agent.provider,
        "intent": agent.intent,
        "model": agent.model,
        "allowed_tools": agent.allowed_tools,
        "created_at": str(agent.created_at) if agent.created_at else None,
        "updated_at": str(agent.updated_at) if agent.updated_at else None,
    }


def _serialize_pipeline(pipeline) -> dict:
    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "steps": [
            {
                "id": s.id,
                "pipeline_id": s.pipeline_id,
                "agent_id": s.agent_id,
                "order_index": s.order_index,
            }
            for s in (pipeline.steps or [])
        ],
        "created_at": str(pipeline.created_at) if pipeline.created_at else None,
        "updated_at": str(pipeline.updated_at) if pipeline.updated_at else None,
    }


def mcp_tool_wrapper(func):
    """Wraps async with async_session() + try/except AppError."""
    import inspect as _inspect
    _sig = _inspect.signature(func)
    _no_session = [p for p in _sig.parameters.values() if p.name != "session"]
    _new_sig = _sig.replace(parameters=_no_session)

    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            try:
                return await func(session, *args, **kwargs)
            except AppError as e:
                return {"error": e.message}

    wrapper.__name__ = func.__name__
    wrapper.__signature__ = _new_sig
    return wrapper


@mcp.tool(description=_desc["tool.get_issue_details.description"])
@mcp_tool_wrapper
async def get_issue_details(session, project_id: str, issue_id: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.get_for_project(issue_id, project_id)
    return {
        "id": issue.id,
        "project_id": issue.project_id,
        "name": issue.name,
        "description": issue.description,
        "status": issue.status,
        "priority": issue.priority,
        "specification": issue.specification,
        "plan": issue.plan,
        "recap": issue.recap,
        "tasks": [
            {"id": t.id, "name": t.name, "status": t.status, "order": t.order}
            for t in issue.tasks
        ],
        "created_at": issue.created_at or None,
        "updated_at": issue.updated_at or None,
    }


@mcp.tool(description=_desc["tool.get_issue_status.description"])
@mcp_tool_wrapper
async def get_issue_status(session, project_id: str, issue_id: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.get_for_project(issue_id, project_id)
    return {"id": issue.id, "status": issue.status}


@mcp.tool(description=_desc["tool.get_project_context.description"])
@mcp_tool_wrapper
async def get_project_context(session, project_id: str) -> dict:
    project_service = ProjectService(session)
    project = await project_service.get_by_id(project_id)
    return {
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "tech_stack": project.tech_stack,
    }


@mcp.tool(description=_desc["tool.update_project_context.description"])
@mcp_tool_wrapper
async def update_project_context(session, project_id: str, description: str | None = None, tech_stack: str | None = None) -> dict:
    project_service = ProjectService(session)
    project = await project_service.update(project_id, description=description, tech_stack=tech_stack)
    await session.commit()
    await event_service.emit({
        "type": "project_updated",
        "project_id": project_id,
        "timestamp": iso_now(),
    })
    return {
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "tech_stack": project.tech_stack,
    }


@mcp.tool(description=_desc["tool.set_issue_name.description"])
@mcp_tool_wrapper
async def set_issue_name(session, project_id: str, issue_id: str, name: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.set_name(issue_id, project_id, name)
    await session.commit()
    await event_service.emit({
        "type": "issue_content_updated",
        "content_type": "name",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue.name or "",
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "name": issue.name}


@mcp.tool(description=_desc["tool.complete_issue.description"])
@mcp_tool_wrapper
async def complete_issue(session, project_id: str, issue_id: str, recap: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.complete_issue(issue_id, project_id, recap)
    # Extract data while session is open
    issue_data = {
        "name": _issue_display_name(issue, max_len=100),
        "specification": issue.specification,
        "plan": issue.plan,
        "recap": issue.recap,
    }
    issue_id_val = issue.id
    issue_name = _issue_display_name(issue)
    issue_status = issue.status
    await session.commit()

    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": issue_status,
        "project_id": project_id,
        "issue_id": issue_id_val,
        "issue_name": issue_name,
        "timestamp": iso_now(),
    })

    return {"id": issue_id_val, "status": issue_status, "recap": issue.recap}


@mcp.tool(description=_desc["tool.create_issue.description"])
async def create_issue(project_id: str, description: str, priority: int = 3) -> dict:
    if not description or not description.strip():
        return {"error": "Description cannot be blank"}
    if priority < 1 or priority > 5:
        return {"error": "Priority must be between 1 and 5"}
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create(
                project_id=project_id,
                description=description,
                priority=priority,
            )
            result = {
                "id": issue.id,
                "project_id": issue.project_id,
                "description": issue.description,
                "priority": issue.priority,
                "status": issue.status,
            }
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.create_issue_spec.description"])
@mcp_tool_wrapper
async def create_issue_spec(session, project_id: str, issue_id: str, spec: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.create_spec(issue_id, project_id, spec)
    await session.commit()
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": issue.status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": _issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "specification": issue.specification}


@mcp.tool(description=_desc["tool.edit_issue_spec.description"])
@mcp_tool_wrapper
async def edit_issue_spec(session, project_id: str, issue_id: str, spec: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.edit_spec(issue_id, project_id, spec)
    await session.commit()
    await event_service.emit({
        "type": "issue_content_updated",
        "content_type": "spec",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": _issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "specification": issue.specification}


@mcp.tool(description=_desc["tool.create_issue_plan.description"])
@mcp_tool_wrapper
async def create_issue_plan(session, project_id: str, issue_id: str, plan: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.create_plan(issue_id, project_id, plan)
    await session.commit()
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": issue.status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": _issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "plan": issue.plan}


@mcp.tool(description=_desc["tool.edit_issue_plan.description"])
@mcp_tool_wrapper
async def edit_issue_plan(session, project_id: str, issue_id: str, plan: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.edit_plan(issue_id, project_id, plan)
    await session.commit()
    await event_service.emit({
        "type": "issue_content_updated",
        "content_type": "plan",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": _issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "plan": issue.plan}
@mcp.tool(description=_desc["tool.accept_issue.description"])
@mcp_tool_wrapper
async def accept_issue(session, project_id: str, issue_id: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.accept_issue(issue_id, project_id)
    issue_status = issue.status
    issue_name_val = _issue_display_name(issue)
    await session.commit()
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": issue_status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_name_val,
        "timestamp": iso_now(),
    })

    return {"id": issue_id, "status": issue_status}


@mcp.tool(description=_desc["tool.cancel_issue.description"])
@mcp_tool_wrapper
async def cancel_issue(session, project_id: str, issue_id: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.cancel_issue(issue_id, project_id)
    issue_status = issue.status
    issue_name_val = _issue_display_name(issue)
    await session.commit()
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": issue_status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_name_val,
        "timestamp": iso_now(),
    })
    return {"id": issue_id, "status": issue_status}


@mcp.tool(description=_desc["tool.force_finish_issue.description"])
@mcp_tool_wrapper
async def force_finish_issue(session, project_id: str, issue_id: str, recap: str | None = None) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.force_finish_issue(issue_id, project_id, recap=recap)
    issue_status = issue.status
    issue_name_val = _issue_display_name(issue)
    await session.commit()
    await event_service.emit({
        "type": "issue_status_changed",
        "new_status": issue_status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_name_val,
        "timestamp": iso_now(),
    })
    return {"id": issue_id, "status": issue_status}


@mcp.tool(description=_desc["tool.send_notification.description"])
async def send_notification(project_id: str, issue_id: str, title: str, message: str = "") -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except AppError as e:
            return {"error": e.message}
        issue_name = _issue_display_name(issue) or "Untitled issue"
        project = await ProjectService(session).get_by_id(project_id)
        project_name = project.name if project else ""
        await event_service.emit({
            "type": "notification",
            "title": title,
            "message": message,
            "project_id": project_id,
            "issue_id": issue_id,
            "issue_name": issue_name,
            "project_name": project_name,
            "timestamp": iso_now(),
        })
        return {"success": True}


# ── Task tools (atomic plan tasks) ──────────────────────────────────────────


@mcp.tool(description=_desc["tool.create_plan_tasks.description"])
async def create_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            created = await task_service.create_bulk(issue_id, tasks)
            issue = await IssueService(session).get_by_id(issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": issue_id,
                    "timestamp": iso_now(),
                })
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status, "order": t.order} for t in created]}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.replace_plan_tasks.description"])
async def replace_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            created = await task_service.replace_all(issue_id, tasks)
            issue = await IssueService(session).get_by_id(issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": issue_id,
                    "timestamp": iso_now(),
                })
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status, "order": t.order} for t in created]}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.update_task_status.description"])
async def update_task_status(task_id: str, status: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, status=status)
            # file-backed TaskService returns TaskRecord without issue_id — find it via IssueService
            issue_rec = None
            task_issue_id = ""
            for project in await ProjectService(session).list_all(archived=False):
                from app.storage import issue_store as _is
                found = _is.find_task(project.path, task_id)
                if found is not None:
                    issue_rec, _ = found
                    task_issue_id = issue_rec.id
                    break
            task_id_val = task.id
            task_name = task.name
            task_status = task.status
            issue = issue_rec
            all_done = (
                await task_service.all_completed(task_issue_id)
                if task.status == TaskStatus.COMPLETED.value
                else False
            )
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": task_issue_id,
                    "task_id": task_id_val,
                    "timestamp": iso_now(),
                })
            if all_done and issue:
                from app.hooks.registry import HookContext, HookEvent, hook_registry
                from app.services.project_service import ProjectService as _PS
                async with async_session() as s2:
                    project = await _PS(s2).get_by_id(issue.project_id)
                await hook_registry.fire(
                    HookEvent.ALL_TASKS_COMPLETED,
                    HookContext(
                        project_id=issue.project_id,
                        issue_id=task_issue_id,
                        event=HookEvent.ALL_TASKS_COMPLETED,
                        metadata={
                            "issue_name": issue.name or "",
                            "project_name": project.name if project else "",
                            "project_path": project.path if project else "",
                        },
                    ),
                )
            return {"id": task_id_val, "name": task_name, "status": task_status}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.update_task_name.description"])
async def update_task_name(task_id: str, name: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, name=name)
            issue = None
            task_issue_id = ""
            for project in await ProjectService(session).list_all(archived=False):
                from app.storage import issue_store as _is
                found = _is.find_task(project.path, task_id)
                if found is not None:
                    issue, _ = found
                    task_issue_id = issue.id
                    break
            task_id_val = task.id
            task_name = task.name
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": task_issue_id,
                    "task_id": task_id_val,
                    "timestamp": iso_now(),
                })
            return {"id": task_id_val, "name": task_name}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.delete_task.description"])
async def delete_task(task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            # Find owning issue before deletion
            issue = None
            task_issue_id = ""
            for project in await ProjectService(session).list_all(archived=False):
                from app.storage import issue_store as _is
                found = _is.find_task(project.path, task_id)
                if found is not None:
                    issue, _ = found
                    task_issue_id = issue.id
                    break
            await task_service.delete(task_id)
            project_id = issue.project_id if issue else None
            await session.commit()
            if project_id:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": project_id,
                    "issue_id": task_issue_id,
                    "timestamp": iso_now(),
                })
            return {"deleted": True}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.get_plan_tasks.description"])
async def get_plan_tasks(issue_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.list_by_issue(issue_id)
        return {"tasks": [{"id": t.id, "name": t.name, "status": t.status, "order": t.order} for t in tasks]}


@mcp.tool(description=_desc["tool.get_next_issue.description"])
async def get_next_issue(project_id: str) -> dict:
    async with async_session() as session:
        paused = await SettingsService(session).get("work_queue_paused")
        if paused == "true":
            return {"issue": None, "message": "Work queue is paused"}
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_next_issue(project_id)
            if issue is None:
                return {"issue": None, "message": "No workable issues in queue"}
            return {
                "issue": {
                    "id": issue.id,
                    "name": issue.name,
                    "description": issue.description,
                    "status": issue.status,
                    "priority": issue.priority,
                }
            }
        except AppError as e:
            return {"error": e.message}


from app.schemas.memory import MemoryResponse
from app.services.memory_service import MemoryService
from app.services import memory_events


def _memory_to_dict(m, counts) -> dict:
    r = MemoryResponse.from_model(m, **counts)
    return r.model_dump(mode="json")


@mcp.tool(description=_desc["tool.memory_create.description"])
async def memory_create(project_id: str, title: str, description: str = "", parent_id: str | None = None) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            m = await svc.create(project_id=project_id, title=title, description=description, parent_id=parent_id)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        counts = await svc.counts(m.id)
        await memory_events.emit_created(project_id=project_id, memory_id=m.id)
        return _memory_to_dict(m, counts)


@mcp.tool(description=_desc["tool.memory_update.description"])
async def memory_update(memory_id: str, title: str | None = None, description: str | None = None, parent_id: str | None = None, parent_id_clear: bool = False) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            if parent_id_clear:
                m = await svc.update(memory_id, title=title, description=description, parent_id=None)
            elif parent_id is not None:
                m = await svc.update(memory_id, title=title, description=description, parent_id=parent_id)
            else:
                m = await svc.update(memory_id, title=title, description=description)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        counts = await svc.counts(m.id)
        await memory_events.emit_updated(project_id=m.project_id, memory_id=m.id)
        return _memory_to_dict(m, counts)


@mcp.tool(description=_desc["tool.memory_delete.description"])
async def memory_delete(memory_id: str) -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            m = await svc.get(memory_id)
            project_id = m.project_id
            await svc.delete(memory_id)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        await memory_events.emit_deleted(project_id=project_id, memory_id=memory_id)
        return {"deleted": True}


@mcp.tool(description=_desc["tool.memory_link.description"])
async def memory_link(from_id: str, to_id: str, relation: str = "") -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            link = await svc.link(from_id, to_id, relation=relation)
            m = await svc.get(from_id)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        await memory_events.emit_linked(project_id=m.project_id, from_id=from_id, to_id=to_id, relation=link.relation)
        return {"from_id": link.from_id, "to_id": link.to_id, "relation": link.relation}


@mcp.tool(description=_desc["tool.memory_unlink.description"])
async def memory_unlink(from_id: str, to_id: str, relation: str = "") -> dict:
    async with async_session() as session:
        svc = MemoryService(session)
        try:
            m = await svc.get(from_id)
            deleted = await svc.unlink(from_id, to_id, relation=relation)
            await session.commit()
        except AppError as e:
            return {"error": e.message}
        if deleted:
            await memory_events.emit_unlinked(project_id=m.project_id, from_id=from_id, to_id=to_id, relation=relation)
        return {"deleted": bool(deleted)}


# ── Project file tools ──────────────────────────────────────────────────────


from app.services.file_service import FileService


def _file_to_dict(f, *, project_id: str = "") -> dict:
    meta = (getattr(f, "metadata", None) or getattr(f, "file_metadata", None) or {})
    return {
        "id": f.id,
        "project_id": getattr(f, "project_id", project_id),
        "original_name": f.original_name,
        "file_type": f.file_type,
        "file_size": f.file_size,
        "mime_type": f.mime_type,
        "extraction_status": f.extraction_status,
        "extraction_error": f.extraction_error,
        "low_text": bool(meta.get("low_text")),
        "created_at": f.created_at if isinstance(f.created_at, str) else (f.created_at.isoformat() if f.created_at else None),
    }


@mcp.tool(description=_desc["tool.list_project_files.description"])
async def list_project_files(project_id: str) -> dict:
    async with async_session() as session:
        svc = FileService(session)
        records = await svc.list_by_project(project_id)
        return {"files": [_file_to_dict(r, project_id=project_id) for r in records]}


@mcp.tool(description=_desc["tool.read_project_file.description"])
async def read_project_file(project_id: str, file_id: str, offset: int = 0, max_chars: int = 50000) -> dict:
    async with async_session() as session:
        svc = FileService(session)
        record = await svc.get_by_id(project_id, file_id)
        if record is None:
            return {"error": "File not found"}
        text_full = record.extracted_text or ""
        _ = project_id  # keep reference; file_store already loaded text cache
        total = len(text_full)
        offset = max(0, offset)
        max_chars = max(1, min(max_chars, 500_000))
        chunk = text_full[offset : offset + max_chars]
        return {
            "id": record.id,
            "name": record.original_name,
            "type": record.file_type,
            "status": record.extraction_status,
            "error": record.extraction_error,
            "offset": offset,
            "total_chars": total,
            "truncated": offset + max_chars < total,
            "content": chunk,
        }


# search_project_files removed — LLM greps .manager_ai/files/*.txt directly.


# ── Project Link tools ──────────────────────────────────────────────────────

from app.services.project_link_service import ProjectLinkService


@mcp.tool(description=_desc["tool.get_project_links.description"])
async def get_project_links(project_id: str) -> dict:
    async with async_session() as session:
        svc = ProjectLinkService(session)
        links = await svc.list_for_project(project_id)
        return {
            "links": [
                {
                    "id": link.id,
                    "source_project_id": link.source_project_id,
                    "source_project_name": link.source_project.name,
                    "target_project_id": link.target_project_id,
                    "target_project_name": link.target_project.name,
                    "description": link.description,
                    "created_at": link.created_at.isoformat() if link.created_at else None,
                    "updated_at": link.updated_at.isoformat() if link.updated_at else None,
                }
                for link in links
            ]
        }


# ── Playwright / Credential tools ──────────────────────────────────────────

from app.mcp.catalog import catalog_loader
from app.mcp.plugin_manager import plugin_manager
from app.mcp.plugin_config import load_plugins, get_plugin_config, PluginsFile


@mcp.tool(description=_desc["tool.get_project_url.description"])
async def get_project_url(project_id: str) -> dict:
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
            return {"url": project.url}
        except AppError as e:
            return {"error": e.message}


# ── Plugin tools ────────────────────────────────────────────────────────────


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
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "RUNNING"), None)
        if not active:
            return {"active": None}
        steps = active["steps"]
        idx = active["current_step_index"]
        if idx >= len(steps):
            return {"active": None}
        step = steps[idx]
        return {
            "run_id": active["id"],
            "step_run_id": step["id"],
            "agent_name": step["agent_name"],
            "agent_intent": step.get("agent_intent", ""),
            "step_index": idx,
            "step_status": step["status"],
            "terminal_id": step.get("terminal_id"),
        }


@mcp.tool(description=_desc["tool.get_active_pipeline_run.description"])
async def get_active_pipeline_run(issue_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "RUNNING"), None)
        if not active:
            return {"active": None}
        return active


@mcp.tool(description=_desc["tool.send_agent_message.description"])
async def send_agent_message(run_id: str, sender_agent_name: str, content: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        try:
            result = await svc.add_message(
                run_id=run_id,
                sender_agent_name=sender_agent_name,
                content=content,
            )
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.get_pipeline_messages.description"])
async def get_pipeline_messages(run_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        return {"messages": await svc.get_messages(run_id)}


@mcp.tool(description=_desc["tool.finished_pipeline_step.description"])
async def finished_pipeline_step(
    issue_id: str,
    summary: str,
    rejected: bool = False,
    rejection_reason: str | None = None,
    target_step_index: int | None = None,
) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "RUNNING"), None)
        if not active:
            issue_service = IssueService(session)
            issue = await issue_service.get_by_id(issue_id)
            if issue and issue.status == IssueStatus.ACCEPTED.value:
                logger.warning(
                    "No active pipeline run for issue %s (status ACCEPTED) — "
                    "step completed via accept_issue without finished_pipeline_step",
                    issue_id,
                )
                return {
                    "success": True,
                    "step_completed": True,
                    "pipeline_finished": True,
                    "warning": "No active pipeline run found; step implicitly completed",
                }
            return {"error": "No active pipeline run for this issue"}

        run_id = active["id"]
        idx = active["current_step_index"]
        steps = active["steps"]
        if idx >= len(steps):
            return {"error": "No active step"}

        step = steps[idx]
        agent_name = step["agent_name"]

        if rejected:
            if not rejection_reason:
                return {"error": "rejection_reason is required when rejected=True"}

            if target_step_index is None:
                resolved = await svc.resolve_rejection_target(run_id, step["pipeline_step_id"])
                if resolved is None:
                    return {
                        "error": "No rejection redirect configured for this step. "
                                 "Provide target_step_index or configure an event rule."
                    }
                target_step_index = resolved

            issue_service = IssueService(session)
            issue = await issue_service.get_by_id(issue_id)
            project_id = issue.project_id if issue else None
            if not project_id:
                return {"error": "Could not determine project_id for issue"}

            reject_result = await svc.reject_step(
                run_id=run_id,
                reason=rejection_reason,
                target_step_index=target_step_index,
                project_id=project_id,
            )

        await svc.add_message(
            run_id=run_id,
            sender_agent_name=agent_name,
            content=summary,
        )

        ok = set_step_completed(run_id, idx)
        pipeline_finished = False if rejected else idx >= len(steps) - 1

        await session.commit()

        result = {
            "success": ok,
            "step_completed": ok,
            "pipeline_finished": pipeline_finished,
        }
        if rejected:
            result["rejected"] = True
            result["rejection_count"] = reject_result.get("rejection_count", 0)
            result["max_reached"] = reject_result.get("max_reached", False)
        return result


# ── Orchestrated pipeline MCP tools (Hermes orchestrator) ─────────


@mcp.tool(description=_desc["tool.start_pipeline_step.description"])
async def start_pipeline_step(run_id: str, project_id: str) -> dict:
    """Avvia lo step corrente di una pipeline orchestrata."""
    async with async_session() as session:
        try:
            project = await ProjectService(session).get_by_id(project_id)
        except AppError as e:
            return {"error": e.message}
        svc = PipelineRunService(session, session_factory=async_session)
        try:
            result = await svc.start_step(
                run_id=run_id,
                project_id=project_id,
                project_path=project.path,
            )
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.advance_pipeline.description"])
async def advance_pipeline(run_id: str) -> dict:
    """Avanza la pipeline orchestrata al prossimo step."""
    async with async_session() as session:
        svc = PipelineRunService(session)
        try:
            result = await svc.advance_step(run_id)
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.pause_pipeline.description"])
async def pause_pipeline(run_id: str) -> dict:
    """Mette in pausa la pipeline orchestrata."""
    async with async_session() as session:
        svc = PipelineRunService(session)
        try:
            result = await svc.pause_run(run_id)
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.resume_pipeline.description"])
async def resume_pipeline(run_id: str) -> dict:
    """Riprende una pipeline in pausa (PAUSED)."""
    async with async_session() as session:
        svc = PipelineRunService(session)
        try:
            result = await svc.resume_run(run_id)
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}
