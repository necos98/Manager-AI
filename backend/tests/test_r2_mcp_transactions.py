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
