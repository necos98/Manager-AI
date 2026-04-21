import pytest

from app.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_list_all_excludes_archived_by_default(db_session):
    svc = ProjectService(db_session)
    active = await svc.create(name="Active", path="/a")
    archived = await svc.create(name="Archived", path="/b")
    await svc.archive(archived.id)
    await db_session.flush()

    projects = await svc.list_all()

    ids = [p.id for p in projects]
    assert active.id in ids
    assert archived.id not in ids


@pytest.mark.asyncio
async def test_list_all_archived_true_returns_only_archived(db_session):
    svc = ProjectService(db_session)
    await svc.create(name="Active", path="/a")
    archived = await svc.create(name="Archived", path="/b")
    await svc.archive(archived.id)
    await db_session.flush()

    projects = await svc.list_all(archived=True)

    assert [p.id for p in projects] == [archived.id]


@pytest.mark.asyncio
async def test_list_all_orders_alphabetically_case_insensitive(db_session):
    svc = ProjectService(db_session)
    await svc.create(name="banana", path="/b")
    await svc.create(name="Apple", path="/a")
    await svc.create(name="cherry", path="/c")

    projects = await svc.list_all()

    assert [p.name for p in projects] == ["Apple", "banana", "cherry"]


@pytest.mark.asyncio
async def test_archive_sets_timestamp(db_session):
    svc = ProjectService(db_session)
    project = await svc.create(name="P", path="/p")
    await db_session.flush()

    await svc.archive(project.id)
    await db_session.flush()

    refreshed = await svc.get_by_id(project.id)
    assert refreshed.archived_at is not None


@pytest.mark.asyncio
async def test_unarchive_clears_timestamp(db_session):
    svc = ProjectService(db_session)
    project = await svc.create(name="P", path="/p")
    await svc.archive(project.id)
    await db_session.flush()

    await svc.unarchive(project.id)
    await db_session.flush()

    refreshed = await svc.get_by_id(project.id)
    assert refreshed.archived_at is None


@pytest.mark.asyncio
async def test_archive_is_idempotent(db_session):
    svc = ProjectService(db_session)
    project = await svc.create(name="P", path="/p")
    await svc.archive(project.id)
    await db_session.flush()

    first = (await svc.get_by_id(project.id)).archived_at

    await svc.archive(project.id)
    await db_session.flush()

    second = (await svc.get_by_id(project.id)).archived_at
    assert first == second
