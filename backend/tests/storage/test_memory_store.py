from pathlib import Path

import pytest

from app.storage import atomic, memory_store, paths
from app.storage.memory_store import MemoryLinkRecord, MemoryRecord


def _new_memory(
    memory_id: str = "m1",
    *,
    title: str = "A memory",
    description: str = "body",
    parent_id: str | None = None,
    links: list[MemoryLinkRecord] | None = None,
    created_at: str = "2026-04-01T10:00:00",
    project_id: str = "p1",
) -> MemoryRecord:
    return MemoryRecord(
        id=memory_id,
        project_id=project_id,
        title=title,
        parent_id=parent_id,
        description=description,
        created_at=created_at,
        updated_at=created_at,
        links=links or [],
    )


@pytest.fixture
def proj(tmp_path: Path) -> str:
    return str(tmp_path)


def test_create_and_load_memory(proj):
    rec = _new_memory("m1", title="Foo", description="bar body")
    memory_store.create_memory(proj, rec)

    loaded = memory_store.load_memory(proj, "m1")
    assert loaded is not None
    assert loaded.id == "m1"
    assert loaded.title == "Foo"
    assert loaded.description == "bar body"
    assert loaded.parent_id is None


def test_load_missing_memory_returns_none(proj):
    assert memory_store.load_memory(proj, "nope") is None


def test_create_memory_writes_frontmatter(proj):
    memory_store.create_memory(proj, _new_memory("mf", title="X", description="hello"))
    content = paths.memory_md(proj, "mf").read_text(encoding="utf-8")
    assert "---" in content
    assert "id: mf" in content
    assert "title: X" in content
    assert "hello" in content


def test_create_memory_registers_in_index(proj):
    memory_store.create_memory(proj, _new_memory("m1", created_at="2026-04-01T10:00:00"))
    memory_store.create_memory(proj, _new_memory("m2", created_at="2026-04-02T10:00:00"))
    index = atomic.read_yaml(paths.memories_index(proj))
    assert [e["id"] for e in index["memories"]] == ["m1", "m2"]


def test_index_sorted_by_created_at_then_id(proj):
    memory_store.create_memory(proj, _new_memory("late", created_at="2026-04-05T10:00:00"))
    memory_store.create_memory(proj, _new_memory("early", created_at="2026-04-01T10:00:00"))
    memory_store.create_memory(proj, _new_memory("mid", created_at="2026-04-03T10:00:00"))
    index = atomic.read_yaml(paths.memories_index(proj))
    assert [e["id"] for e in index["memories"]] == ["early", "mid", "late"]


def test_update_memory(proj):
    memory_store.create_memory(proj, _new_memory("u1", title="Old", description="old body"))
    rec = memory_store.load_memory(proj, "u1")
    rec.title = "New"
    rec.description = "new body"
    memory_store.update_memory(proj, rec)

    loaded = memory_store.load_memory(proj, "u1")
    assert loaded.title == "New"
    assert loaded.description == "new body"


def test_delete_memory_removes_file_and_index(proj):
    memory_store.create_memory(proj, _new_memory("d1"))
    memory_store.create_memory(proj, _new_memory("d2"))
    memory_store.delete_memory(proj, "d1")

    assert not paths.memory_md(proj, "d1").exists()
    index = atomic.read_yaml(paths.memories_index(proj))
    assert [e["id"] for e in index["memories"]] == ["d2"]


def test_delete_memory_detaches_children(proj):
    memory_store.create_memory(proj, _new_memory("p"))
    memory_store.create_memory(proj, _new_memory("c1", parent_id="p"))
    memory_store.create_memory(proj, _new_memory("c2", parent_id="p"))

    memory_store.delete_memory(proj, "p")
    c1 = memory_store.load_memory(proj, "c1")
    c2 = memory_store.load_memory(proj, "c2")
    assert c1.parent_id is None
    assert c2.parent_id is None


