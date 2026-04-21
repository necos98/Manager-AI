from datetime import datetime, timezone

from app.services.event_service import event_service


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def emit_created(*, project_id: str, memory_id: str) -> None:
    await event_service.emit({"type": "memory_created", "project_id": project_id, "memory_id": memory_id, "timestamp": _now()})


async def emit_updated(*, project_id: str, memory_id: str) -> None:
    await event_service.emit({"type": "memory_updated", "project_id": project_id, "memory_id": memory_id, "timestamp": _now()})


async def emit_deleted(*, project_id: str, memory_id: str) -> None:
    await event_service.emit({"type": "memory_deleted", "project_id": project_id, "memory_id": memory_id, "timestamp": _now()})


async def emit_linked(*, project_id: str, from_id: str, to_id: str, relation: str) -> None:
    await event_service.emit({"type": "memory_linked", "project_id": project_id, "from_id": from_id, "to_id": to_id, "relation": relation, "timestamp": _now()})


async def emit_unlinked(*, project_id: str, from_id: str, to_id: str, relation: str) -> None:
    await event_service.emit({"type": "memory_unlinked", "project_id": project_id, "from_id": from_id, "to_id": to_id, "relation": relation, "timestamp": _now()})
