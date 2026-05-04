import pytest

from app.exceptions import AppError
from app.models.project import Project
from app.services.memory_service import MemoryService


@pytest.fixture
def svc(db_session):
    return MemoryService(db_session)


@pytest.mark.asyncio
async def test_create_list_get(db_session, svc, tmp_path):
    db_session.add(Project(id="p1", name="P", path=str(tmp_path)))
    await db_session.flush()
    m = await svc.create(project_id="p1", title="T", description="D")
    assert m.id and m.title == "T"

    listed = await svc.list(project_id="p1")
    assert [x.id for x in listed] == [m.id]

    got = await svc.get(m.id)
    assert got.id == m.id


@pytest.mark.asyncio
async def test_parent_cycle_is_rejected(db_session, svc, tmp_path):
    db_session.add(Project(id="p1", name="P", path=str(tmp_path)))
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    b = await svc.create(project_id="p1", title="B", description="", parent_id=a.id)
    with pytest.raises(AppError):
        await svc.update(a.id, parent_id=b.id)


@pytest.mark.asyncio
async def test_parent_must_be_same_project(db_session, svc, tmp_path):
    p1 = tmp_path / "p1"
    p2 = tmp_path / "p2"
    p1.mkdir(); p2.mkdir()
    db_session.add_all([Project(id="p1", name="P", path=str(p1)), Project(id="p2", name="Q", path=str(p2))])
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    with pytest.raises(AppError):
        await svc.create(project_id="p2", title="B", description="", parent_id=a.id)


@pytest.mark.asyncio
async def test_delete_sets_children_parent_to_null(db_session, svc, tmp_path):
    db_session.add(Project(id="p1", name="P", path=str(tmp_path)))
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    b = await svc.create(project_id="p1", title="B", description="", parent_id=a.id)
    await svc.delete(a.id)
    refreshed = await svc.get(b.id)
    assert refreshed.parent_id is None


@pytest.mark.asyncio
async def test_link_and_unlink(db_session, svc, tmp_path):
    db_session.add(Project(id="p1", name="P", path=str(tmp_path)))
    await db_session.flush()
    a = await svc.create(project_id="p1", title="A", description="")
    b = await svc.create(project_id="p1", title="B", description="")
    link = await svc.link(a.id, b.id, relation="see_also")
    assert link.relation == "see_also"
    related = await svc.get_related(a.id)
    assert [l.to_id for l in related["links_out"]] == [b.id]
    await svc.unlink(a.id, b.id, relation="see_also")
    related = await svc.get_related(a.id)
    assert related["links_out"] == []


@pytest.mark.asyncio
async def test_search_naive(db_session, svc, tmp_path):
    db_session.add(Project(id="p1", name="P", path=str(tmp_path)))
    await db_session.flush()
    await svc.create(project_id="p1", title="Alpha memory", description="about databases")
    await svc.create(project_id="p1", title="Beta", description="about painting")
    hits = await svc.search(project_id="p1", query="databases")
    assert len(hits) == 1
    assert hits[0]["memory"].title == "Alpha memory"
