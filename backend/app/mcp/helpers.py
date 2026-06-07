"""Common utilities for MCP tools."""

import inspect
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from app.exceptions import AppError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def mcp_session():
    """Context manager yielding an async DB session.

    Uses dynamic ``import app.database`` so tests can patch
    ``app.database.async_session`` and the change is picked up
    at call time.
    """
    import app.database

    async with app.database.async_session() as session:
        yield session


def safe_uuid(value: str) -> UUID | None:
    """Convert string to UUID or return *None*."""
    try:
        return UUID(value)
    except (ValueError, TypeError):
        return None


def ok(data: dict) -> dict:
    """Return a success response dict."""
    return data


def err(message: str) -> dict:
    """Return an error response dict."""
    return {"error": message}


def mcp_tool_wrapper(func):
    """Wraps an async function with ``mcp_session()`` + ``try/except AppError``.

    Strips the ``session`` parameter from the signature so MCP sees
    a clean interface.  Used by tools that follow the standard pattern:
    create service -> call method -> commit -> emit event -> return dict.
    """
    sig = inspect.signature(func)
    no_session = [p for p in sig.parameters.values() if p.name != "session"]
    new_sig = sig.replace(parameters=no_session)

    async def wrapper(*args, **kwargs):
        async with mcp_session() as session:
            try:
                return await func(session, *args, **kwargs)
            except AppError as e:
                return {"error": e.message}

    wrapper.__name__ = func.__name__
    wrapper.__signature__ = new_sig
    return wrapper


# ── serializer helpers (shared across domains) ────────────────────────


def issue_display_name(issue, max_len: int = 50) -> str:
    """Best-effort display name for an issue."""
    return issue.name or (issue.description or "")[:max_len] or ""


def serialize_agent(agent) -> dict:
    """Convert an agent ORM object to a plain dict."""
    return {
        "id": agent.id,
        "name": agent.name,
        "intent": agent.intent,
        "model": agent.model,
        "allowed_tools": agent.allowed_tools,
        "created_at": str(agent.created_at) if agent.created_at else None,
        "updated_at": str(agent.updated_at) if agent.updated_at else None,
    }
