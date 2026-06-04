"""Tests for agent and pipeline export/import endpoints."""

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


SAMPLE_AGENT = {
    "name": "TestAgent",
    "intent": "You are a test agent",
    "model": "claude-sonnet-4-6",
    "allowed_tools": ["read", "write"],
}

SAMPLE_AGENT_2 = {
    "name": "TestAgent2",
    "intent": "You are another test agent",
}


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _export_wrapper(type_: str, items: list) -> bytes:
    return json.dumps({
        "version": 1,
        "type": type_,
        "exported_at": "2026-06-04T21:00:00Z",
        "items": items,
    }).encode()


# ─── Agent Export ───


@pytest.mark.asyncio
async def test_export_agents_empty(client):
    resp = await client.get("/api/agents/export")
    assert resp.status_code == 200
    assert resp.headers.get("content-disposition", "").startswith("attachment")
    data = resp.json()
    assert data["version"] == 1
    assert data["type"] == "agents"
    assert data["items"] == []


@pytest.mark.asyncio
async def test_export_agents_all(client):
    a1 = (await client.post("/api/agents", json=SAMPLE_AGENT)).json()
    a2 = (await client.post("/api/agents", json=SAMPLE_AGENT_2)).json()

    resp = await client.get("/api/agents/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "agents"
    assert len(data["items"]) == 2
    exported_ids = {i["id"] for i in data["items"]}
    assert exported_ids == {a1["id"], a2["id"]}

    # No timestamps in export
    for item in data["items"]:
        assert "created_at" not in item
        assert "updated_at" not in item


@pytest.mark.asyncio
async def test_export_agent_single(client):
    a1 = (await client.post("/api/agents", json=SAMPLE_AGENT)).json()
    resp = await client.get(f"/api/agents/export/{a1['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == a1["id"]
    assert data["items"][0]["name"] == "TestAgent"


@pytest.mark.asyncio
async def test_export_agent_not_found(client):
    resp = await client.get("/api/agents/export/nonexistent-id")
    assert resp.status_code == 404


# ─── Agent Import ───


@pytest.mark.asyncio
async def test_import_agents_preview_new(client):
    agent_id = "test-id-001"
    content = _export_wrapper("agents", [
        {"id": agent_id, "name": "ImportedAgent", "intent": "imported"},
    ])
    resp = await client.post(
        "/api/agents/import/preview",
        files={"file": ("test.json", content, "application/json")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["new"]) == 1
    assert data["new"][0]["id"] == agent_id
    assert len(data["conflicts"]) == 0


@pytest.mark.asyncio
async def test_import_agents_preview_with_conflicts(client):
    existing = (await client.post("/api/agents", json=SAMPLE_AGENT)).json()
    content = _export_wrapper("agents", [
        {"id": existing["id"], "name": "UpdatedName", "intent": "updated"},
    ])
    resp = await client.post(
        "/api/agents/import/preview",
        files={"file": ("test.json", content, "application/json")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["conflicts"]) == 1
    assert data["conflicts"][0]["incoming"]["name"] == "UpdatedName"
    assert data["conflicts"][0]["existing"]["name"] == "TestAgent"


@pytest.mark.asyncio
async def test_import_agents_preview_invalid_json(client):
    resp = await client.post(
        "/api/agents/import/preview",
        files={"file": ("bad.json", b"not json", "application/json")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_agents_preview_wrong_type(client):
    content = _export_wrapper("pipelines", [])
    resp = await client.post(
        "/api/agents/import/preview",
        files={"file": ("test.json", content, "application/json")},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_agents_confirm_new(client):
    content = _export_wrapper("agents", [
        {"id": "new-agent-1", "name": "NewAgent", "intent": "new", "model": None, "allowed_tools": None},
    ])
    resp = await client.post(
        "/api/agents/import/confirm",
        files={"file": ("test.json", content, "application/json")},
        data={"conflicts": "{}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert data["skipped"] == 0
    assert data["errors"] == []

    # Verify persisted
    list_resp = await client.get("/api/agents")
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_import_agents_confirm_overwrite(client):
    existing = (await client.post("/api/agents", json=SAMPLE_AGENT)).json()
    content = _export_wrapper("agents", [
        {"id": existing["id"], "name": "Overwritten", "intent": "updated", "model": None, "allowed_tools": None},
    ])
    resp = await client.post(
        "/api/agents/import/confirm",
        files={"file": ("test.json", content, "application/json")},
        data={"conflicts": json.dumps({existing["id"]: "overwrite"})},
    )
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1

    # Verify overwritten
    get_resp = await client.get(f"/api/agents/{existing['id']}")
    assert get_resp.json()["name"] == "Overwritten"


@pytest.mark.asyncio
async def test_import_agents_confirm_skip(client):
    existing = (await client.post("/api/agents", json=SAMPLE_AGENT)).json()
    content = _export_wrapper("agents", [
        {"id": existing["id"], "name": "ShouldStay", "intent": "skipped"},
    ])
    resp = await client.post(
        "/api/agents/import/confirm",
        files={"file": ("test.json", content, "application/json")},
        data={"conflicts": json.dumps({existing["id"]: "skip"})},
    )
    assert resp.status_code == 200
    assert resp.json()["skipped"] == 1

    get_resp = await client.get(f"/api/agents/{existing['id']}")
    assert get_resp.json()["name"] == "TestAgent"


# ─── Pipeline Export ───


@pytest.mark.asyncio
async def test_export_pipelines_empty(client):
    resp = await client.get("/api/pipelines/export")
    assert resp.status_code == 200
    assert resp.headers.get("content-disposition", "").startswith("attachment")
    data = resp.json()
    assert data["version"] == 1
    assert data["type"] == "pipelines"
    assert data["items"] == []


@pytest.mark.asyncio
async def test_export_pipelines_all(client):
    agent = (await client.post("/api/agents", json=SAMPLE_AGENT)).json()
    pipeline = (
        await client.post(
            "/api/pipelines",
            json={"name": "TestPipeline", "steps": [{"agent_id": agent["id"]}]},
        )
    ).json()

    resp = await client.get("/api/pipelines/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "pipelines"
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["id"] == pipeline["id"]
    assert len(item["steps"]) == 1
    assert item["steps"][0]["agent"]["id"] == agent["id"]
    assert item["steps"][0]["agent"]["name"] == "TestAgent"


@pytest.mark.asyncio
async def test_export_pipeline_not_found(client):
    resp = await client.get("/api/pipelines/export/nonexistent")
    assert resp.status_code == 404


# ─── Pipeline Import ───


@pytest.mark.asyncio
async def test_import_pipelines_preview_new(client):
    content = _export_wrapper("pipelines", [
        {
            "id": "pipe-1",
            "name": "ImportedPipeline",
            "steps": [
                {
                    "id": "step-1",
                    "pipeline_id": "pipe-1",
                    "agent_id": "agent-1",
                    "order_index": 0,
                    "agent": {"id": "agent-1", "name": "StepAgent", "intent": "test"},
                }
            ],
        }
    ])
    resp = await client.post(
        "/api/pipelines/import/preview",
        files={"file": ("test.json", content, "application/json")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["new"]) == 1
    assert len(data["conflicts"]) == 0


@pytest.mark.asyncio
async def test_import_pipelines_preview_missing_agents(client):
    content = _export_wrapper("pipelines", [
        {
            "id": "pipe-2",
            "name": "MissingAgents",
            "steps": [
                {
                    "id": "step-2",
                    "pipeline_id": "pipe-2",
                    "agent_id": "ghost-agent",
                    "order_index": 0,
                    # No inline agent data
                }
            ],
        }
    ])
    resp = await client.post(
        "/api/pipelines/import/preview",
        files={"file": ("test.json", content, "application/json")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["missing_agents"]) > 0
    assert data["missing_agents"][0]["agent_id"] == "ghost-agent"


@pytest.mark.asyncio
async def test_import_pipelines_confirm_with_agents(client):
    content = _export_wrapper("pipelines", [
        {
            "id": "pipe-3",
            "name": "FullPipeline",
            "steps": [
                {
                    "id": "step-3",
                    "pipeline_id": "pipe-3",
                    "agent_id": "agent-builtin",
                    "order_index": 0,
                    "agent": {"id": "agent-builtin", "name": "BuiltInAgent", "intent": "helper"},
                }
            ],
        }
    ])
    resp = await client.post(
        "/api/pipelines/import/confirm",
        files={"file": ("test.json", content, "application/json")},
        data={"conflicts": "{}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1

    # Verify pipeline created
    pipes = (await client.get("/api/pipelines")).json()
    assert any(p["name"] == "FullPipeline" for p in pipes)

    # Verify agent auto-created
    agents = (await client.get("/api/agents")).json()
    assert any(a["name"] == "BuiltInAgent" for a in agents)


@pytest.mark.asyncio
async def test_import_pipelines_confirm_overwrite(client):
    agent = (await client.post("/api/agents", json=SAMPLE_AGENT)).json()
    pipeline = (
        await client.post(
            "/api/pipelines",
            json={"name": "OriginalName", "steps": [{"agent_id": agent["id"]}]},
        )
    ).json()

    content = _export_wrapper("pipelines", [
        {
            "id": pipeline["id"],
            "name": "RenamedPipeline",
            "steps": [
                {
                    "id": "new-step",
                    "pipeline_id": pipeline["id"],
                    "agent_id": agent["id"],
                    "order_index": 0,
                    "agent": {"id": agent["id"], "name": agent["name"], "intent": agent["intent"]},
                }
            ],
        }
    ])
    resp = await client.post(
        "/api/pipelines/import/confirm",
        files={"file": ("test.json", content, "application/json")},
        data={"conflicts": json.dumps({pipeline["id"]: "overwrite"})},
    )
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1
    assert resp.json()["skipped"] == 0

    # Verify renamed
    updated = (await client.get(f"/api/pipelines/{pipeline['id']}")).json()
    assert updated["name"] == "RenamedPipeline"
