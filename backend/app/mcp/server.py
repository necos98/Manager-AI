import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.services.project_service import ProjectService
from app.services.settings_service import SettingsService
from app.services.task_service import TaskService

# Load descriptions from default_settings.json at startup.
# Tool descriptions are static for the lifetime of this process
# (MCP protocol exposes them at handshake time, not per-call).
# To apply DB-stored description overrides, restart the backend.
_defaults_path = Path(__file__).parent / "default_settings.json"
_desc = json.loads(_defaults_path.read_text(encoding="utf-8"))

mcp = FastMCP(_desc["server.name"], streamable_http_path="/")


@mcp.tool(description=_desc["tool.get_next_task.description"])
async def get_next_task(project_id: str) -> dict | None:
    async with async_session() as session:
        task_service = TaskService(session)
        task = await task_service.get_next_task(project_id)
        if task is None:
            return None
        result = {
            "id": task.id,
            "description": task.description,
            "status": task.status.value,
        }
        if task.decline_feedback:
            result["decline_feedback"] = task.decline_feedback
        return result


@mcp.tool(description=_desc["tool.get_task_details.description"])
async def get_task_details(project_id: str, task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_for_project(task_id, project_id)
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {
            "id": task.id,
            "project_id": task.project_id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority,
            "plan": task.plan,
            "recap": task.recap,
            "decline_feedback": task.decline_feedback,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


@mcp.tool(description=_desc["tool.get_task_status.description"])
async def get_task_status(project_id: str, task_id: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_for_project(task_id, project_id)
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {"id": task.id, "status": task.status.value}


@mcp.tool(description=_desc["tool.get_project_context.description"])
async def get_project_context(project_id: str) -> dict:
    async with async_session() as session:
        project_service = ProjectService(session)
        project = await project_service.get_by_id(project_id)
        if project is None:
            return {"error": "Project not found"}
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "description": project.description,
            "tech_stack": project.tech_stack,
        }


@mcp.tool(description=_desc["tool.set_task_name.description"])
async def set_task_name(project_id: str, task_id: str, name: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.set_name(task_id, project_id, name)
            await session.commit()
            return {"id": task.id, "name": task.name}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.save_task_plan.description"])
async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        settings_service = SettingsService(session)
        try:
            task = await task_service.save_plan(task_id, project_id, plan)
            await session.commit()
            # Response message is read from DB on every call — real-time updates.
            response_msg = await settings_service.get("tool.save_task_plan.response_message")
            return {
                "id": task.id,
                "status": task.status.value,
                "plan": task.plan,
                "message": response_msg,
            }
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool(description=_desc["tool.complete_task.description"])
async def complete_task(project_id: str, task_id: str, recap: str) -> dict:
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.complete_task(task_id, project_id, recap)
            await session.commit()
            return {"id": task.id, "status": task.status.value, "recap": task.recap}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}
