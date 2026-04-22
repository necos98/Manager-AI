import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.event_service import event_service, BaseNotifier
from app.services.settings_service import SettingsService


class CaptureNotifier(BaseNotifier):
    def __init__(self):
        self.events: list[dict] = []

    async def notify(self, event):
        self.events.append(event)


@pytest_asyncio.fixture
async def client(db_session):
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def capture():
    cap = CaptureNotifier()
    event_service._notifiers.append(cap)
    yield cap
    if cap in event_service._notifiers:
        event_service._notifiers.remove(cap)


async def _set(db_session, key: str, value: str):
    svc = SettingsService(db_session)
    await svc.set(key, value)
    await db_session.commit()


async def test_tts_dropped_when_disabled(client, db_session, capture):
    await _set(db_session, "tts.enabled", "false")
    resp = await client.post("/api/events", json={"type": "tts", "text": "hello"})
    assert resp.status_code == 200
    assert all(e.get("type") != "tts" for e in capture.events)


async def test_tts_broadcast_when_enabled(client, db_session, capture):
    await _set(db_session, "tts.enabled", "true")
    await _set(db_session, "tts.voice", "Zira")
    await _set(db_session, "tts.rate", "1.2")
    await _set(db_session, "tts.pitch", "0.9")
    resp = await client.post("/api/events", json={"type": "tts", "text": "hello world"})
    assert resp.status_code == 200
    tts_events = [e for e in capture.events if e.get("type") == "tts"]
    assert len(tts_events) == 1
    assert tts_events[0]["text"] == "hello world"
    assert tts_events[0]["voice"] == "Zira"
    assert tts_events[0]["rate"] == 1.2
    assert tts_events[0]["pitch"] == 0.9


async def test_tts_truncates_to_cap(client, db_session, capture):
    await _set(db_session, "tts.enabled", "true")
    await _set(db_session, "tts.cap_chars", "20")
    long = "Sentence one. Sentence two is much longer than twenty chars."
    resp = await client.post("/api/events", json={"type": "tts", "text": long})
    assert resp.status_code == 200
    tts_events = [e for e in capture.events if e.get("type") == "tts"]
    assert len(tts_events) == 1
    text = tts_events[0]["text"]
    assert len(text) <= 21  # cap + ellipsis
    assert text.endswith("…")


async def test_tts_empty_text_dropped(client, db_session, capture):
    await _set(db_session, "tts.enabled", "true")
    resp = await client.post("/api/events", json={"type": "tts", "text": "   "})
    assert resp.status_code == 200
    assert all(e.get("type") != "tts" for e in capture.events)
