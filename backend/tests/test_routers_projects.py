import json
import os
import uuid
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
import yaml
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.routers.projects import _check_resource_consistency


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
async def test_create_project(client):
    response = await client.post("/api/projects", json={"name": "Test", "path": "/tmp/test", "description": "Desc"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client):
    await client.post("/api/projects", json={"name": "P1", "path": "/p1"})
    await client.post("/api/projects", json={"name": "P2", "path": "/p2"})
    response = await client.get("/api/projects")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_get_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    project_id = create_resp.json()["id"]
    response = await client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test"


@pytest.mark.asyncio
async def test_get_project_not_found(client):
    response = await client.get(f"/api/projects/{uuid.uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Old", "path": "/old"})
    project_id = create_resp.json()["id"]
    response = await client.put(f"/api/projects/{project_id}", json={"name": "New"})
    assert response.status_code == 200
    assert response.json()["name"] == "New"


@pytest.mark.asyncio
async def test_delete_project(client):
    create_resp = await client.post("/api/projects", json={"name": "Del", "path": "/del"})
    project_id = create_resp.json()["id"]
    response = await client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_project_with_tech_stack(client):
    response = await client.post(
        "/api/projects",
        json={"name": "Test", "path": "/tmp/test", "tech_stack": "Python, FastAPI"},
    )
    assert response.status_code == 201
    assert response.json()["tech_stack"] == "Python, FastAPI"


@pytest.mark.asyncio
async def test_create_project_tech_stack_defaults_to_empty(client):
    response = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    assert response.status_code == 201
    assert response.json()["tech_stack"] == ""


@pytest.mark.asyncio
async def test_update_project_tech_stack(client):
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Test", "path": "/tmp", "tech_stack": "Python"},
    )
    project_id = create_resp.json()["id"]
    response = await client.put(
        f"/api/projects/{project_id}", json={"tech_stack": "Python, React"}
    )
    assert response.status_code == 200
    assert response.json()["tech_stack"] == "Python, React"


@pytest.mark.asyncio
async def test_list_projects_excludes_archived_by_default(client):
    active = await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/projects")
    ids = [p["id"] for p in response.json()]

    assert active.json()["id"] in ids
    assert archived.json()["id"] not in ids


@pytest.mark.asyncio
async def test_list_projects_archived_true_returns_archived_only(client):
    await client.post("/api/projects", json={"name": "Active", "path": "/a"})
    archived = await client.post("/api/projects", json={"name": "Archived", "path": "/b"})
    await client.post(f"/api/projects/{archived.json()['id']}/archive")

    response = await client.get("/api/projects?archived=true")
    ids = [p["id"] for p in response.json()]

    assert ids == [archived.json()["id"]]


@pytest.mark.asyncio
async def test_list_projects_alphabetical(client):
    await client.post("/api/projects", json={"name": "banana", "path": "/b"})
    await client.post("/api/projects", json={"name": "Apple", "path": "/a"})
    await client.post("/api/projects", json={"name": "cherry", "path": "/c"})

    response = await client.get("/api/projects")
    names = [p["name"] for p in response.json()]

    assert names == ["Apple", "banana", "cherry"]


