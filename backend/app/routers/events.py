import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.event_service import event_service, websocket_notifier
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.websocket("/ws")
async def events_ws(websocket: WebSocket):
    await websocket.accept()
    websocket_notifier.connect(websocket)
    try:
        while True:
            # Keep connection alive; clients may send pings as plain text
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("events_ws error", exc_info=True)
    finally:
        websocket_notifier.disconnect(websocket)


def _truncate_for_tts(text: str, cap: int) -> str:
    text = text.strip()
    if len(text) <= cap:
        return text
    window = text[:cap]
    for sep in (". ", "! ", "? "):
        idx = window.rfind(sep)
        if idx >= cap // 2:
            return window[: idx + 1].rstrip() + "…"
    idx = window.rfind(" ")
    if idx >= cap // 2:
        return window[:idx] + "…"
    return window + "…"


async def _prepare_tts_event(event: dict, db: AsyncSession) -> dict | None:
    text = (event.get("text") or "").strip()
    if not text:
        return None
    svc = SettingsService(db)
    enabled = (await svc.get("tts.enabled")).lower() == "true"
    if not enabled:
        return None
    try:
        cap = max(1, int(await svc.get("tts.cap_chars")))
    except (TypeError, ValueError):
        cap = 500
    voice = await svc.get("tts.voice")
    try:
        rate = float(await svc.get("tts.rate"))
    except (TypeError, ValueError):
        rate = 1.0
    try:
        pitch = float(await svc.get("tts.pitch"))
    except (TypeError, ValueError):
        pitch = 1.0
    return {
        "type": "tts",
        "text": _truncate_for_tts(text, cap),
        "voice": voice,
        "rate": rate,
        "pitch": pitch,
        "terminal_id": event.get("terminal_id"),
        "issue_id": event.get("issue_id"),
        "project_id": event.get("project_id"),
        "timestamp": event.get("timestamp") or datetime.now(timezone.utc).isoformat(),
    }


@router.post("")
async def post_event(event: dict, db: AsyncSession = Depends(get_db)):
    if event.get("type") == "tts":
        tts_event = await _prepare_tts_event(event, db)
        if tts_event is None:
            return {"ok": True, "dropped": True}
        await event_service.emit(tts_event)
        return {"ok": True}

    # Enrich with issue_name if issue_id + project_id are provided
    if event.get("issue_id") and event.get("project_id") and "issue_name" not in event:
        try:
            from app.models.issue import Issue
            issue = await db.get(Issue, event["issue_id"])
            if issue:
                event["issue_name"] = issue.name or (issue.description or "")[:50] or "Untitled issue"
        except Exception:
            pass

    if "timestamp" not in event:
        event["timestamp"] = datetime.now(timezone.utc).isoformat()

    await event_service.emit(event)
    return {"ok": True}
