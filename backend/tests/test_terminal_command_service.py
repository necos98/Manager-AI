import pytest
import pytest_asyncio

from app.models.project import Project
from app.services.terminal_command_service import TerminalCommandService


@pytest_asyncio.fixture
async def project(db_session):
    p = Project(name="Test Project", path="/tmp/test")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def service(db_session):
    return TerminalCommandService(db_session)


@pytest.mark.asyncio
async def test_list_global_empty(service):
    result = await service.list(project_id=None)
    assert result == []


@pytest.mark.asyncio
async def test_create_global_command(service):
    cmd = await service.create("echo hello", 0, project_id=None)
    assert cmd.command == "echo hello"
    assert cmd.sort_order == 0
    assert cmd.project_id is None


@pytest.mark.asyncio
async def test_create_project_command(service, project):
    cmd = await service.create("npm install", 0, project_id=project.id)
    assert cmd.project_id == project.id


@pytest.mark.asyncio
async def test_list_returns_ordered(service):
    await service.create("second", 1, project_id=None)
    await service.create("first", 0, project_id=None)
    result = await service.list(project_id=None)
    assert [c.command for c in result] == ["first", "second"]


@pytest.mark.asyncio
async def test_resolve_uses_project_commands_when_present(service, project):
    await service.create("global cmd", 0, project_id=None)
    await service.create("project cmd", 0, project_id=project.id)
    result = await service.resolve(project.id)
    assert len(result) == 1
    assert result[0].command == "project cmd"


@pytest.mark.asyncio
async def test_resolve_falls_back_to_global(service, project):
    await service.create("global cmd", 0, project_id=None)
    result = await service.resolve(project.id)
    assert len(result) == 1
    assert result[0].command == "global cmd"


@pytest.mark.asyncio
async def test_resolve_returns_empty_when_no_commands(service, project):
    result = await service.resolve(project.id)
    assert result == []


@pytest.mark.asyncio
async def test_update_command(service):
    cmd = await service.create("echo old", 0, project_id=None)
    updated = await service.update(cmd.id, command="echo new")
    assert updated.command == "echo new"


@pytest.mark.asyncio
async def test_update_sort_order(service):
    cmd = await service.create("echo hello", 0, project_id=None)
    updated = await service.update(cmd.id, sort_order=5)
    assert updated.sort_order == 5


@pytest.mark.asyncio
async def test_delete_command(service):
    cmd = await service.create("echo hello", 0, project_id=None)
    await service.delete(cmd.id)
    result = await service.list(project_id=None)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_raises(service):
    with pytest.raises(KeyError):
        await service.delete(9999)


@pytest.mark.asyncio
async def test_reorder(service):
    c1 = await service.create("first", 0, project_id=None)
    c2 = await service.create("second", 1, project_id=None)
    await service.reorder([
        {"id": c1.id, "sort_order": 1},
        {"id": c2.id, "sort_order": 0},
    ])
    result = await service.list(project_id=None)
    assert [c.command for c in result] == ["second", "first"]


@pytest.mark.asyncio
async def test_cascade_delete_removes_commands(db_session, project, service):
    await service.create("project cmd", 0, project_id=project.id)
    await db_session.delete(project)
    await db_session.flush()
    result = await service.list(project_id=project.id)
    assert result == []


@pytest.mark.asyncio
async def test_create_multiline_command(service):
    cmd = await service.create("npm install\nnpm test", 0, project_id=None)
    assert "\n" in cmd.command


@pytest.mark.asyncio
async def test_create_command_with_condition(service):
    cmd = await service.create(
        "npm run build", 0, project_id=None, condition="$issue_status == ACCEPTED"
    )
    assert cmd.condition == "$issue_status == ACCEPTED"
