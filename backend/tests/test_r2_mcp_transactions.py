"""Test that MCP tools handle AppError correctly without explicit rollback."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_set_issue_name_appError_returns_error_dict():
    """AppError in set_issue_name returns error dict, no crash."""
    from app.exceptions import AppError
    from app.mcp.server import set_issue_name

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_service = MagicMock()
    mock_service.set_name = AsyncMock(side_effect=AppError("not found", 404))

    with patch("app.mcp.server.async_session", return_value=mock_session), \
         patch("app.mcp.server.IssueService", return_value=mock_service):
        result = await set_issue_name(
            project_id="proj-1",
            issue_id="issue-1",
            name="New Name",
        )

    assert result == {"error": "not found"}
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_issue_spec_appError_returns_error_dict():
    """AppError in create_issue_spec returns error dict, no crash."""
    from app.exceptions import AppError
    from app.mcp.server import create_issue_spec

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_service = MagicMock()
    mock_service.create_spec = AsyncMock(side_effect=AppError("forbidden", 403))

    with patch("app.mcp.server.async_session", return_value=mock_session), \
         patch("app.mcp.server.IssueService", return_value=mock_service):
        result = await create_issue_spec(
            project_id="proj-1",
            issue_id="issue-1",
            spec="some spec",
        )

    assert result == {"error": "forbidden"}
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_mcp_get_project_context_nonexistent_returns_error():
    """get_project_context con project_id inesistente ritorna {'error': ...}, non lancia eccezioni."""
    from app.exceptions import AppError
    from app.mcp.server import get_project_context

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_project_service = MagicMock()
    mock_project_service.get_by_id = AsyncMock(
        side_effect=AppError("Project not found", 404)
    )

    with patch("app.mcp.server.async_session", return_value=mock_session), \
         patch("app.mcp.server.ProjectService", return_value=mock_project_service):
        result = await get_project_context("00000000-0000-0000-0000-000000000000")

    assert "error" in result
    assert "not found" in result["error"].lower()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_complete_issue_mcp_no_commit_on_app_error():
    """AppError in complete_issue MCP tool: commit non viene chiamato."""
    from app.exceptions import AppError
    from app.mcp.server import complete_issue

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_issue_service = MagicMock()
    mock_issue_service.complete_issue = AsyncMock(
        side_effect=AppError("Cannot complete: issue not in Accepted state", 422)
    )

    with patch("app.mcp.server.async_session", return_value=mock_session), \
         patch("app.mcp.server.IssueService", return_value=mock_issue_service):
        result = await complete_issue(
            project_id="proj-1",
            issue_id="issue-1",
            recap="Done",
        )

    assert result == {"error": "Cannot complete: issue not in Accepted state"}
    mock_session.commit.assert_not_called()
