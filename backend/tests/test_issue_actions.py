import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.exceptions import InvalidTransitionError
from app.models.issue import IssueStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="Test", path="/tmp/test")


@pytest_asyncio.fixture
async def issue(db_session, project):
    service = IssueService(db_session)
    return await service.create(project_id=project.id, description="Test issue")


async def test_start_analysis_fires_hook(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        result = await service.start_analysis(issue.id, project.id)
        assert result.id == issue.id
        assert result.status == IssueStatus.NEW  # state unchanged
        mock_registry.fire.assert_called_once()
        call_args = mock_registry.fire.call_args
        from app.hooks.registry import HookEvent, HookContext
        assert call_args[0][0] == HookEvent.ISSUE_ANALYSIS_STARTED
        context: HookContext = call_args[0][1]
        assert context.metadata["issue_description"] == issue.description
        assert context.metadata["project_path"] == project.path


async def test_start_analysis_requires_new_status(db_session, issue, project):
    service = IssueService(db_session)
    issue.status = IssueStatus.REASONING
    await db_session.flush()
    with pytest.raises(InvalidTransitionError):
        await service.start_analysis(issue.id, project.id)


async def test_accept_issue_via_service(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        issue.status = IssueStatus.PLANNED
        await db_session.flush()
        result = await service.accept_issue(issue.id, project.id)
        assert result.status == IssueStatus.ACCEPTED


async def test_cancel_issue_via_service(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        result = await service.cancel_issue(issue.id, project.id)
        assert result.status == IssueStatus.CANCELED


async def test_update_issue_name(db_session, issue, project):
    service = IssueService(db_session)
    updated = await service.set_name(issue.id, project.id, "New name")
    assert updated.name == "New name"


async def test_update_issue_name_too_long(db_session, issue, project):
    service = IssueService(db_session)
    from app.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await service.set_name(issue.id, project.id, "x" * 501)
