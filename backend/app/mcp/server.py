import uuid

from mcp.server.fastmcp import FastMCP

from app.database import async_session
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

mcp = FastMCP("Manager AI")


@mcp.tool()
async def get_next_task(project_id: str) -> dict | None:
    """Get the highest priority task that needs work (Declined before New, then by priority).
    Returns task id, description, status, and decline_feedback if present. Returns null if none available.
    """
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            pid = uuid.UUID(project_id)
        except ValueError:
            return {"error": f"Invalid project_id: {project_id!r}"}
        task = await task_service.get_next_task(pid)
        if task is None:
            return None
        result = {
            "id": str(task.id),
            "description": task.description,
            "status": task.status.value,
        }
        if task.decline_feedback:
            result["decline_feedback"] = task.decline_feedback
        return result


@mcp.tool()
async def get_task_details(project_id: str, task_id: str) -> dict:
    """Get all details of a specific task."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_for_project(uuid.UUID(task_id), uuid.UUID(project_id))
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {
            "id": str(task.id),
            "project_id": str(task.project_id),
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


@mcp.tool()
async def get_task_status(project_id: str, task_id: str) -> dict:
    """Get the current status of a task."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.get_for_project(uuid.UUID(task_id), uuid.UUID(project_id))
        except ValueError:
            return {"error": "Task not found"}
        except PermissionError as e:
            return {"error": str(e)}
        return {"id": str(task.id), "status": task.status.value}


@mcp.tool()
async def get_project_context(project_id: str) -> dict:
    """Get project information (name, path, description)."""
    async with async_session() as session:
        project_service = ProjectService(session)
        try:
            pid = uuid.UUID(project_id)
        except ValueError:
            return {"error": f"Invalid project_id: {project_id!r}"}
        project = await project_service.get_by_id(pid)
        if project is None:
            return {"error": "Project not found"}
        return {
            "id": str(project.id),
            "name": project.name,
            "path": project.path,
            "description": project.description,
        }


@mcp.tool()
async def set_task_name(project_id: str, task_id: str, name: str) -> dict:
    """Set the name of a task after analysis."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.set_name(uuid.UUID(task_id), uuid.UUID(project_id), name)
            await session.commit()
            return {"id": str(task.id), "name": task.name}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool()
async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    """Save a markdown plan for a task and set status to Planned. Only works for tasks in New or Declined status."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.save_plan(uuid.UUID(task_id), uuid.UUID(project_id), plan)
            await session.commit()
            return {"id": str(task.id), "status": task.status.value, "plan": task.plan}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}


@mcp.tool()
async def complete_task(project_id: str, task_id: str, recap: str) -> dict:
    """Mark a task as Finished and save the recap. Only works for tasks in Accepted status."""
    async with async_session() as session:
        task_service = TaskService(session)
        try:
            task = await task_service.complete_task(uuid.UUID(task_id), uuid.UUID(project_id), recap)
            await session.commit()
            return {"id": str(task.id), "status": task.status.value, "recap": task.recap}
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}
