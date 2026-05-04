import asyncio
import logging
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from datetime import datetime, timezone

from app.database import async_session
from app.exceptions import AppError
from app.services.event_service import event_service
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.models.task import TaskStatus
from app.services.task_service import TaskService
from app.services.settings_service import SettingsService

_defaults_path = Path(__file__).parent / "default_settings.json"
_desc = json.loads(_defaults_path.read_text(encoding="utf-8"))

mcp = FastMCP(_desc["server.name"], streamable_http_path="/")

logger = logging.getLogger(__name__)


@mcp.tool(description=_desc["tool.get_issue_details.description"])
async def get_issue_details(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except AppError as e:
            return {"error": e.message}
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
async def get_issue_status(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except AppError as e:
            return {"error": e.message}
        return {"id": issue.id, "status": issue.status}


@mcp.tool(description=_desc["tool.get_project_context.description"])
async def get_project_context(project_id: str) -> dict:
    async with async_session() as session:
        project_service = ProjectService(session)
        try:
            project = await project_service.get_by_id(project_id)
            return {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "description": project.description,
                "tech_stack": project.tech_stack,
            }
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.update_project_context.description"])
async def update_project_context(project_id: str, description: str | None = None, tech_stack: str | None = None) -> dict:
    async with async_session() as session:
        project_service = ProjectService(session)
        try:
            project = await project_service.update(project_id, description=description, tech_stack=tech_stack)
            await session.commit()
            await event_service.emit({
                "type": "project_updated",
                "project_id": project_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {
                "id": project.id,
                "name": project.name,
                "path": project.path,
                "description": project.description,
                "tech_stack": project.tech_stack,
            }
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.set_issue_name.description"])
async def set_issue_name(project_id: str, issue_id: str, name: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.set_name(issue_id, project_id, name)
            await session.commit()
            await event_service.emit({
                "type": "issue_content_updated",
                "content_type": "name",
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "name": issue.name}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.complete_issue(issue_id, project_id, recap)
            # Extract data while session is open
            issue_data = {
                "name": issue.name or (issue.description or "")[:100],
                "specification": issue.specification,
                "plan": issue.plan,
                "recap": issue.recap,
            }
            issue_id_val = issue.id
            issue_name = issue.name or (issue.description or "")[:50] or ""
            issue_status = issue.status
            try:
                project = await ProjectService(session).get_by_id(project_id)
                project_name = project.name
            except AppError:
                project_name = ""
            await session.commit()

            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue_status,
                "project_id": project_id,
                "issue_id": issue_id_val,
                "issue_name": issue_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {"id": issue_id_val, "status": issue_status, "recap": issue.recap}
        except AppError as e:
            return {"error": e.message}


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
async def create_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create_spec(issue_id, project_id, spec)
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status, "specification": issue.specification}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.edit_issue_spec.description"])
async def edit_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.edit_spec(issue_id, project_id, spec)
            await session.commit()
            await event_service.emit({
                "type": "issue_content_updated",
                "content_type": "spec",
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status, "specification": issue.specification}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.create_issue_plan.description"])
async def create_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create_plan(issue_id, project_id, plan)
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status, "plan": issue.plan}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.edit_issue_plan.description"])
async def edit_issue_plan(project_id: str, issue_id: str, plan: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.edit_plan(issue_id, project_id, plan)
            await session.commit()
            await event_service.emit({
                "type": "issue_content_updated",
                "content_type": "plan",
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status, "plan": issue.plan}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.accept_issue.description"])
async def accept_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.accept_issue(issue_id, project_id)
            issue_status = issue.status
            issue_name_val = issue.name or (issue.description or "")[:50] or ""
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue_status,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue_name_val,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue_id, "status": issue_status}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.cancel_issue.description"])
async def cancel_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.cancel_issue(issue_id, project_id)
            issue_status = issue.status
            issue_name_val = issue.name or (issue.description or "")[:50] or ""
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue_status,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue_name_val,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue_id, "status": issue_status}
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.send_notification.description"])
async def send_notification(project_id: str, issue_id: str, title: str, message: str = "") -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except AppError as e:
            return {"error": e.message}
        issue_name = issue.name or (issue.description or "")[:50] or "Untitled issue"
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
            for project in await ProjectService(session).list_all(archived=None):
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
            for project in await ProjectService(session).list_all(archived=None):
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
            for project in await ProjectService(session).list_all(archived=None):
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
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
