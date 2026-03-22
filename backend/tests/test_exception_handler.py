import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_404_returns_json_detail(client):
    """A non-existent project returns 404 with JSON detail from global handler."""
    resp = await client.get("/api/projects/nonexistent-id")
    assert resp.status_code == 404
    assert "detail" in resp.json()
