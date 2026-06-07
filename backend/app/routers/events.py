import asyncio
import logging

from app.utils.datetime import iso_now
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
            # Wait for client messages with a timeout so we can send
            # keepalive pings.  If the client is gone the send will raise
            # and we clean up.
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Clients may send "ping" as plain text; respond with "pong".
                if raw == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text("ping")
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
            from app.services.issue_service import IssueService
            issue = await IssueService(db).get_for_project(event["issue_id"], event["project_id"])
            event["issue_name"] = issue.name or (issue.description or "")[:50] or "Untitled issue"
        except Exception:
            pass

    if "timestamp" not in event:
        event["timestamp"] = iso_now()

    await event_service.emit(event)
    return {"ok": True}
