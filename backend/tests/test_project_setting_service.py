import pytest_asyncio
from app.services.project_setting_service import ProjectSettingService
from app.services.project_service import ProjectService


@pytest_asyncio.fixture
async def project(db_session):
    return await ProjectService(db_session).create(name="Proj", path="/tmp/p", description="")


async def test_get_returns_default_when_not_set(db_session, project):
    svc = ProjectSettingService(db_session)
    value = await svc.get(project.id, "auto_workflow_enabled", default="false")
    assert value == "false"


async def test_set_and_get(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await db_session.commit()
    value = await svc.get(project.id, "auto_workflow_enabled", default="false")
    assert value == "true"


async def test_get_all_for_project(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await svc.set(project.id, "auto_implementation_enabled", "false")
    await db_session.commit()
    all_settings = await svc.get_all_for_project(project.id)
    assert all_settings["auto_workflow_enabled"] == "true"
    assert all_settings["auto_implementation_enabled"] == "false"


async def test_set_overwrites_existing(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await db_session.commit()
    await svc.set(project.id, "auto_workflow_enabled", "false")
    await db_session.commit()
    value = await svc.get(project.id, "auto_workflow_enabled", default="true")
    assert value == "false"


async def test_delete_setting(db_session, project):
    svc = ProjectSettingService(db_session)
    await svc.set(project.id, "auto_workflow_enabled", "true")
    await db_session.commit()
    await svc.delete(project.id, "auto_workflow_enabled")
    await db_session.commit()
    value = await svc.get(project.id, "auto_workflow_enabled", default="false")
    assert value == "false"
