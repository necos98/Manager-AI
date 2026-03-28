import asyncio
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from datetime import datetime, timezone

from app.database import async_session
from app.exceptions import AppError
from app.models.issue import Issue
from app.rag import get_rag_service
from app.services.event_service import event_service
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

_defaults_path = Path(__file__).parent / "default_settings.json"
_desc = json.loads(_defaults_path.read_text(encoding="utf-8"))

mcp = FastMCP(_desc["server.name"], streamable_http_path="/")


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
            "status": issue.status.value,
            "priority": issue.priority,
            "specification": issue.specification,
            "plan": issue.plan,
            "recap": issue.recap,
            "tasks": [
                {"id": t.id, "name": t.name, "status": t.status.value, "order": t.order}
                for t in issue.tasks
            ],
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
        }


@mcp.tool(description=_desc["tool.get_issue_status.description"])
async def get_issue_status(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except AppError as e:
            return {"error": e.message}
        return {"id": issue.id, "status": issue.status.value}


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
            await session.rollback()
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
            issue_status = issue.status.value
            try:
                project = await ProjectService(session).get_by_id(project_id)
                project_name = project.name
            except AppError:
                project_name = ""
            await session.commit()

            # Trigger async embedding
            rag = get_rag_service()
            asyncio.create_task(rag.embed_issue(
                project_id=project_id,
                source_id=issue_id_val,
                issue_data=issue_data,
                project_name=project_name,
            ))

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


@mcp.tool(description=_desc["tool.create_issue_spec.description"])
async def create_issue_spec(project_id: str, issue_id: str, spec: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.create_spec(issue_id, project_id, spec)
            await session.commit()
            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue.status.value,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value, "specification": issue.specification}
        except AppError as e:
            await session.rollback()
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
            return {"id": issue.id, "status": issue.status.value, "specification": issue.specification}
        except AppError as e:
            await session.rollback()
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
                "new_status": issue.status.value,
                "project_id": project_id,
                "issue_id": issue_id,
                "issue_name": issue.name or (issue.description or "")[:50] or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"id": issue.id, "status": issue.status.value, "plan": issue.plan}
        except AppError as e:
            await session.rollback()
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
            return {"id": issue.id, "status": issue.status.value, "plan": issue.plan}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}


@mcp.tool(description=_desc["tool.accept_issue.description"])
async def accept_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.accept_issue(issue_id, project_id)
            issue_status = issue.status.value
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
            issue_status = issue.status.value
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
            issue = await session.get(Issue, issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": issue_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in created]}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}


@mcp.tool(description=_desc["tool.replace_plan_tasks.description"])
async def replace_plan_tasks(issue_id: str, tasks: list[dict]) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            created = await task_service.replace_all(issue_id, tasks)
            issue = await session.get(Issue, issue_id)
            await session.commit()
            if issue:
                await event_service.emit({
                    "type": "task_updated",
                    "project_id": issue.project_id,
                    "issue_id": issue_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in created]}
        except AppError as e:
            await session.rollback()
            return {"error": e.message}


@mcp.tool(description=_desc["tool.update_task_status.description"])
async def update_task_status(task_id: str, status: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, status=status)
            task_issue_id = task.issue_id
            task_id_val = task.id
            task_name = task.name
            task_status = task.status.value
            issue = await session.get(Issue, task_issue_id)
            all_done = (
                await task_service.all_completed(task_issue_id)
                if task.status.value == "Completed"
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
            await session.rollback()
            return {"error": e.message}


@mcp.tool(description=_desc["tool.update_task_name.description"])
async def update_task_name(task_id: str, name: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.update(task_id, name=name)
            task_issue_id = task.issue_id
            task_id_val = task.id
            task_name = task.name
            issue = await session.get(Issue, task_issue_id)
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
            await session.rollback()
            return {"error": e.message}


@mcp.tool(description=_desc["tool.delete_task.description"])
async def delete_task(task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_by_id(task_id)
            task_issue_id = task.issue_id
            issue = await session.get(Issue, task_issue_id)
            project_id = issue.project_id if issue else None
            await session.delete(task)
            await session.flush()
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
            await session.rollback()
            return {"error": e.message}


@mcp.tool(description=_desc["tool.get_plan_tasks.description"])
async def get_plan_tasks(issue_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        tasks = await task_service.list_by_issue(issue_id)
        return {"tasks": [{"id": t.id, "name": t.name, "status": t.status.value, "order": t.order} for t in tasks]}


# ── RAG tools (project context search) ─────────────────────────────────────


@mcp.tool(description=_desc["tool.search_project_context.description"])
async def search_project_context(
    project_id: str,
    query: str,
    source_type: str | None = None,
    limit: int = 5,
) -> dict:
    rag = get_rag_service()
    results = await rag.search(
        query=query, project_id=project_id, source_type=source_type, limit=limit
    )
    return {"results": results}


@mcp.tool(description=_desc["tool.get_context_chunk_details.description"])
async def get_context_chunk_details(project_id: str, chunk_id: str) -> dict:
    rag = get_rag_service()
    chunk = await rag.get_chunk_details(chunk_id=chunk_id, project_id=project_id)
    if chunk is None:
        return {"error": "Chunk not found or does not belong to this project"}
    return chunk
