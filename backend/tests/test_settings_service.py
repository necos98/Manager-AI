import pytest
import pytest_asyncio

from app.services.settings_service import SettingsService


@pytest_asyncio.fixture
async def service(db_session):
    return SettingsService(db_session)


async def test_get_returns_default_when_not_customized(service):
    value = await service.get("server.name")
    assert value == "Manager AI"


async def test_get_returns_db_value_when_customized(db_session, service):
    await service.set("server.name", "My Custom Name")
    await db_session.commit()
    value = await service.get("server.name")
    assert value == "My Custom Name"


async def test_get_raises_keyerror_for_unknown_key(service):
    with pytest.raises(KeyError):
        await service.get("nonexistent.key")


async def test_get_all_returns_all_defaults_not_customized(service):
    settings = await service.get_all()
    assert len(settings) == 39
    keys = [s.key for s in settings]
    assert "server.name" in keys
    assert "tool.create_issue_spec.description" in keys
    assert "tool.create_plan_tasks.description" in keys
    assert all(not s.is_customized for s in settings)
    for s in settings:
        assert s.value == s.default


async def test_get_all_marks_customized_correctly(db_session, service):
    await service.set("server.name", "Custom")
    await db_session.commit()
    settings = await service.get_all()
    server_name = next(s for s in settings if s.key == "server.name")
    assert server_name.is_customized is True
    assert server_name.value == "Custom"
    assert server_name.default == "Manager AI"


async def test_get_all_ignores_db_keys_not_in_json(db_session, service):
    from app.models.setting import Setting
    stale = Setting(key="obsolete.key", value="old")
    db_session.add(stale)
    await db_session.flush()
    settings = await service.get_all()
    keys = [s.key for s in settings]
    assert "obsolete.key" not in keys


async def test_set_creates_new_row(db_session, service):
    setting = await service.set("server.name", "New Name")
    await db_session.commit()
    assert setting.key == "server.name"
    assert setting.value == "New Name"


async def test_set_updates_existing_row(db_session, service):
    await service.set("server.name", "First")
    await db_session.commit()
    await service.set("server.name", "Second")
    await db_session.commit()
    value = await service.get("server.name")
    assert value == "Second"


async def test_set_raises_keyerror_for_unknown_key(service):
    with pytest.raises(KeyError):
        await service.set("nonexistent.key", "value")


async def test_reset_removes_customization(db_session, service):
    await service.set("server.name", "Custom")
    await db_session.commit()
    await service.reset("server.name")
    await db_session.commit()
    value = await service.get("server.name")
    assert value == "Manager AI"


async def test_reset_is_idempotent_when_not_customized(service):
    await service.reset("server.name")


async def test_reset_all_clears_all_customizations(db_session, service):
    await service.set("server.name", "Custom 1")
    await service.set("tool.get_issue_status.description", "Custom 2")
    await db_session.commit()
    await service.reset_all()
    await db_session.commit()
    settings = await service.get_all()
    assert all(not s.is_customized for s in settings)


async def test_get_one_returns_correct_out(db_session, service):
    out = await service.get_one("server.name")
    assert out.key == "server.name"
    assert out.value == "Manager AI"
    assert out.default == "Manager AI"
    assert out.is_customized is False

    await service.set("server.name", "Custom")
    await db_session.commit()
    out = await service.get_one("server.name")
    assert out.value == "Custom"
    assert out.is_customized is True
