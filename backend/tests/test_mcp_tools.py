import asyncio
import uuid
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio

from app.exceptions import NotFoundError
from app.models.issue import IssueStatus
from app.services.project_service import ProjectService
from app.services.issue_service import IssueService
import app.mcp.server as mcp_server
from unittest.mock import patch


@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="MCP Test", path="/tmp/mcp", description="MCP test project", tech_stack="Python, FastAPI")


@pytest.fixture
def issue_service(db_session):
    return IssueService(db_session)


@pytest.fixture
def project_service(db_session):
    return ProjectService(db_session)


@pytest.mark.asyncio
async def test_mcp_autonomous_workflow(issue_service, project):
    """Simulates full autonomous flow: create_spec -> create_plan -> accept -> complete"""
    issue = await issue_service.create(project_id=project.id, description="Feature Z", priority=1)

    # Claude writes spec
    await issue_service.create_spec(issue.id, project.id, "# Spec\n\nBuild feature Z.")
    assert issue.status == IssueStatus.REASONING
    assert issue.specification == "# Spec\n\nBuild feature Z."

    # Claude refines spec after user feedback
    await issue_service.edit_spec(issue.id, project.id, "# Spec v2\n\nBuild feature Z with extra.")
    assert issue.specification == "# Spec v2\n\nBuild feature Z with extra."
    assert issue.status == IssueStatus.REASONING

    # Claude writes plan
    await issue_service.create_plan(issue.id, project.id, "# Plan\n\nStep 1: Do it.")
    assert issue.status == IssueStatus.PLANNED

    # User approves in conversation, Claude accepts
    await issue_service.accept_issue(issue.id, project.id)
    assert issue.status == IssueStatus.ACCEPTED

    # Claude completes
    result = await issue_service.complete_issue(issue.id, project.id, "Done.")
    assert result.status == IssueStatus.FINISHED


@pytest.mark.asyncio
async def test_mcp_complete_flow(issue_service, project):
    """Simulates: spec -> plan -> accept -> complete with recap"""
    issue = await issue_service.create(project_id=project.id, description="Feature Y", priority=1)
    await issue_service.create_spec(issue.id, project.id, "# Spec")
    await issue_service.create_plan(issue.id, project.id, "# Plan")
    await issue_service.accept_issue(issue.id, project.id)
    assert issue.status == IssueStatus.ACCEPTED

    result = await issue_service.complete_issue(issue.id, project.id, "Implemented feature Y successfully")
    assert result.status == IssueStatus.FINISHED
    assert result.recap == "Implemented feature Y successfully"


@pytest.mark.asyncio
async def test_mcp_cancel_flow(issue_service, project):
    """Claude can cancel from any status"""
    issue = await issue_service.create(project_id=project.id, description="Cancel me", priority=1)
    await issue_service.create_spec(issue.id, project.id, "# Spec")
    result = await issue_service.cancel_issue(issue.id, project.id)
    assert result.status == IssueStatus.CANCELED


@pytest.mark.asyncio
async def test_mcp_project_context(project_service, project):
    """get_project_context returns project info"""
    fetched = await project_service.get_by_id(project.id)
    assert fetched.name == "MCP Test"
    assert fetched.path == "/tmp/mcp"
    assert fetched.description == "MCP test project"
    assert fetched.tech_stack == "Python, FastAPI"


@pytest.mark.asyncio
async def test_mcp_get_project_context_includes_tech_stack(db_session, project):
    """get_project_context tool returns tech_stack in its dict"""

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_project_context(str(project.id))

    assert result["tech_stack"] == "Python, FastAPI"
    assert result["name"] == "MCP Test"


@pytest.mark.asyncio
async def test_mcp_get_issue_details_includes_specification(db_session, project):
    """get_issue_details returns specification field"""
    issue_service = IssueService(db_session)
    issue = await issue_service.create(project_id=project.id, description="Spec issue", priority=1)
    await issue_service.create_spec(issue.id, project.id, "# My Spec")
    await db_session.refresh(issue)  # populate server_default fields (created_at, updated_at)

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_issue_details(str(project.id), str(issue.id))

    assert result["specification"] == "# My Spec"
    assert result["status"] == "Reasoning"


@pytest.mark.asyncio
async def test_mcp_issue_project_validation(issue_service, project):
    """All MCP tools must validate project_id ownership"""
    issue = await issue_service.create(project_id=project.id, description="Test", priority=1)
    fake_project_id = uuid.uuid4()

    with pytest.raises(NotFoundError, match="Issue not found"):
        await issue_service.set_name(issue.id, fake_project_id, "Name")

    with pytest.raises(NotFoundError, match="Issue not found"):
        await issue_service.create_spec(issue.id, fake_project_id, "Spec")

    with pytest.raises(NotFoundError, match="Issue not found"):
        await issue_service.complete_issue(issue.id, fake_project_id, "Recap")


@pytest.mark.asyncio
async def test_mcp_create_issue_success(db_session, project):
    """create_issue tool creates issue in New status and returns payload"""

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.create_issue(
            project_id=str(project.id),
            description="fix the thing",
            priority=2,
        )

    assert "error" not in result
    assert result["project_id"] == project.id
    assert result["description"] == "fix the thing"
    assert result["priority"] == 2
    assert result["status"] == "New"
    assert result["id"]


@pytest.mark.asyncio
async def test_mcp_create_issue_default_priority(db_session, project):
    """create_issue defaults priority to 3 when omitted"""

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.create_issue(
            project_id=str(project.id),
            description="default-priority issue",
        )

    assert result["priority"] == 3
    assert result["status"] == "New"


@pytest.mark.asyncio
async def test_mcp_create_issue_rejects_blank_description():
    """Blank description is rejected without touching the DB"""
    result = await mcp_server.create_issue(project_id="anything", description="   ")
    assert result == {"error": "Description cannot be blank"}


@pytest.mark.asyncio
async def test_mcp_create_issue_rejects_bad_priority(db_session, project):
    """Priority outside [1,5] is rejected"""

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        low = await mcp_server.create_issue(project_id=str(project.id), description="x", priority=0)
        high = await mcp_server.create_issue(project_id=str(project.id), description="x", priority=9)

    assert low == {"error": "Priority must be between 1 and 5"}
    assert high == {"error": "Priority must be between 1 and 5"}

