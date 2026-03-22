from unittest.mock import MagicMock, AsyncMock, patch

import pytest


@pytest.fixture
def mock_rag_service():
    svc = MagicMock()
    svc.search = AsyncMock(return_value=[
        {"chunk_id": "c1", "title": "test.txt", "source_type": "file", "score": 0.85, "preview": "hello"}
    ])
    svc.get_chunk_details = AsyncMock(return_value={
        "chunk_id": "c1", "chunk_text": "full text", "source_type": "file",
        "source_id": "f1", "title": "test.txt", "chunk_index": 0,
        "total_chunks": 1, "metadata": {}, "adjacent_chunks": {"previous": None, "next": None},
    })
    return svc


async def test_search_project_context(mock_rag_service):
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import search_project_context
        result = await search_project_context(project_id="p1", query="hello")
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["chunk_id"] == "c1"
        mock_rag_service.search.assert_called_once_with(
            query="hello", project_id="p1", source_type=None, limit=5
        )


async def test_search_project_context_with_filters(mock_rag_service):
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import search_project_context
        await search_project_context(project_id="p1", query="hello", source_type="file", limit=3)
        mock_rag_service.search.assert_called_once_with(
            query="hello", project_id="p1", source_type="file", limit=3
        )


async def test_get_context_chunk_details(mock_rag_service):
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import get_context_chunk_details
        result = await get_context_chunk_details(project_id="p1", chunk_id="c1")
        assert result["chunk_id"] == "c1"
        assert result["chunk_text"] == "full text"


async def test_get_context_chunk_details_not_found(mock_rag_service):
    mock_rag_service.get_chunk_details = AsyncMock(return_value=None)
    with patch("app.mcp.server.get_rag_service", return_value=mock_rag_service):
        from app.mcp.server import get_context_chunk_details
        result = await get_context_chunk_details(project_id="p1", chunk_id="nonexistent")
        assert "error" in result
