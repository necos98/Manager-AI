import pytest
import pytest_asyncio

from app.exceptions import NotFoundError
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


async def test_add_feedback(db_session, issue, project):
    service = IssueService(db_session)
    fb = await service.add_feedback(issue.id, project.id, "The plan needs more detail on tests")
    assert fb.id is not None
    assert fb.issue_id == issue.id
    assert fb.content == "The plan needs more detail on tests"


async def test_list_feedback_ordered(db_session, issue, project):
    service = IssueService(db_session)
    await service.add_feedback(issue.id, project.id, "First comment")
    await db_session.commit()
    await service.add_feedback(issue.id, project.id, "Second comment")
    feedbacks = await service.list_feedback(issue.id, project.id)
    assert len(feedbacks) == 2
    assert feedbacks[0].content == "First comment"
    assert feedbacks[1].content == "Second comment"


async def test_add_feedback_issue_not_found(db_session, project):
    service = IssueService(db_session)
    with pytest.raises(NotFoundError):
        await service.add_feedback("nonexistent-id", project.id, "feedback")
