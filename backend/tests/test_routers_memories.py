import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import get_db
from app.models.project import Project
from app.services.memory_service import MemoryService


@pytest.mark.asyncio
async def test_list_and_detail(db_session):
    async def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.flush()
    svc = MemoryService(db_session)
    a = await svc.create(project_id="p1", title="Root", description="top")
    b = await svc.create(project_id="p1", title="Child", description="leaf", parent_id=a.id)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/projects/p1/memories")
        assert r.status_code == 200
        assert {m["id"] for m in r.json()} == {a.id, b.id}

        r = await client.get(f"/api/memories/{a.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == a.id
        assert [c["id"] for c in body["children"]] == [b.id]

    app.dependency_overrides.clear()
