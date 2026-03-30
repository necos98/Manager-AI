import pytest
import pytest_asyncio

from app.models.project import Project
from app.models.project_variable import ProjectVariable
from app.services.project_variable_service import ProjectVariableService


@pytest_asyncio.fixture
async def project(db_session):
    p = Project(name="Test", path="/tmp/t")
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture
async def service(db_session):
    return ProjectVariableService(db_session)


@pytest.mark.asyncio
async def test_list_empty(service, project):
    result = await service.list(project.id)
    assert result == []


@pytest.mark.asyncio
async def test_create_variable(service, project):
    v = await service.create(project.id, name="DB_URL", value="sqlite:///test.db")
    assert v.name == "DB_URL"
    assert v.value == "sqlite:///test.db"
    assert v.is_secret is False
    assert v.project_id == project.id


@pytest.mark.asyncio
async def test_create_secret_variable(service, project):
    v = await service.create(project.id, name="API_KEY", value="secret123", is_secret=True)
    assert v.is_secret is True


@pytest.mark.asyncio
async def test_create_duplicate_name_raises(service, project):
    await service.create(project.id, name="VAR", value="a")
    with pytest.raises(ValueError, match="already exists"):
        await service.create(project.id, name="VAR", value="b")


@pytest.mark.asyncio
async def test_update_variable(service, project):
    v = await service.create(project.id, name="VAR", value="old")
    updated = await service.update(v.id, value="new")
    assert updated.value == "new"


@pytest.mark.asyncio
async def test_delete_variable(service, project):
    v = await service.create(project.id, name="VAR", value="x")
    await service.delete(v.id)
    result = await service.list(project.id)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_raises(service, project):
    with pytest.raises(KeyError):
        await service.delete(9999)


@pytest.mark.asyncio
async def test_cascade_delete(db_session, project, service):
    await service.create(project.id, name="VAR", value="x")
    await db_session.delete(project)
    await db_session.flush()
    result = await service.list(project.id)
    assert result == []