@pytest.mark.asyncio
async def test_archive_project_sets_archived_at_and_returns_response(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]

    response = await client.post(f"/api/projects/{project_id}/archive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is not None


@pytest.mark.asyncio
async def test_archive_project_not_found(client):
    response = await client.post(f"/api/projects/{uuid.uuid4()}/archive")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unarchive_project_clears_archived_at(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]
    await client.post(f"/api/projects/{project_id}/archive")

    response = await client.post(f"/api/projects/{project_id}/unarchive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_archive_is_idempotent(client):
    created = await client.post("/api/projects", json={"name": "P", "path": "/p"})
    project_id = created.json()["id"]

    first = await client.post(f"/api/projects/{project_id}/archive")
    second = await client.post(f"/api/projects/{project_id}/archive")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["archived_at"] == second.json()["archived_at"]


# ---------------------------------------------------------------------------
# _check_resource_consistency unit tests
# ---------------------------------------------------------------------------

AUTH_ID = "11111111-1111-1111-1111-111111111111"
WRONG_ID = "99999999-9999-9999-9999-999999999999"


def _make_project(path):
    return MagicMock(path=path, id=AUTH_ID)


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _make_manager_json(root, project_id=AUTH_ID):
    _write(os.path.join(root, "manager.json"), json.dumps({"project_id": project_id}))


class TestCheckResourceConsistency:
    """Unit tests for _check_resource_consistency — no DB, no HTTP, just filesystem."""

    def test_manager_json_missing(self, tmp_path):
        """When manager.json is missing, return ok=None with a note."""
        mgr = os.path.join(tmp_path, ".manager_ai")
        os.makedirs(mgr)
        _write(os.path.join(mgr, "issues.yaml"), yaml.safe_dump({"schema_version": 1, "issues": []}))

        result = _check_resource_consistency(_make_project(str(tmp_path)))

        assert result["ok"] is None
        assert result["scanned"] == 0
        assert result["fixed"] == 0
        assert "note" in result

    def test_all_consistent(self, tmp_path):
        """When all project_ids match, ok=True, fixed=0."""
        root = str(tmp_path)
        _make_manager_json(root)
        mgr = os.path.join(root, ".manager_ai")

        # issues.yaml — correct
        _write(os.path.join(mgr, "issues.yaml"), yaml.safe_dump({
            "schema_version": 1,
            "issues": [{"id": "i1", "project_id": AUTH_ID, "status": "New"}],
        }))
        # individual issue — correct
        _write(os.path.join(mgr, "issues", "i1", "issue.yaml"), yaml.safe_dump({
            "id": "i1", "project_id": AUTH_ID, "status": "New",
        }))
        # memories.yaml — correct
        _write(os.path.join(mgr, "memories.yaml"), yaml.safe_dump({
            "schema_version": 1,
            "memories": [{"id": "m1", "project_id": AUTH_ID, "title": "t"}],
        }))
        # memory .md — correct
        _write(os.path.join(mgr, "memories", "m1.md"), (
            "---\nid: m1\nproject_id: " + AUTH_ID + "\ntitle: t\n---\nbody\n"))

        result = _check_resource_consistency(_make_project(root))

        assert result["ok"] is True
        assert result["fixed"] == 0
        assert result["scanned"] == 4

    def test_fixes_mismatched_issues_yaml(self, tmp_path):
        """Entries in issues.yaml with wrong project_id get fixed."""
        root = str(tmp_path)
        _make_manager_json(root)
        mgr = os.path.join(root, ".manager_ai")
        _write(os.path.join(mgr, "issues.yaml"), yaml.safe_dump({
            "schema_version": 1,
            "issues": [
                {"id": "i1", "project_id": WRONG_ID, "status": "New"},
                {"id": "i2", "project_id": AUTH_ID, "status": "New"},
            ],
        }))

        result = _check_resource_consistency(_make_project(root))

        assert result["scanned"] == 2
        assert result["fixed"] == 1
        assert result["ok"] is False
        # Verify file was rewritten
        fixed = yaml.safe_load(_read(os.path.join(mgr, "issues.yaml")))
        assert fixed["issues"][0]["project_id"] == AUTH_ID
        assert fixed["issues"][1]["project_id"] == AUTH_ID

    def test_fixes_mismatched_individual_issue(self, tmp_path):
        root = str(tmp_path)
        _make_manager_json(root)
        mgr = os.path.join(root, ".manager_ai")
        _write(os.path.join(mgr, "issues", "i1", "issue.yaml"), yaml.safe_dump({
            "id": "i1", "project_id": WRONG_ID, "status": "New",
        }))

        result = _check_resource_consistency(_make_project(root))

        assert result["fixed"] == 1
        fixed = yaml.safe_load(_read(os.path.join(mgr, "issues", "i1", "issue.yaml")))
        assert fixed["project_id"] == AUTH_ID

    def test_fixes_mismatched_memories_yaml(self, tmp_path):
        root = str(tmp_path)
        _make_manager_json(root)
        mgr = os.path.join(root, ".manager_ai")
        _write(os.path.join(mgr, "memories.yaml"), yaml.safe_dump({
            "schema_version": 1,
            "memories": [
                {"id": "m1", "project_id": WRONG_ID, "title": "t"},
                {"id": "m2", "project_id": AUTH_ID, "title": "t2"},
            ],
        }))

        result = _check_resource_consistency(_make_project(root))

        assert result["fixed"] == 1
        fixed = yaml.safe_load(_read(os.path.join(mgr, "memories.yaml")))
        assert fixed["memories"][0]["project_id"] == AUTH_ID

    def test_fixes_mismatched_memory_md(self, tmp_path):
        root = str(tmp_path)
        _make_manager_json(root)
        mgr = os.path.join(root, ".manager_ai")
        _write(os.path.join(mgr, "memories", "m1.md"), (
            "---\nid: m1\nproject_id: " + WRONG_ID + "\ntitle: t\n---\nbody text\n"))

        result = _check_resource_consistency(_make_project(root))

        assert result["fixed"] == 1
        fixed = _read(os.path.join(mgr, "memories", "m1.md"))
        assert "project_id: " + AUTH_ID in fixed
        assert "body text" in fixed  # body preserved

    def test_details_report_mismatches(self, tmp_path):
        root = str(tmp_path)
        _make_manager_json(root)
        mgr = os.path.join(root, ".manager_ai")
        _write(os.path.join(mgr, "issues.yaml"), yaml.safe_dump({
            "schema_version": 1,
            "issues": [{"id": "i-bad", "project_id": WRONG_ID, "status": "New"}],
        }))

        result = _check_resource_consistency(_make_project(root))

        assert len(result["details"]) == 1
        assert result["details"][0]["resource_id"] == "i-bad"
        assert result["details"][0]["file"] == os.path.join(".manager_ai", "issues.yaml")

    def test_no_manager_ai_dir(self, tmp_path):
        _make_manager_json(str(tmp_path))

        result = _check_resource_consistency(_make_project(str(tmp_path)))

        assert result["scanned"] == 0
        assert result["fixed"] == 0

    def test_skip_missing_issues_yaml(self, tmp_path):
        """Missing optional files are silently skipped."""
        root = str(tmp_path)
        _make_manager_json(root)
        os.makedirs(os.path.join(root, ".manager_ai"))

        result = _check_resource_consistency(_make_project(root))

        assert result["scanned"] == 0
        assert result["fixed"] == 0


# ---------------------------------------------------------------------------
# Health endpoint integration test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_includes_resource_consistency(client, tmp_path):
    """GET /api/projects/{id}/health includes resource_consistency field."""
    root = str(tmp_path)
    _make_manager_json(root)
    mgr = os.path.join(root, ".manager_ai")
    _write(os.path.join(mgr, "issues.yaml"), yaml.safe_dump({
        "schema_version": 1,
        "issues": [{"id": "i1", "project_id": AUTH_ID, "status": "New"}],
    }))

    # Create project with tmp_path as path
    create_resp = await client.post("/api/projects", json={
        "name": "health-test", "path": root,
    })
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # The project.id from DB won't match AUTH_ID — manager.json has AUTH_ID.
    # Re-write manager.json with the actual project_id so the test is realistic.
    # But wait: the test is about mismatches. Let's test with matching IDs first.
    actual_id = create_resp.json()["id"]
    _write(os.path.join(root, "manager.json"), json.dumps({"project_id": actual_id}))
    _write(os.path.join(mgr, "issues.yaml"), yaml.safe_dump({
        "schema_version": 1,
        "issues": [{"id": "i1", "project_id": actual_id, "status": "New"}],
    }))

    response = await client.get(f"/api/projects/{project_id}/health")
    assert response.status_code == 200
    data = response.json()
    assert "resource_consistency" in data
    assert data["resource_consistency"]["ok"] is True
    assert data["resource_consistency"]["scanned"] >= 0


@pytest.mark.asyncio
async def test_health_includes_playwright_mcp(client, tmp_path):
    """GET /api/projects/{id}/health includes playwright_mcp field."""
    root = str(tmp_path)
    _make_manager_json(root)

    create_resp = await client.post("/api/projects", json={
        "name": "health-pw-test", "path": root,
    })
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/projects/{project_id}/health")
    assert response.status_code == 200
    data = response.json()
    assert "playwright_mcp" in data
    assert "installed" in data["playwright_mcp"]
    assert "location" in data["playwright_mcp"]
    assert data["playwright_mcp"]["installed"] is False
    assert data["playwright_mcp"]["location"] is None


@pytest.mark.asyncio
async def test_health_playwright_mcp_installed_via_project_mcp(client, tmp_path):
    """GET /api/projects/{id}/health detects Playwright in .mcp.json."""
    root = str(tmp_path)
    _make_manager_json(root)
    _write(os.path.join(root, ".mcp.json"), json.dumps({
        "mcpServers": {"Playwright": {"command": "npx", "args": ["@playwright/mcp@latest"]}},
    }))

    create_resp = await client.post("/api/projects", json={
        "name": "health-pw-installed", "path": root,
    })
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/projects/{project_id}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["playwright_mcp"]["installed"] is True
    assert ".mcp.json" in data["playwright_mcp"]["location"]
