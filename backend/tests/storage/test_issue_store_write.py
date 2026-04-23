from pathlib import Path

import pytest

from app.storage import atomic, issue_store, paths
from app.storage.issue_store import (
    FeedbackRecord,
    IssueRecord,
    RelationRecord,
    TaskRecord,
)


def _new_record(
    issue_id: str = "i1",
    *,
    name: str | None = "Test",
    status: str = "New",
    priority: int = 3,
    description: str = "body",
    specification: str | None = None,
    plan: str | None = None,
    recap: str | None = None,
    tasks: list[TaskRecord] | None = None,
    relations: list[RelationRecord] | None = None,
    created_at: str = "2026-04-01T10:00:00",
    project_id: str = "p1",
) -> IssueRecord:
    return IssueRecord(
        id=issue_id,
        project_id=project_id,
        name=name,
        status=status,
        priority=priority,
        description=description,
        specification=specification,
        plan=plan,
        recap=recap,
        created_at=created_at,
        updated_at=created_at,
        tasks=tasks or [],
        relations=relations or [],
    )


@pytest.fixture
def proj(tmp_path: Path) -> str:
    return str(tmp_path)


def test_create_issue_writes_yaml_and_description(proj):
    rec = _new_record("a1", description="desc for a1")
    issue_store.create_issue(proj, rec)

    assert paths.issue_yaml(proj, "a1").exists()
    assert paths.issue_md(proj, "a1", "description").exists()
    assert paths.issues_index(proj).exists()

    loaded = issue_store.load_issue(proj, "a1")
    assert loaded is not None
    assert loaded.id == "a1"
    assert loaded.description == "desc for a1"


def test_create_issue_writes_optional_md_when_present(proj):
    rec = _new_record("a2", description="d", specification="s", plan="p", recap="r")
    issue_store.create_issue(proj, rec)
    loaded = issue_store.load_issue(proj, "a2")
    assert loaded.specification == "s"
    assert loaded.plan == "p"
    assert loaded.recap == "r"


def test_create_issue_skips_missing_optional_md(proj):
    rec = _new_record("a3", specification=None, plan=None, recap=None)
    issue_store.create_issue(proj, rec)
    assert not paths.issue_md(proj, "a3", "specification").exists()
    assert not paths.issue_md(proj, "a3", "plan").exists()
    assert not paths.issue_md(proj, "a3", "recap").exists()


def test_create_issue_registers_in_root_index(proj):
    issue_store.create_issue(proj, _new_record("a1"))
    issue_store.create_issue(proj, _new_record("a2", created_at="2026-04-02T10:00:00"))
    index_data = atomic.read_yaml(paths.issues_index(proj))
    ids = [e["id"] for e in index_data["issues"]]
    assert ids == ["a1", "a2"]


def test_index_sorted_by_created_at_then_id(proj):
    issue_store.create_issue(proj, _new_record("later", created_at="2026-04-05T10:00:00"))
    issue_store.create_issue(proj, _new_record("earlier", created_at="2026-04-01T10:00:00"))
    issue_store.create_issue(proj, _new_record("middle", created_at="2026-04-03T10:00:00"))
    index_data = atomic.read_yaml(paths.issues_index(proj))
    assert [e["id"] for e in index_data["issues"]] == ["earlier", "middle", "later"]


def test_update_issue_rewrites_markdown_fields(proj):
    rec = _new_record("u1", description="old", specification="old-spec")
    issue_store.create_issue(proj, rec)

    rec.description = "new"
    rec.specification = "new-spec"
    rec.plan = "new-plan"
    issue_store.update_issue(proj, rec)

    loaded = issue_store.load_issue(proj, "u1")
    assert loaded.description == "new"
    assert loaded.specification == "new-spec"
    assert loaded.plan == "new-plan"


def test_update_issue_removes_optional_md_set_to_none(proj):
    rec = _new_record("u2", specification="start", plan="start")
    issue_store.create_issue(proj, rec)
    assert paths.issue_md(proj, "u2", "specification").exists()

    rec.specification = None
    rec.plan = None
    issue_store.update_issue(proj, rec)

    assert not paths.issue_md(proj, "u2", "specification").exists()
    assert not paths.issue_md(proj, "u2", "plan").exists()


def test_delete_issue_removes_folder_and_index_entry(proj):
    issue_store.create_issue(proj, _new_record("d1"))
    issue_store.create_issue(proj, _new_record("d2"))
    issue_store.delete_issue(proj, "d1")

    assert not paths.issue_dir(proj, "d1").exists()
    index_data = atomic.read_yaml(paths.issues_index(proj))
    assert [e["id"] for e in index_data["issues"]] == ["d2"]


def test_delete_issue_missing_is_noop(proj):
    issue_store.delete_issue(proj, "nope")  # no error


