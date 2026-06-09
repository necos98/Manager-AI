"""Shared MCP tool implementations — plain async functions, no decorators.

Each function takes ``session`` (an AsyncSession from app.database) as its
first parameter and returns a JSON-serialisable dict.

Worker and orchestrator MCP servers each import the subset they need and wrap
with their own @mcp.tool() decorator + HTTP path adapter.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.exceptions import AppError
from app.models.issue import IssueStatus
from app.models.task import TaskStatus
from app.services.agent_service import AgentService
from app.services.event_service import event_service
from app.services.issue_service import IssueService
from app.services.pipeline_run import PipelineRunService, set_step_completed
from app.services.pipeline_service import PipelineService
from app.services.project_service import ProjectService
from app.services.settings_service import SettingsService
from app.services.task_service import TaskService
from app.services.file_service import FileService
from app.services.memory_service import MemoryService
from app.services import memory_events
from app.services.activity_service import ActivityService
from app.services.project_link_service import ProjectLinkService
from app.services.question_service import QuestionService, question_store
from app.mcp.catalog import catalog_loader
from app.mcp.plugin_manager import plugin_manager
from app.mcp.plugin_config import load_plugins, get_plugin_config, PluginsFile
from app.schemas.memory import MemoryResponse
from app.schemas.setting import SettingOut
from app.storage import issue_store as _issue_store
from app.storage import memory_store as _memory_store
from app.storage import file_store as _file_store
from app.storage.cache import clear_all_caches
from app.storage.project_loader import _load_project_into_memory
from app.storage.memory_store_core import memory_store as _global_store
from app.utils.datetime import iso_now, now
from app.models.issue import Issue
from app.models.task import TaskStatus as TaskStatusEnum

logger = logging.getLogger(__name__)

_DEFAULTS_PATH = Path(__file__).parent / "default_settings.json"
_DESC: dict[str, str] = json.loads(_DEFAULTS_PATH.read_text(encoding="utf-8"))


# ── Helpers ──────────────────────────────────────────────────────────────────


def issue_display_name(issue, max_len: int = 50) -> str:
    return issue.name or (issue.description or "")[:max_len] or ""


def serialize_agent(agent) -> dict:
    return {
        "id": agent.id,
        "name": agent.name,
        "intent": agent.intent,
        "model": agent.model,
        "allowed_tools": agent.allowed_tools,
        "created_at": str(agent.created_at) if agent.created_at else None,
        "updated_at": str(agent.updated_at) if agent.updated_at else None,
    }


def serialize_pipeline(pipeline) -> dict:
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


def _memory_to_dict(m, counts) -> dict:
    r = MemoryResponse.from_model(m, **counts)
    return r.model_dump(mode="json")


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


async def _emit_event(event: dict[str, Any]) -> None:
    """Fire a real-time event through the WebSocket bus."""
    await event_service.emit(event)


def _not_found(msg: str = "Not found") -> dict:
    return {"error": msg}


# ── Issue Tools ──────────────────────────────────────────────────────────────


async def get_issue_details(session: AsyncSession, project_id: str, issue_id: str) -> dict:
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


async def get_issue_status(session: AsyncSession, project_id: str, issue_id: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.get_for_project(issue_id, project_id)
    return {"id": issue.id, "status": issue.status}


async def list_issues(
    session: AsyncSession,
    project_id: str,
    status: str | None = None,
    search: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict:
    """List issues for a project with optional filters."""
    issue_service = IssueService(session)
    status_enum = IssueStatus(status) if status else None
    records = await issue_service.list_by_project(
        project_id,
        status=status_enum,
        search=search,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    return {
        "issues": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "name": r.name,
                "description": r.description,
                "status": r.status,
                "priority": r.priority,
                "category": getattr(r, "category", None),
                "created_at": r.created_at or None,
                "updated_at": r.updated_at or None,
            }
            for r in records
        ],
        "total": len(records),
    }


async def get_issue_statuses() -> dict:
    """Return the valid issue statuses and their lifecycle."""
    return {
        "statuses": [s.value for s in IssueStatus],
        "lifecycle": "New → Reasoning → Planned → Accepted → Finished",
        "cancelable_from_any": True,
        "force_finish_from_any": True,
        "transitions": {
            "New": ["Reasoning"],
            "Reasoning": ["Planned"],
            "Planned": ["Accepted"],
            "Accepted": ["Finished"],
            "Finished": [],
            "Canceled": [],
        },
    }


async def create_issue(session: AsyncSession, project_id: str, description: str, priority: int = 3) -> dict:
    if not description or not description.strip():
        return {"error": "Description cannot be blank"}
    if priority < 1 or priority > 5:
        return {"error": "Priority must be between 1 and 5"}
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


async def set_issue_name(session: AsyncSession, project_id: str, issue_id: str, name: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.set_name(issue_id, project_id, name)
    await session.commit()
    await _emit_event({
        "type": "issue_content_updated",
        "content_type": "name",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue.name or "",
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "name": issue.name}


async def create_issue_spec(session: AsyncSession, project_id: str, issue_id: str, spec: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.create_spec(issue_id, project_id, spec)
    await session.commit()
    await _emit_event({
        "type": "issue_status_changed",
        "new_status": issue.status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "specification": issue.specification}


async def edit_issue_spec(session: AsyncSession, project_id: str, issue_id: str, spec: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.edit_spec(issue_id, project_id, spec)
    await session.commit()
    await _emit_event({
        "type": "issue_content_updated",
        "content_type": "spec",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "specification": issue.specification}


async def create_issue_plan(session: AsyncSession, project_id: str, issue_id: str, plan: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.create_plan(issue_id, project_id, plan)
    await session.commit()
    await _emit_event({
        "type": "issue_status_changed",
        "new_status": issue.status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "plan": issue.plan}


async def edit_issue_plan(session: AsyncSession, project_id: str, issue_id: str, plan: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.edit_plan(issue_id, project_id, plan)
    await session.commit()
    await _emit_event({
        "type": "issue_content_updated",
        "content_type": "plan",
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_display_name(issue),
        "timestamp": iso_now(),
    })
    return {"id": issue.id, "status": issue.status, "plan": issue.plan}


async def accept_issue(session: AsyncSession, project_id: str, issue_id: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.accept_issue(issue_id, project_id)
    issue_status = issue.status
    issue_name_val = issue_display_name(issue)
    await session.commit()
    await _emit_event({
        "type": "issue_status_changed",
        "new_status": issue_status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_name_val,
        "timestamp": iso_now(),
    })
    return {"id": issue_id, "status": issue_status}


async def cancel_issue(session: AsyncSession, project_id: str, issue_id: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.cancel_issue(issue_id, project_id)
    issue_status = issue.status
    issue_name_val = issue_display_name(issue)
    await session.commit()
    await _emit_event({
        "type": "issue_status_changed",
        "new_status": issue_status,
        "project_id": project_id,
        "issue_id": issue_id,
        "issue_name": issue_name_val,
        "timestamp": iso_now(),
    })
    return {"id": issue_id, "status": issue_status}


async def force_finish_issue(session: AsyncSession, project_id: str, issue_id: str, recap: str | None = None) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.force_finish_issue(issue_id, project_id, recap=recap)
    await session.commit()
    project = await ProjectService(session).get_by_id(project_id)
    project_name = project.name if project else ""
    await _emit_event({
        "type": "issue_status_changed",
        "new_status": issue.status,
        "project_id": project_id,
        "project_name": project_name,
        "issue_id": issue_id,
        "issue_name": issue_display_name(issue),
        "description": issue.description,
        "recap": issue.recap,
        "timestamp": iso_now(),
    })
    return {"id": issue_id, "status": issue.status}


async def complete_issue(session: AsyncSession, project_id: str, issue_id: str, recap: str) -> dict:
    issue_service = IssueService(session)
    issue = await issue_service.complete_issue(issue_id, project_id, recap)
    issue_data = {
        "name": issue_display_name(issue, max_len=100),
        "specification": issue.specification,
        "plan": issue.plan,
        "recap": issue.recap,
    }
    issue_id_val = issue.id
    issue_name = issue_display_name(issue)
    issue_status = issue.status
    await session.commit()
    project = await ProjectService(session).get_by_id(project_id)
    project_name = project.name if project else ""
    await _emit_event({
        "type": "issue_status_changed",
        "new_status": issue_status,
        "project_id": project_id,
        "project_name": project_name,
        "issue_id": issue_id_val,
        "issue_name": issue_name,
        "description": issue.description,
        "recap": issue.recap,
        "timestamp": iso_now(),
    })
    return {"id": issue_id_val, "status": issue_status, "recap": issue.recap}


async def get_next_issue(session: AsyncSession, project_id: str) -> dict:
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


# ── Task Tools ───────────────────────────────────────────────────────────────


async def create_plan_tasks(session: AsyncSession, issue_id: str, tasks: list[dict]) -> dict:
    task_service = TaskService(session)
    try:
        created = await task_service.create_bulk(issue_id, tasks)
        issue = await IssueService(session).get_by_id(issue_id)
        await session.commit()
        if issue:
            await _emit_event({
                "type": "task_updated",
                "project_id": issue.project_id,
                "issue_id": issue_id,
                "timestamp": iso_now(),
            })
        return {"tasks": [{"id": t.id, "name": t.name, "status": t.status, "order": t.order} for t in created]}
    except AppError as e:
        return {"error": e.message}


async def replace_plan_tasks(session: AsyncSession, issue_id: str, tasks: list[dict]) -> dict:
    task_service = TaskService(session)
    try:
        created = await task_service.replace_all(issue_id, tasks)
        issue = await IssueService(session).get_by_id(issue_id)
        await session.commit()
        if issue:
            await _emit_event({
                "type": "task_updated",
                "project_id": issue.project_id,
                "issue_id": issue_id,
                "timestamp": iso_now(),
            })
        return {"tasks": [{"id": t.id, "name": t.name, "status": t.status, "order": t.order} for t in created]}
    except AppError as e:
        return {"error": e.message}


async def update_task_status(session: AsyncSession, task_id: str, status: str) -> dict:
    task_service = TaskService(session)
    try:
        task = await task_service.update(task_id, status=status)
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
            await _emit_event({
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


async def update_task_name(session: AsyncSession, task_id: str, name: str) -> dict:
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
            await _emit_event({
                "type": "task_updated",
                "project_id": issue.project_id,
                "issue_id": task_issue_id,
                "task_id": task_id_val,
                "timestamp": iso_now(),
            })
        return {"id": task_id_val, "name": task_name}
    except AppError as e:
        return {"error": e.message}


async def delete_task(session: AsyncSession, task_id: str) -> dict:
    task_service = TaskService(session)
    try:
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
            await _emit_event({
                "type": "task_updated",
                "project_id": project_id,
                "issue_id": task_issue_id,
                "timestamp": iso_now(),
            })
        return {"deleted": True}
    except AppError as e:
        return {"error": e.message}


async def get_plan_tasks(session: AsyncSession, issue_id: str) -> dict:
    task_service = TaskService(session)
    tasks = await task_service.list_by_issue(issue_id)
    return {"tasks": [{"id": t.id, "name": t.name, "status": t.status, "order": t.order} for t in tasks]}


# ── Project Context Tools ────────────────────────────────────────────────────


async def get_project_context(session: AsyncSession, project_id: str) -> dict:
    project_service = ProjectService(session)
    project = await project_service.get_by_id(project_id)
    return {
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "tech_stack": project.tech_stack,
    }


async def update_project_context(session: AsyncSession, project_id: str, description: str | None = None, tech_stack: str | None = None) -> dict:
    project_service = ProjectService(session)
    project = await project_service.update(project_id, description=description, tech_stack=tech_stack)
    await session.commit()
    await _emit_event({
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


async def get_project_links(session: AsyncSession, project_id: str) -> dict:
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


async def get_project_url(session: AsyncSession, project_id: str) -> dict:
    try:
        project = await ProjectService(session).get_by_id(project_id)
        return {"url": project.url}
    except AppError as e:
        return {"error": e.message}


# ── Memory Tools ─────────────────────────────────────────────────────────────


async def memory_create(session: AsyncSession, project_id: str, title: str, description: str = "", parent_id: str | None = None) -> dict:
    svc = MemoryService(session)
    try:
        m = await svc.create(project_id=project_id, title=title, description=description, parent_id=parent_id)
        await session.commit()
    except AppError as e:
        return {"error": e.message}
    counts = await svc.counts(m.id)
    await memory_events.emit_created(project_id=project_id, memory_id=m.id)
    return _memory_to_dict(m, counts)


async def memory_update(session: AsyncSession, memory_id: str, title: str | None = None, description: str | None = None, parent_id: str | None = None, parent_id_clear: bool = False) -> dict:
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


async def memory_delete(session: AsyncSession, memory_id: str) -> dict:
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


async def memory_link(session: AsyncSession, from_id: str, to_id: str, relation: str = "") -> dict:
    svc = MemoryService(session)
    try:
        link = await svc.link(from_id, to_id, relation=relation)
        m = await svc.get(from_id)
        await session.commit()
    except AppError as e:
        return {"error": e.message}
    await memory_events.emit_linked(project_id=m.project_id, from_id=from_id, to_id=to_id, relation=link.relation)
    return {"from_id": link.from_id, "to_id": link.to_id, "relation": link.relation}


async def memory_unlink(session: AsyncSession, from_id: str, to_id: str, relation: str = "") -> dict:
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


async def memory_search(session: AsyncSession, project_id: str, query: str, limit: int = 20) -> dict:
    """Search across a project's memory titles and descriptions."""
    svc = MemoryService(session)
    try:
        results = await svc.search(project_id=project_id, query=query, limit=limit)
        return {
            "results": [
                {
                    "id": r["memory"].id,
                    "title": r["memory"].title,
                    "snippet": r["snippet"],
                    "rank": r["rank"],
                    "created_at": r["memory"].created_at,
                }
                for r in results
            ],
            "count": len(results),
        }
    except AppError as e:
        return {"error": e.message}


