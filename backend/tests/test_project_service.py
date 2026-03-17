import uuid

from app.services.project_service import ProjectService


async def test_create_project(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test", description="A test project")
    assert project.name == "Test"
    assert project.path == "/tmp/test"
    assert project.id is not None


async def test_list_projects(db_session):
    service = ProjectService(db_session)
    await service.create(name="P1", path="/p1", description="")
    await service.create(name="P2", path="/p2", description="")
    projects = await service.list_all()
    assert len(projects) == 2


async def test_get_project(db_session):
    service = ProjectService(db_session)
    created = await service.create(name="Test", path="/tmp", description="desc")
    fetched = await service.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Test"


async def test_get_project_not_found(db_session):
    service = ProjectService(db_session)
    result = await service.get_by_id(uuid.uuid4())
    assert result is None


async def test_update_project(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Old", path="/old", description="")
    updated = await service.update(project.id, name="New")
    assert updated.name == "New"
    assert updated.path == "/old"


async def test_delete_project(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Del", path="/del", description="")
    deleted = await service.delete(project.id)
    assert deleted is True
    assert await service.get_by_id(project.id) is None


async def test_create_project_with_tech_stack(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test", tech_stack="Python, FastAPI")
    assert project.tech_stack == "Python, FastAPI"


async def test_create_project_tech_stack_defaults_to_empty(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test")
    assert project.tech_stack == ""


async def test_update_project_tech_stack(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test", tech_stack="Python")
    updated = await service.update(project.id, tech_stack="Python, FastAPI, React")
    assert updated.tech_stack == "Python, FastAPI, React"
