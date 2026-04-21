import contextlib
import pytest

import app.mcp.server as mcp_server
from app.models.project import Project


@pytest.mark.asyncio
async def test_memory_tools_direct(db_session, monkeypatch):
    @contextlib.asynccontextmanager
    async def _fake():
        yield db_session
    monkeypatch.setattr(mcp_server, "async_session", _fake)

    db_session.add(Project(id="p1", name="P", path="/tmp/p"))
    await db_session.commit()

    created = await mcp_server.memory_create(project_id="p1", title="Alpha", description="quick brown fox")
    assert "id" in created and created["title"] == "Alpha"

    listed = await mcp_server.memory_list(project_id="p1")
    assert any(m["id"] == created["id"] for m in listed["memories"])

    hits = await mcp_server.memory_search(project_id="p1", query="brown")
    assert len(hits["results"]) == 1
