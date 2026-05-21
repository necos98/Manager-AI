import asyncio
import logging
import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session
from app.exceptions import AppError
from app.models.agent import Agent
from app.models.agent_message import AgentMessage
from app.models.pipeline import AgentStepRun, AgentStepStatus, Pipeline, PipelineRun, PipelineRunStatus
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.schemas.agent_message import AgentMessageCreate, AgentMessageResponse
from app.schemas.pipeline import PipelineCreate, PipelineUpdate, PipelineResponse, PipelineRunFullResponse, PipelineRunResponse, AgentStepRunResponse
from app.services.event_service import event_service
from app.services.issue_service import IssueService
from app.services.orchestrator_service import OrchestratorService
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

            # Auto-start default pipeline
            try:
                orchestrator = OrchestratorService(session)
                pipeline_run = await orchestrator.start_pipeline(
                    trigger_type="issue_accepted", issue_id=issue_id
                )
                result: dict = {"id": issue_id, "status": issue_status}
                if pipeline_run:
                    result["pipeline_run_id"] = pipeline_run.id
                return result
            except Exception:
                logger.warning(
                    "Failed to auto-start pipeline for issue %s", issue_id, exc_info=True
                )
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

from app.services.credential_service import CredentialService
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


@mcp.tool(description=_desc["tool.list_credentials.description"])
async def list_credentials(project_id: str) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        roles = await svc.list_roles(project_id)
        return {"roles": roles}


@mcp.tool(description=_desc["tool.get_credential.description"])
async def get_credential(project_id: str, role: str) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        try:
            return await svc.get(project_id, role)
        except AppError as e:
            return {"error": e.message}


@mcp.tool(description=_desc["tool.set_credential.description"])
async def set_credential(project_id: str, role: str, url: str, fields: dict) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        cred = await svc.upsert(project_id, role, url, fields)
        await session.commit()
        return {"id": cred.id, "role": cred.role, "url": cred.url}


@mcp.tool(description=_desc["tool.delete_credential.description"])
async def delete_credential(project_id: str, role: str) -> dict:
    async with async_session() as session:
        svc = CredentialService(session)
        try:
            await svc.delete(project_id, role)
            await session.commit()
            return {"deleted": True}
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


# ── Agent tools ──────────────────────────────────────────────────────────────


@mcp.tool(description=_desc["tool.list_agents.description"])
async def list_agents(project_id: str) -> dict:
    async with async_session() as session:
        orch = OrchestratorService(session)
        agents = await orch.ensure_default_agents(project_id)
        return {"agents": [AgentResponse.from_model(a).model_dump(mode="json") for a in agents]}


