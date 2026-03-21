import asyncio
import json
from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    """Abstract base class for event notifiers."""

    @abstractmethod
    async def notify(self, event: dict):
        pass


class WebSocketNotifier(BaseNotifier):
    """Broadcasts events to all connected WebSocket clients."""

    def __init__(self):
        self._clients: set = set()

    def connect(self, ws):
        self._clients.add(ws)

    def disconnect(self, ws):
        self._clients.discard(ws)

    async def notify(self, event: dict):
        if not self._clients:
            return

        message = json.dumps(event)
        dead = set()

        for ws in list(self._clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self._clients.discard(ws)


class EventService:
    """Singleton service that emits events to all registered notifiers."""

    def __init__(self):
        self._notifiers: list = []

    def register(self, notifier: BaseNotifier):
        self._notifiers.append(notifier)

    async def emit(self, event: dict):
        for notifier in self._notifiers:
            try:
                await notifier.notify(event)
            except Exception:
                pass


# Module-level singleton with WebSocketNotifier pre-registered
websocket_notifier = WebSocketNotifier()
event_service = EventService()
event_service.register(websocket_notifier)
