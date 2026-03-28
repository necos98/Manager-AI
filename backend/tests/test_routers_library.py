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
async def test_list_skills_returns_list(client):
    response = await client.get("/api/library/skills")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # Built-in skills from claude_library/ should be present
    names = [s["name"] for s in response.json()]
    assert "laravel-12" in names


@pytest.mark.asyncio
async def test_list_agents_returns_list(client):
    response = await client.get("/api/library/agents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    names = [a["name"] for a in data]
    assert "backend-architect" in names


@pytest.mark.asyncio
async def test_get_skill_not_found(client):
    response = await client.get("/api/library/skills/nonexistent-skill-xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_skill_detail(client):
    response = await client.get("/api/library/skills/laravel-12")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "laravel-12"
    assert data["built_in"] is True
    assert len(data["content"]) > 10


@pytest.mark.asyncio
async def test_create_skill(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "claude_library_path", str(tmp_path))
    # Create the skills directory
    (tmp_path / "skills").mkdir()

    response = await client.post("/api/library/skills", json={
        "name": "test-skill",
        "category": "tech",
        "description": "A test skill",
        "content": "# Test\nSome content",
    })
    assert response.status_code == 201
    assert response.json()["name"] == "test-skill"
    assert response.json()["built_in"] is False


@pytest.mark.asyncio
async def test_create_skill_duplicate(client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "claude_library_path", str(tmp_path))
    (tmp_path / "skills").mkdir()

    await client.post("/api/library/skills", json={
        "name": "dup-skill", "category": "tech", "description": "D", "content": "C",
    })
    response = await client.post("/api/library/skills", json={
        "name": "dup-skill", "category": "tech", "description": "D", "content": "C",
    })
    assert response.status_code == 409