def test_delete_memory_removes_inbound_links(proj):
    memory_store.create_memory(proj, _new_memory("a"))
    memory_store.create_memory(proj, _new_memory("b"))
    memory_store.add_link(proj, "a", MemoryLinkRecord(to_id="b", relation="see_also", created_at="2026-04-01T10:00:00"))

    memory_store.delete_memory(proj, "b")
    a = memory_store.load_memory(proj, "a")
    assert a.links == []


def test_list_memories_light(proj):
    memory_store.create_memory(proj, _new_memory("m1", title="one", description="body1", created_at="2026-04-01T10:00:00"))
    memory_store.create_memory(proj, _new_memory("m2", title="two", description="body2", created_at="2026-04-02T10:00:00"))

    listed = memory_store.list_memories(proj)
    assert [m.id for m in listed] == ["m1", "m2"]
    assert listed[0].title == "one"
    # light listing leaves description empty
    assert listed[0].description == ""


def test_list_memories_full_loads_bodies(proj):
    memory_store.create_memory(proj, _new_memory("m1", description="body1"))
    memory_store.create_memory(proj, _new_memory("m2", description="body2"))

    listed = memory_store.list_memories_full(proj)
    by_id = {m.id: m for m in listed}
    assert by_id["m1"].description == "body1"
    assert by_id["m2"].description == "body2"


def test_add_and_remove_link(proj):
    memory_store.create_memory(proj, _new_memory("a"))
    memory_store.create_memory(proj, _new_memory("b"))

    memory_store.add_link(proj, "a", MemoryLinkRecord(to_id="b", relation="see_also", created_at="2026-04-01T10:00:00"))
    a = memory_store.load_memory(proj, "a")
    assert len(a.links) == 1
    assert a.links[0].to_id == "b"

    removed = memory_store.remove_link(proj, "a", "b", "see_also")
    assert removed is True
    a = memory_store.load_memory(proj, "a")
    assert a.links == []


def test_remove_link_missing_returns_false(proj):
    memory_store.create_memory(proj, _new_memory("a"))
    assert memory_store.remove_link(proj, "a", "b", "nope") is False


def test_add_link_deduplicates(proj):
    memory_store.create_memory(proj, _new_memory("a"))
    memory_store.create_memory(proj, _new_memory("b"))
    link = MemoryLinkRecord(to_id="b", relation="see_also", created_at="2026-04-01T10:00:00")
    memory_store.add_link(proj, "a", link)
    memory_store.add_link(proj, "a", link)
    a = memory_store.load_memory(proj, "a")
    assert len(a.links) == 1


def test_links_persisted_in_frontmatter(proj):
    memory_store.create_memory(proj, _new_memory("a"))
    memory_store.create_memory(proj, _new_memory("b"))
    memory_store.add_link(proj, "a", MemoryLinkRecord(to_id="b", relation="see_also", created_at="2026-04-01T10:00:00"))

    # Reload index reflects the link
    index = atomic.read_yaml(paths.memories_index(proj))
    a_entry = next(e for e in index["memories"] if e["id"] == "a")
    assert a_entry["links"] == [{"to_id": "b", "relation": "see_also", "created_at": "2026-04-01T10:00:00"}]


def test_rebuild_memories_index(proj):
    memory_store.create_memory(proj, _new_memory("m1", created_at="2026-04-01T10:00:00"))
    memory_store.create_memory(proj, _new_memory("m2", created_at="2026-04-02T10:00:00"))
    paths.memories_index(proj).unlink()
    memory_store.rebuild_memories_index(proj)
    index = atomic.read_yaml(paths.memories_index(proj))
    assert [e["id"] for e in index["memories"]] == ["m1", "m2"]


def test_parent_preserved(proj):
    memory_store.create_memory(proj, _new_memory("root"))
    memory_store.create_memory(proj, _new_memory("child", parent_id="root"))
    loaded = memory_store.load_memory(proj, "child")
    assert loaded.parent_id == "root"