# ── Project File Tools ───────────────────────────────────────────────────────


async def list_project_files(session: AsyncSession, project_id: str) -> dict:
    svc = FileService(session)
    records = await svc.list_by_project(project_id)
    return {"files": [_file_to_dict(r, project_id=project_id) for r in records]}


async def read_project_file(session: AsyncSession, project_id: str, file_id: str, offset: int = 0, max_chars: int = 50000) -> dict:
    svc = FileService(session)
    record = await svc.get_by_id(project_id, file_id)
    if record is None:
        return {"error": "File not found"}
    text_full = record.extracted_text or ""
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


# ── Notification Tool ────────────────────────────────────────────────────────


async def send_notification(session: AsyncSession, project_id: str, issue_id: str, title: str, message: str = "") -> dict:
    issue_service = IssueService(session)
    try:
        issue = await issue_service.get_for_project(issue_id, project_id)
    except AppError as e:
        return {"error": e.message}
    issue_name = issue_display_name(issue) or "Untitled issue"
    project = await ProjectService(session).get_by_id(project_id)
    project_name = project.name if project else ""
    await _emit_event({
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


# ── Plugin Tools ─────────────────────────────────────────────────────────────


async def list_plugins(session: AsyncSession, project_id: str) -> dict:
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


async def get_plugin_config_tool(session: AsyncSession, project_id: str, plugin_name: str) -> dict:
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


async def enable_plugin_tool(session: AsyncSession, project_id: str, plugin_name: str) -> dict:
    try:
        project = await ProjectService(session).get_by_id(project_id)
    except AppError as e:
        return {"error": e.message}
    cat = catalog_loader.get(plugin_name)
    if cat is None:
        return {"error": f"Plugin '{plugin_name}' not found in catalog. Available: {list(catalog_loader.plugins.keys())}"}
    success = await plugin_manager.enable_plugin(
        project_id, project.path, plugin_name, None  # mcp server passed by caller
    )
    return {"success": success}


async def disable_plugin_tool(session: AsyncSession, project_id: str, plugin_name: str) -> dict:
    try:
        project = await ProjectService(session).get_by_id(project_id)
    except AppError as e:
        return {"error": e.message}
    success = await plugin_manager.disable_plugin(
        project_id, project.path, plugin_name, None
    )
    return {"success": success}


# ── Question Tool ────────────────────────────────────────────────────────────


async def ask_user_question(session: AsyncSession, issue_id: str, question: str, options: list[str] | None = None, timeout_seconds: int = 300) -> dict:
    if not question.strip():
        return {"error": "Question text cannot be empty"}
    if timeout_seconds < 5 or timeout_seconds > 3600:
        return {"error": "Timeout must be between 5 and 3600 seconds"}

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

    issue_name = issue_display_name(issue) or "Untitled issue"
    project = await ProjectService(session).get_by_id(project_id)
    project_name = project.name if project else ""

    await _emit_event({
        "type": "question_asked",
        "question_id": q.id,
        "project_id": project_id,
        "project_name": project_name,
        "issue_id": issue_id,
        "issue_name": issue_name,
        "question": q.question,
        "options": q.options,
        "timestamp": iso_now(),
    })
    await _emit_event({
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
        async with async_session() as s2:
            await QuestionService(s2).timeout(q.id)
        await _emit_event({
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


# ── Agent Tools ──────────────────────────────────────────────────────────────


async def create_agent(session: AsyncSession, name: str, intent: str = "", model: str | None = None, allowed_tools: list[str] | None = None) -> dict:
    svc = AgentService(session)
    agent = await svc.create(
        name=name,
        model=model,
        allowed_tools=allowed_tools,
        intent=intent,
    )
    await session.commit()
    return serialize_agent(agent)


async def list_agents(session: AsyncSession) -> dict:
    svc = AgentService(session)
    agents = await svc.list_all()
    return {"agents": [serialize_agent(a) for a in agents]}


async def get_agent(session: AsyncSession, agent_id: str) -> dict:
    svc = AgentService(session)
    agent = await svc.get_by_id(agent_id)
    return serialize_agent(agent)


async def update_agent(session: AsyncSession, agent_id: str, name: str | None = None, intent: str | None = None, model: str | None = None, allowed_tools: list[str] | None = None) -> dict:
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
    agent = await svc.update(agent_id, **kwargs)
    await session.commit()
    return serialize_agent(agent)


async def delete_agent(session: AsyncSession, agent_id: str) -> dict:
    svc = AgentService(session)
    await svc.delete(agent_id)
    await session.commit()
    return {"deleted": True}


# ── Pipeline Tools ───────────────────────────────────────────────────────────


async def create_pipeline(session: AsyncSession, name: str, steps: list[dict]) -> dict:
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
    return serialize_pipeline(pipeline)


async def list_pipelines_tool(session: AsyncSession) -> dict:
    svc = PipelineService(session)
    pipelines = await svc.list_all()
    return {"pipelines": [serialize_pipeline(p) for p in pipelines]}


async def get_pipeline_tool(session: AsyncSession, pipeline_id: str) -> dict:
    svc = PipelineService(session)
    pipeline = await svc.get_pipeline(pipeline_id)
    return serialize_pipeline(pipeline)


async def update_pipeline_tool(session: AsyncSession, pipeline_id: str, name: str) -> dict:
    svc = PipelineService(session)
    await svc.update_pipeline(pipeline_id, name)
    await session.commit()
    pipeline = await svc.get_pipeline(pipeline_id)
    return serialize_pipeline(pipeline)


async def delete_pipeline_tool(session: AsyncSession, pipeline_id: str) -> dict:
    svc = PipelineService(session)
    await svc.delete_pipeline(pipeline_id)
    await session.commit()
    return {"deleted": True}


async def add_step(session: AsyncSession, pipeline_id: str, agent_id: str, order_index: int = 0) -> dict:
    svc = PipelineService(session)
    await svc.add_step(pipeline_id, agent_id, order_index)
    await session.commit()
    pipeline = await svc.get_pipeline(pipeline_id)
    return serialize_pipeline(pipeline)


async def remove_step(session: AsyncSession, step_id: str) -> dict:
    svc = PipelineService(session)
    try:
        await svc.remove_step(step_id)
        await session.commit()
        return {"deleted": True}
    except AppError as e:
        return {"error": e.message}


async def reorder_steps(session: AsyncSession, pipeline_id: str, step_ids: list[str]) -> dict:
    svc = PipelineService(session)
    await svc.reorder_steps(pipeline_id, step_ids)
    await session.commit()
    pipeline = await svc.get_pipeline(pipeline_id)
    return serialize_pipeline(pipeline)


# ── Pipeline Event Rule Tools ────────────────────────────────────────────────


async def add_pipeline_event_rule(
    session: AsyncSession,
    pipeline_id: str,
    event_type: str,
    source_step_id: str,
    target_step_id: str,
    action_type: str = "redirect",
    action_params: dict | None = None,
) -> dict:
    svc = PipelineService(session)
    try:
        rule = await svc.add_event_rule(
            pipeline_id=pipeline_id,
            event_type=event_type,
            source_step_id=source_step_id,
            target_step_id=target_step_id,
            action_type=action_type,
            action_params=action_params,
        )
        await session.commit()
        return {
            "id": rule.id,
            "pipeline_id": rule.pipeline_id,
            "event_type": rule.event_type,
            "source_step_id": rule.source_step_id,
            "target_step_id": rule.target_step_id,
            "action_type": rule.action_type,
            "action_params": rule.action_params,
            "enabled": rule.enabled,
        }
    except AppError as e:
        return {"error": e.message}


async def remove_pipeline_event_rule(session: AsyncSession, rule_id: str) -> dict:
    svc = PipelineService(session)
    try:
        await svc.remove_event_rule(rule_id)
        await session.commit()
        return {"deleted": True}
    except AppError as e:
        return {"error": e.message}


async def list_pipeline_event_rules_tool(session: AsyncSession, pipeline_id: str) -> dict:
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
                "action_type": r.action_type,
                "action_params": r.action_params,
                "enabled": r.enabled,
            }
            for r in rules
        ]
    }


async def update_pipeline_event_rule_tool(
    session: AsyncSession,
    rule_id: str,
    event_type: str | None = None,
    source_step_id: str | None = None,
    target_step_id: str | None = None,
    action_type: str | None = None,
    action_params: dict | None = None,
    enabled: bool | None = None,
) -> dict:
    svc = PipelineService(session)
    kwargs = {}
    if event_type is not None:
        kwargs["event_type"] = event_type
    if source_step_id is not None:
        kwargs["source_step_id"] = source_step_id
    if target_step_id is not None:
        kwargs["target_step_id"] = target_step_id
    if action_type is not None:
        kwargs["action_type"] = action_type
    if action_params is not None:
        kwargs["action_params"] = action_params
    if enabled is not None:
        kwargs["enabled"] = enabled
    try:
        rule = await svc.update_event_rule(rule_id, **kwargs)
        await session.commit()
        return {
            "id": rule.id,
            "pipeline_id": rule.pipeline_id,
            "event_type": rule.event_type,
            "source_step_id": rule.source_step_id,
            "target_step_id": rule.target_step_id,
            "action_type": rule.action_type,
            "action_params": rule.action_params,
            "enabled": rule.enabled,
        }
    except AppError as e:
        return {"error": e.message}


# ── Pipeline Run Tools ────────────────────────────────────────────────────────


async def run_pipeline(session: AsyncSession, project_id: str, pipeline_id: str, issue_id: str) -> dict:
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
        )
        await session.commit()
        return result
    except AppError as e:
        return {"error": e.message}


async def get_pipeline_run_status(session: AsyncSession, run_id: str) -> dict:
    svc = PipelineRunService(session)
    try:
        return await svc.get_run(run_id)
    except AppError as e:
        return {"error": e.message}


async def get_active_agent(session: AsyncSession, issue_id: str) -> dict:
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


async def get_active_pipeline_run(session: AsyncSession, issue_id: str) -> dict:
    svc = PipelineRunService(session)
    runs = await svc.get_runs_for_issue(issue_id)
    active = next((r for r in runs if r["status"] == "RUNNING"), None)
    if not active:
        return {"active": None}
    return active


async def send_agent_message(session: AsyncSession, run_id: str, sender_agent_name: str, content: str) -> dict:
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


async def get_pipeline_messages(session: AsyncSession, run_id: str) -> dict:
    svc = PipelineRunService(session)
    return {"messages": await svc.get_messages(run_id)}


async def finished_pipeline_step(session: AsyncSession, issue_id: str, summary: str, rejected: bool = False, rejection_reason: str | None = None, target_step_index: int | None = None) -> dict:
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

    await svc.add_message(run_id=run_id, sender_agent_name=agent_name, content=summary)

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


async def pause_pipeline(session: AsyncSession, run_id: str) -> dict:
    svc = PipelineRunService(session)
    try:
        result = await svc.pause_run(run_id)
        await session.commit()
        return result
    except AppError as e:
        return {"error": e.message}


async def resume_pipeline(session: AsyncSession, run_id: str) -> dict:
    svc = PipelineRunService(session)
    try:
        result = await svc.resume_run(run_id)
        await session.commit()
        return result
    except AppError as e:
        return {"error": e.message}


async def cancel_pipeline(session: AsyncSession, run_id: str) -> dict:
    svc = PipelineRunService(session)
    try:
        await svc.cancel_run(run_id)
        await session.commit()
        return {"success": True}
    except AppError as e:
        return {"error": e.message}


# ── 🆕 System Admin Tools ──────────────────────────────────────────────────


async def list_projects(session: AsyncSession, archived: bool = False) -> dict:
    svc = ProjectService(session)
    projects = await svc.list_all(archived=archived)
    result = []
    for p in projects:
        counts = await svc.get_issue_counts(p.id)
        result.append({
            "id": p.id,
            "name": p.name,
            "path": p.path,
            "description": p.description,
            "tech_stack": p.tech_stack,
            "shell": p.shell,
            "url": p.url,
            "archived_at": str(p.archived_at) if p.archived_at else None,
            "favorited_at": str(p.favorited_at) if p.favorited_at else None,
            "issue_counts": counts,
        })
    return {"projects": result}


async def get_project(session: AsyncSession, project_id: str) -> dict:
    svc = ProjectService(session)
    project = await svc.get_by_id(project_id)
    counts = await svc.get_issue_counts(project.id)
    return {
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "tech_stack": project.tech_stack,
        "shell": project.shell,
        "url": project.url,
        "created_at": str(project.created_at) if project.created_at else None,
        "archived_at": str(project.archived_at) if project.archived_at else None,
        "favorited_at": str(project.favorited_at) if project.favorited_at else None,
        "issue_counts": counts,
    }


async def create_project_tool(session: AsyncSession, name: str, path: str, description: str = "", tech_stack: str = "") -> dict:
    svc = ProjectService(session)
    try:
        project = await svc.create(
            name=name, path=path, description=description, tech_stack=tech_stack,
        )
        await session.commit()
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "description": project.description,
            "tech_stack": project.tech_stack,
        }
    except Exception as e:
        return {"error": str(e)}


async def update_project_tool(session: AsyncSession, project_id: str, name: str | None = None, path: str | None = None, description: str | None = None, tech_stack: str | None = None, url: str | None = None) -> dict:
    svc = ProjectService(session)
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if path is not None:
        kwargs["path"] = path
    if description is not None:
        kwargs["description"] = description
    if tech_stack is not None:
        kwargs["tech_stack"] = tech_stack
    if url is not None:
        kwargs["url"] = url
    project = await svc.update(project_id, **kwargs)
    await session.commit()
    return {
        "id": project.id,
        "name": project.name,
        "path": project.path,
        "description": project.description,
        "tech_stack": project.tech_stack,
    }


async def archive_project_tool(session: AsyncSession, project_id: str) -> dict:
    from app.mcp.plugin_manager import plugin_manager as _pm
    svc = ProjectService(session)
    project = await svc.archive(project_id)
    await session.commit()
    await _pm.stop_plugins_for_project(project_id)
    _global_store.remove_project(project.path)
    return {"id": project.id, "archived_at": str(project.archived_at) if project.archived_at else None}


async def unarchive_project_tool(session: AsyncSession, project_id: str) -> dict:
    from app.mcp.plugin_manager import plugin_manager as _pm
    svc = ProjectService(session)
    project = await svc.unarchive(project_id)
    await session.commit()
    _load_project_into_memory(project.path, _global_store)
    await _pm.start_plugins_for_project(project.id, project.path, None)
    return {"id": project.id, "archived_at": None}


async def delete_project_tool(session: AsyncSession, project_id: str) -> dict:
    from app.services.terminal_service import terminal_service
    from app.services.terminal_session import _sessions, _stop_reader
    svc = ProjectService(session)
    await svc.get_by_id(project_id)  # validate exists
    for term in terminal_service.list_active(project_id=project_id):
        try:
            _stop_reader(term["id"])
            _sessions.pop(term["id"], None)
            terminal_service.kill(term["id"])
        except KeyError:
            pass
    await svc.delete(project_id)
    await session.commit()
    return {"deleted": True}


# ── 🆕 Settings Admin Tools ────────────────────────────────────────────────


async def list_settings(session: AsyncSession) -> dict:
    svc = SettingsService(session)
    settings = await svc.get_all()
    return {"settings": [s.model_dump(mode="json") for s in settings]}


async def get_setting(session: AsyncSession, key: str) -> dict:
    svc = SettingsService(session)
    try:
        setting = await svc.get_one(key)
        return setting.model_dump(mode="json")
    except KeyError:
        return {"error": f"Unknown setting key: {key}"}


async def update_setting(session: AsyncSession, key: str, value: str) -> dict:
    svc = SettingsService(session)
    try:
        await svc.set(key, value)
        await session.commit()
        setting = await svc.get_one(key)
        return setting.model_dump(mode="json")
    except KeyError:
        return {"error": f"Unknown setting key: {key}"}


async def reset_setting(session: AsyncSession, key: str) -> dict:
    svc = SettingsService(session)
    try:
        await svc.reset(key)
        await session.commit()
        setting = await svc.get_one(key)
        return setting.model_dump(mode="json")
    except KeyError:
        return {"error": f"Unknown setting key: {key}"}


# ── 🆕 Dashboard & Activity Tools ───────────────────────────────────────────


async def get_dashboard(session: AsyncSession) -> dict:
    svc = ProjectService(session)
    data = await svc.get_dashboard_data()
    return {"projects": data}


async def get_project_activity(session: AsyncSession, project_id: str, issue_id: str | None = None, limit: int = 100, offset: int = 0) -> dict:
    svc = ActivityService(session)
    entries = await svc.list_for_project(project_id, issue_id=issue_id, limit=limit, offset=offset)
    return {
        "activities": [
            {
                "id": e.id,
                "issue_id": e.issue_id,
                "action": e.action,
                "details": e.details,
                "created_at": str(e.created_at) if e.created_at else None,
            }
            for e in entries
        ]
    }


# ── 🆕 Pipeline Runs History Tool ────────────────────────────────────────────


async def get_pipeline_runs_for_issue(session: AsyncSession, issue_id: str) -> dict:
    svc = PipelineRunService(session)
    runs = await svc.get_runs_for_issue(issue_id)
    return {"runs": runs}


# ── 🆕 Run Issue Tool ─────────────────────────────────────────────────────────


async def run_issue(session: AsyncSession, project_id: str, issue_id: str, provider_name: str | None = None) -> dict:
    """Spawn an agent terminal for a single issue and let it work autonomously.

    Creates a PTY terminal, writes the agent provider's run-issue commands,
    and returns immediately with the terminal ID. The agent inside the terminal
    works through the issue lifecycle (spec → plan → tasks → implementation →
    completion) independently.

    This is simpler than ``run_pipeline`` — no pipeline/step/agent records,
    no multi-step orchestration. Just fire the agent at the issue.
    """
    from app.services.run_issue_service import run_issue as _run_service

    return await _run_service(
        issue_id=issue_id,
        project_id=project_id,
        provider_name=provider_name,
        session=session,
    )


# ── 🆕 Delete Issue Tool ─────────────────────────────────────────────────────


async def delete_issue(session: AsyncSession, project_id: str, issue_id: str) -> dict:
    """Delete an issue permanently. Requires both project_id and issue_id."""
    from app.services.issue_service import IssueService
    svc = IssueService(session)
    try:
        await svc.delete(issue_id, project_id)
        await session.commit()
        return {"success": True, "issue_id": issue_id}
    except AppError as e:
        return {"error": e.message}
