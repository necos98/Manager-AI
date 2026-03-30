import pytest_asyncio
from unittest.mock import AsyncMock, patch
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(name="Q", path="/tmp/q", description="")


@patch("app.services.issue_service.hook_registry")
async def test_get_next_returns_accepted_before_new(mock_reg, db_session, project):
    mock_reg.fire = AsyncMock()
    svc = IssueService(db_session)
    new_issue = await svc.create(project_id=project.id, description="New issue", priority=1)
    accepted_issue = await svc.create(project_id=project.id, description="Accepted issue", priority=2)
    await svc.create_spec(accepted_issue.id, project.id, "# Spec")
    await svc.create_plan(accepted_issue.id, project.id, "# Plan")
    await svc.accept_issue(accepted_issue.id, project.id)
    await db_session.commit()
    next_issue = await svc.get_next_issue(project.id)
    assert next_issue is not None
    assert next_issue.id == accepted_issue.id


@patch("app.services.issue_service.hook_registry")
async def test_get_next_returns_highest_priority_new(mock_reg, db_session, project):
    mock_reg.fire = AsyncMock()
    svc = IssueService(db_session)
    low = await svc.create(project_id=project.id, description="Low prio", priority=3)
    high = await svc.create(project_id=project.id, description="High prio", priority=1)
    await db_session.commit()
    next_issue = await svc.get_next_issue(project.id)
    assert next_issue is not None
    assert next_issue.id == high.id


@patch("app.services.issue_service.hook_registry")
async def test_get_next_returns_none_when_no_workable(mock_reg, db_session, project):
    mock_reg.fire = AsyncMock()
    svc = IssueService(db_session)
    issue = await svc.create(project_id=project.id, description="Issue", priority=1)
    await svc.create_spec(issue.id, project.id, "# Spec")  # REASONING — not workable
    await db_session.commit()
    next_issue = await svc.get_next_issue(project.id)
    assert next_issue is None
