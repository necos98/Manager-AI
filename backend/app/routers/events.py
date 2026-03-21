import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.event_service import event_service, websocket_notifier

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


@router.post("")
async def post_event(event: dict, db: AsyncSession = Depends(get_db)):
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
