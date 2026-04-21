import pytest
from sqlalchemy import select

from app.models.memory import Memory, MemoryLink
from app.models.project import Project


@pytest.mark.asyncio
async def test_memory_and_link_round_trip(db_session):
    proj = Project(id="p1", name="P", path="/tmp/p")
    db_session.add(proj)
    await db_session.flush()

    parent = Memory(id="m1", project_id="p1", title="Parent", description="root")
    child = Memory(id="m2", project_id="p1", title="Child", description="leaf", parent_id="m1")
    db_session.add_all([parent, child])
    await db_session.flush()

    link = MemoryLink(from_id="m1", to_id="m2", relation="see_also")
    db_session.add(link)
    await db_session.flush()

    rows = (await db_session.execute(select(Memory).order_by(Memory.id))).scalars().all()
    assert [m.id for m in rows] == ["m1", "m2"]
    assert rows[1].parent_id == "m1"

    link_rows = (await db_session.execute(select(MemoryLink))).scalars().all()
    assert len(link_rows) == 1
    assert link_rows[0].relation == "see_also"