def test_upsert_task_adds_and_updates(proj):
    issue_store.create_issue(proj, _new_record("tk1"))
    t = TaskRecord(id="t1", name="first", status="Pending", order=0, created_at="2026-04-01T10:00:00", updated_at="2026-04-01T10:00:00")
    issue_store.upsert_task(proj, "tk1", t)
    loaded = issue_store.load_issue(proj, "tk1")
    assert len(loaded.tasks) == 1
    assert loaded.tasks[0].name == "first"

    t2 = TaskRecord(id="t1", name="first-renamed", status="In Progress", order=0, created_at="2026-04-01T10:00:00", updated_at="2026-04-02T10:00:00")
    issue_store.upsert_task(proj, "tk1", t2)
    loaded = issue_store.load_issue(proj, "tk1")
    assert len(loaded.tasks) == 1
    assert loaded.tasks[0].name == "first-renamed"
    assert loaded.tasks[0].status == "In Progress"


def test_remove_task(proj):
    issue_store.create_issue(
        proj,
        _new_record(
            "tk2",
            tasks=[
                TaskRecord(id="a", name="A", status="Pending", order=0, created_at="2026-04-01T10:00:00", updated_at="2026-04-01T10:00:00"),
                TaskRecord(id="b", name="B", status="Pending", order=1, created_at="2026-04-01T10:00:00", updated_at="2026-04-01T10:00:00"),
            ],
        ),
    )
    issue_store.remove_task(proj, "tk2", "a")
    loaded = issue_store.load_issue(proj, "tk2")
    assert [t.id for t in loaded.tasks] == ["b"]


def test_replace_tasks(proj):
    issue_store.create_issue(proj, _new_record("tk3"))
    issue_store.replace_tasks(
        proj,
        "tk3",
        [
            TaskRecord(id="x", name="X", status="Pending", order=0, created_at="2026-04-01T10:00:00", updated_at="2026-04-01T10:00:00"),
            TaskRecord(id="y", name="Y", status="Pending", order=1, created_at="2026-04-01T10:00:00", updated_at="2026-04-01T10:00:00"),
        ],
    )
    loaded = issue_store.load_issue(proj, "tk3")
    assert [t.id for t in loaded.tasks] == ["x", "y"]

    issue_store.replace_tasks(proj, "tk3", [])
    loaded = issue_store.load_issue(proj, "tk3")
    assert loaded.tasks == []


def test_find_task_returns_issue_and_task(proj):
    issue_store.create_issue(proj, _new_record("ft1"))
    issue_store.create_issue(proj, _new_record("ft2"))
    t = TaskRecord(id="target", name="T", status="Pending", order=0, created_at="2026-04-01T10:00:00", updated_at="2026-04-01T10:00:00")
    issue_store.upsert_task(proj, "ft2", t)

    found = issue_store.find_task(proj, "target")
    assert found is not None
    issue, task = found
    assert issue.id == "ft2"
    assert task.id == "target"

    assert issue_store.find_task(proj, "does-not-exist") is None


def test_add_feedback(proj):
    issue_store.create_issue(proj, _new_record("fb1"))
    fb = FeedbackRecord(id="f1", issue_id="fb1", content="hello", created_at="2026-04-01T10:00:00")
    issue_store.add_feedback(proj, "fb1", fb)
    loaded = issue_store.load_feedback(proj, "fb1")
    assert len(loaded) == 1
    assert loaded[0].content == "hello"
    assert loaded[0].id == "f1"


def test_upsert_relation_writes_on_source(proj):
    issue_store.create_issue(proj, _new_record("src"))
    issue_store.create_issue(proj, _new_record("tgt"))
    rel = RelationRecord(target_id="tgt", type="blocks", created_at="2026-04-01T10:00:00")
    issue_store.upsert_relation(proj, "src", rel)
    loaded = issue_store.load_issue(proj, "src")
    assert len(loaded.relations) == 1
    assert loaded.relations[0].target_id == "tgt"


def test_upsert_relation_deduplicates(proj):
    issue_store.create_issue(proj, _new_record("s1"))
    rel = RelationRecord(target_id="t1", type="blocks", created_at="2026-04-01T10:00:00")
    issue_store.upsert_relation(proj, "s1", rel)
    issue_store.upsert_relation(proj, "s1", rel)
    loaded = issue_store.load_issue(proj, "s1")
    assert len(loaded.relations) == 1


def test_remove_relation(proj):
    issue_store.create_issue(proj, _new_record("s2"))
    issue_store.upsert_relation(proj, "s2", RelationRecord(target_id="t", type="blocks", created_at="2026-04-01T10:00:00"))
    issue_store.upsert_relation(proj, "s2", RelationRecord(target_id="u", type="related", created_at="2026-04-01T10:00:00"))
    issue_store.remove_relation(proj, "s2", "t", "blocks")
    loaded = issue_store.load_issue(proj, "s2")
    assert [(r.target_id, r.type) for r in loaded.relations] == [("u", "related")]


def test_rebuild_issues_index_reflects_filesystem(proj):
    issue_store.create_issue(proj, _new_record("r1", created_at="2026-04-01T10:00:00"))
    issue_store.create_issue(proj, _new_record("r2", created_at="2026-04-02T10:00:00"))
    # Tamper: delete index on disk
    paths.issues_index(proj).unlink()
    issue_store.rebuild_issues_index(proj)

    index_data = atomic.read_yaml(paths.issues_index(proj))
    assert [e["id"] for e in index_data["issues"]] == ["r1", "r2"]
