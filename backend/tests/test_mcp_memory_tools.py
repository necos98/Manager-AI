import contextlib
import pytest

import app.mcp.server as mcp_server
from app.models.project import Project


@pytest.mark.asyncio
async def test_memory_write_tools_direct(db_session, monkeypatch, tmp_path):
    @contextlib.asynccontextmanager
    async def _fake():
        yield db_session
    monkeypatch.setattr(mcp_server, "async_session", _fake)

    db_session.add(Project(id="p1", name="P", path=str(tmp_path)))
    await db_session.commit()

    # memory_create is a kept MCP tool
    created = await mcp_server.memory_create(project_id="p1", title="Alpha", description="quick brown fox")
    assert "id" in created and created["title"] == "Alpha"

    # memory_update also kept
    updated = await mcp_server.memory_update(memory_id=created["id"], title="Alpha v2")
    assert updated["title"] == "Alpha v2"

    # Read-side tools (memory_list, memory_search, memory_get) are removed from
    # MCP — LLM uses Read/Grep on .manager_ai/memories/ directly.
    assert not hasattr(mcp_server, "memory_list")
    assert not hasattr(mcp_server, "memory_search")
    assert not hasattr(mcp_server, "memory_get")
    assert not hasattr(mcp_server, "memory_get_related")
    assert not hasattr(mcp_server, "search_project_files")
