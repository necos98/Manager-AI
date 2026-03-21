import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
async def post_event(event: dict):
    await event_service.emit(event)
    return {"ok": True}
