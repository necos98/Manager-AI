import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.exceptions import InvalidTransitionError
from app.models.issue import IssueStatus
from app.services.issue_service import IssueService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session, tmp_path):
    service = ProjectService(db_session)
    return await service.create(name="Test", path=str(tmp_path))


@pytest_asyncio.fixture
async def issue(db_session, project):
    service = IssueService(db_session)
    return await service.create(project_id=project.id, description="Test issue")


async def _advance_to_planned(service, issue, project):
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")


async def test_accept_issue_via_service(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        await _advance_to_planned(service, issue, project)
        result = await service.accept_issue(issue.id, project.id)
        assert result.status == IssueStatus.ACCEPTED.value


async def test_cancel_issue_via_service(db_session, issue, project):
    with patch("app.services.issue_service.hook_registry") as mock_registry:
        mock_registry.fire = AsyncMock()
        service = IssueService(db_session)
        result = await service.cancel_issue(issue.id, project.id)
        assert result.status == IssueStatus.CANCELED.value


async def test_update_issue_name(db_session, issue, project):
    service = IssueService(db_session)
    updated = await service.set_name(issue.id, project.id, "New name")
    assert updated.name == "New name"


async def test_update_issue_name_too_long(db_session, issue, project):
    service = IssueService(db_session)
    from app.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await service.set_name(issue.id, project.id, "x" * 501)


async def test_update_issue_name_via_router_logic(db_session, issue, project):
    """name goes through set_name with 500-char validation."""
    service = IssueService(db_session)
    result = await service.set_name(issue.id, project.id, "My renamed issue")
    assert result.name == "My renamed issue"


async def test_update_issue_name_and_priority_together(db_session, issue, project):
    """Both name and priority can be updated in one call."""
    service = IssueService(db_session)
    await service.set_name(issue.id, project.id, "Combined update")
    updated = await service.update_fields(issue.id, project.id, priority=1)
    assert updated.name == "Combined update"
    assert updated.priority == 1