@mcp.tool(description=_desc["tool.create_agent.description"])
async def create_agent(project_id: str, name: str, role_key: str, system_prompt: str = "") -> dict:
    data = AgentCreate(name=name, role_key=role_key, system_prompt=system_prompt)
    async with async_session() as session:
        agent = Agent(
            project_id=project_id,
            name=data.name,
            role_key=data.role_key,
            system_prompt=data.system_prompt,
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        await event_service.emit({
            "type": "agent_created",
            "project_id": project_id,
            "agent_id": agent.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return AgentResponse.from_model(agent).model_dump(mode="json")


@mcp.tool(description=_desc["tool.update_agent.description"])
async def update_agent(agent_id: str, name: str | None = None, system_prompt: str | None = None, enabled: bool | None = None) -> dict:
    async with async_session() as session:
        agent = await session.get(Agent, agent_id)
        if agent is None:
            return {"error": "Agent not found"}
        if name is not None:
            agent.name = name
        if system_prompt is not None:
            agent.system_prompt = system_prompt
        if enabled is not None:
            agent.enabled = enabled
        await session.commit()
        await session.refresh(agent)
        await event_service.emit({
            "type": "agent_updated",
            "project_id": agent.project_id,
            "agent_id": agent.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return AgentResponse.from_model(agent).model_dump(mode="json")


@mcp.tool(description=_desc["tool.delete_agent.description"])
async def delete_agent(agent_id: str) -> dict:
    async with async_session() as session:
        agent = await session.get(Agent, agent_id)
        if agent is None:
            return {"error": "Agent not found"}
        project_id = agent.project_id
        await session.delete(agent)
        await session.commit()
        await event_service.emit({
            "type": "agent_deleted",
            "project_id": project_id,
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"deleted": True}


# ── Pipeline tools ───────────────────────────────────────────────────────────


@mcp.tool(description=_desc["tool.list_pipelines.description"])
async def list_pipelines(project_id: str) -> dict:
    async with async_session() as session:
        from sqlalchemy import select
        import json as _json
        result = await session.execute(
            select(Pipeline).where(Pipeline.project_id == project_id).order_by(Pipeline.name)
        )
        pipelines = result.scalars().all()
        return {
            "pipelines": [
                {
                    "id": p.id,
                    "project_id": p.project_id,
                    "name": p.name,
                    "steps": _json.loads(p.steps) if p.steps else [],
                    "is_default": p.is_default,
                    "trigger_type": p.trigger_type,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in pipelines
            ]
        }


@mcp.tool(description=_desc["tool.create_pipeline.description"])
async def create_pipeline(project_id: str, name: str, steps: list[dict], is_default: bool = False, trigger_type: str = "issue_accepted") -> dict:
    import json as _json
    from sqlalchemy import update
    async with async_session() as session:
        if is_default:
            await session.execute(
                update(Pipeline)
                .where(Pipeline.project_id == project_id, Pipeline.is_default == True)
                .values(is_default=False)
            )
        pipeline = Pipeline(
            project_id=project_id,
            name=name,
            steps=_json.dumps(steps),
            is_default=is_default,
            trigger_type=trigger_type,
        )
        session.add(pipeline)
        await session.commit()
        await session.refresh(pipeline)
        await event_service.emit({
            "type": "pipeline_created",
            "project_id": project_id,
            "pipeline_id": pipeline.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "id": pipeline.id,
            "project_id": pipeline.project_id,
            "name": pipeline.name,
            "steps": _json.loads(pipeline.steps),
            "is_default": pipeline.is_default,
            "trigger_type": pipeline.trigger_type,
        }


@mcp.tool(description=_desc["tool.update_pipeline.description"])
async def update_pipeline(pipeline_id: str, name: str | None = None, steps: list[dict] | None = None, is_default: bool | None = None, trigger_type: str | None = None) -> dict:
    import json as _json
    from sqlalchemy import update
    async with async_session() as session:
        pipeline = await session.get(Pipeline, pipeline_id)
        if pipeline is None:
            return {"error": "Pipeline not found"}
        if name is not None:
            pipeline.name = name
        if steps is not None:
            pipeline.steps = _json.dumps(steps)
        if trigger_type is not None:
            pipeline.trigger_type = trigger_type
        if is_default is True:
            await session.execute(
                update(Pipeline)
                .where(Pipeline.project_id == pipeline.project_id, Pipeline.is_default == True)
                .values(is_default=False)
            )
            pipeline.is_default = True
        elif is_default is not None:
            pipeline.is_default = is_default
        await session.commit()
        await session.refresh(pipeline)
        await event_service.emit({
            "type": "pipeline_updated",
            "project_id": pipeline.project_id,
            "pipeline_id": pipeline.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "id": pipeline.id,
            "project_id": pipeline.project_id,
            "name": pipeline.name,
            "steps": _json.loads(pipeline.steps),
            "is_default": pipeline.is_default,
            "trigger_type": pipeline.trigger_type,
        }


@mcp.tool(description=_desc["tool.delete_pipeline.description"])
async def delete_pipeline(pipeline_id: str) -> dict:
    async with async_session() as session:
        pipeline = await session.get(Pipeline, pipeline_id)
        if pipeline is None:
            return {"error": "Pipeline not found"}
        project_id = pipeline.project_id
        await session.delete(pipeline)
        await session.commit()
        await event_service.emit({
            "type": "pipeline_deleted",
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"deleted": True}


# ── Agent Chat tools ─────────────────────────────────────────────────────────


@mcp.tool(description=_desc["tool.send_agent_message.description"])
async def send_agent_message(issue_id: str, content: str, message_type: str = "context") -> dict:
    if message_type not in ("context", "decision", "question", "answer", "status"):
        return {"error": "message_type must be one of: context, decision, question, answer, status"}
    agent_name = os.environ.get("MANAGER_AI_AGENT_NAME", "agent")
    agent_role = os.environ.get("MANAGER_AI_AGENT_ROLE", "unknown")
    project_id = os.environ.get("MANAGER_AI_PROJECT_ID", "")
    async with async_session() as session:
        msg = AgentMessage(
            issue_id=issue_id,
            agent_name=agent_name,
            agent_role=agent_role,
            content=content,
            message_type=message_type,
        )
        session.add(msg)
        await session.commit()
        await session.refresh(msg)
        await event_service.emit({
            "type": "agent_message_added",
            "project_id": project_id,
            "issue_id": issue_id,
            "message": {
                "id": msg.id,
                "issue_id": msg.issue_id,
                "agent_name": msg.agent_name,
                "agent_role": msg.agent_role,
                "content": msg.content,
                "message_type": msg.message_type,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return AgentMessageResponse.model_validate(msg).model_dump(mode="json")


@mcp.tool(description=_desc["tool.get_agent_messages.description"])
async def get_agent_messages(issue_id: str) -> dict:
    async with async_session() as session:
        result = await session.execute(
            select(AgentMessage)
            .where(AgentMessage.issue_id == issue_id)
            .order_by(AgentMessage.created_at)
        )
        messages = result.scalars().all()
        return {
            "messages": [
                AgentMessageResponse.model_validate(m).model_dump(mode="json")
                for m in messages
            ]
        }


# ── Pipeline Execution tools ────────────────────────────────────────────────


@mcp.tool(description=_desc["tool.complete_agent_step.description"])
async def complete_agent_step(pipeline_run_id: str, summary: str = "") -> dict:
    async with async_session() as session:
        orch = OrchestratorService(session)
        return await orch.complete_agent_step(pipeline_run_id, summary)


@mcp.tool(description=_desc["tool.get_pipeline_status.description"])
async def get_pipeline_status(pipeline_run_id: str) -> dict:
    async with async_session() as session:
        orch = OrchestratorService(session)
        return await orch.get_pipeline_status(pipeline_run_id)


@mcp.tool(description=_desc["tool.start_pipeline.description"])
async def start_pipeline(issue_id: str) -> dict:
    async with async_session() as session:
        orch = OrchestratorService(session)
        pipeline_run = await orch.start_pipeline(
            trigger_type="manual", issue_id=issue_id
        )
        if pipeline_run is None:
            return {"error": "No default pipeline found for this project"}
        return {
            "pipeline_run_id": pipeline_run.id,
            "status": pipeline_run.status.value,
            "trigger_type": pipeline_run.trigger_type,
        }


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
        try:
            issue = await issue_service.get_by_id(issue_id)
            project_id = issue.project_id
        except AppError:
            return {"error": "Issue not found"}

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"timed_out": True, "question_id": q.id}

    updated = question_store.get(q.id)
    return {
        "question_id": q.id,
        "answer": updated.answer if updated else None,
        "selected_option": updated.selected_option if updated else None,
        "timed_out": False,
    }
