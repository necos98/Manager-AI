# backend/tests/test_issue_service_hooks.py
"""Test that service methods fire hooks on state transitions."""
from unittest.mock import AsyncMock, patch

import pytest_asyncio

from app.models.issue import IssueStatus
from app.hooks.registry import HookEvent
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test", path="/tmp/test", description="Test")


@patch("app.services.issue_service.hook_registry")
async def test_complete_issue_fires_hook(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Test", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    # Reset mock after accept_issue (which also fires a hook)
    mock_registry.fire.reset_mock()
    await service.complete_issue(issue.id, project.id, "Done")
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_COMPLETED


@patch("app.services.issue_service.hook_registry")
async def test_accept_issue_fires_hook(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Accept me", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_ACCEPTED


@patch("app.services.issue_service.hook_registry")
async def test_cancel_issue_fires_hook(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Cancel me", priority=1)
    await service.cancel_issue(issue.id, project.id)
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_CANCELLED
