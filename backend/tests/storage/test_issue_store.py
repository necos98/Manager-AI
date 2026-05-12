from pathlib import Path

import pytest

from app.storage import atomic, issue_store, paths


def _seed_issue(
    project_path: str,
    issue_id: str,
    *,
    name: str | None = "Test issue",
    status: str = "New",
    priority: int = 3,
    description: str = "desc body",
    specification: str | None = None,
    plan: str | None = None,
    recap: str | None = None,
    tasks: list[dict] | None = None,
    relations: list[dict] | None = None,
    feedback: list[dict] | None = None,
    created_at: str = "2026-04-01T10:00:00",
    updated_at: str = "2026-04-01T10:00:00",
    project_id: str = "p1",
) -> None:
    yaml_path = paths.issue_yaml(project_path, issue_id)
    payload: dict = {
        "schema_version": 1,
        "id": issue_id,
        "project_id": project_id,
        "name": name,
        "status": status,
        "priority": priority,
        "created_at": created_at,
        "updated_at": updated_at,
        "tasks": tasks or [],
        "relations": relations or [],
    }
    atomic.write_yaml(yaml_path, payload)
    atomic.write_text(paths.issue_md(project_path, issue_id, "description"), description)
    if specification is not None:
        atomic.write_text(paths.issue_md(project_path, issue_id, "specification"), specification)
    if plan is not None:
        atomic.write_text(paths.issue_md(project_path, issue_id, "plan"), plan)
    if recap is not None:
        atomic.write_text(paths.issue_md(project_path, issue_id, "recap"), recap)
    for fb in feedback or []:
        fb_path = paths.issue_feedback_md(project_path, issue_id, fb["id"])
        frontmatter = (
            "---\n"
            f"id: {fb['id']}\n"
            f"issue_id: {issue_id}\n"
            f"created_at: \"{fb['created_at']}\"\n"
            "---\n"
            f"{fb['content']}"
        )
        atomic.write_text(fb_path, frontmatter)


def _seed_index(project_path: str, entries: list[dict]) -> None:
    atomic.write_yaml(paths.issues_index(project_path), {"schema_version": 1, "issues": entries})


@pytest.fixture
def proj(tmp_path: Path) -> str:
    return str(tmp_path)


def test_load_issue_returns_none_when_missing(proj):
    assert issue_store.load_issue(proj, "missing") is None


def test_issue_exists(proj):
    assert issue_store.issue_exists(proj, "x") is False
    _seed_issue(proj, "x")
    assert issue_store.issue_exists(proj, "x") is True


def test_load_issue_basic_fields(proj):
    _seed_issue(
        proj,
        "i1",
        name="Hello",
        status="Reasoning",
        priority=1,
        description="desc here",
        specification="spec here",
        project_id="proj-A",
    )
    rec = issue_store.load_issue(proj, "i1")
    assert rec is not None
    assert rec.id == "i1"
    assert rec.project_id == "proj-A"
    assert rec.name == "Hello"
    assert rec.status == "Reasoning"
    assert rec.priority == 1
    assert rec.description == "desc here"
    assert rec.specification == "spec here"
    assert rec.plan is None
    assert rec.recap is None


def test_load_issue_all_markdown_fields(proj):
    _seed_issue(
        proj,
        "i2",
        description="d",
        specification="s",
        plan="p",
        recap="r",
    )
    rec = issue_store.load_issue(proj, "i2")
    assert rec.description == "d"
    assert rec.specification == "s"
    assert rec.plan == "p"
    assert rec.recap == "r"


def test_load_issue_tasks_preserved_order(proj):
    tasks = [
        {"id": "t1", "name": "first", "status": "Pending", "order": 0, "created_at": "2026-04-01T10:00:00", "updated_at": "2026-04-01T10:00:00"},
        {"id": "t2", "name": "second", "status": "In Progress", "order": 1, "created_at": "2026-04-01T10:00:00", "updated_at": "2026-04-01T10:00:00"},
    ]
    _seed_issue(proj, "i3", tasks=tasks)
    rec = issue_store.load_issue(proj, "i3")
    assert [t.id for t in rec.tasks] == ["t1", "t2"]
    assert rec.tasks[0].status == "Pending"
    assert rec.tasks[1].status == "In Progress"
    assert rec.tasks[1].order == 1


def test_load_issue_relations(proj):
    rels = [{"target_id": "other", "type": "blocks", "created_at": "2026-04-01T10:00:00"}]
    _seed_issue(proj, "i4", relations=rels)
    rec = issue_store.load_issue(proj, "i4")
    assert len(rec.relations) == 1
    assert rec.relations[0].target_id == "other"
    assert rec.relations[0].type == "blocks"


def test_list_issues_reads_index(proj):
    _seed_index(
        proj,
        [
            {"id": "a", "name": "A", "status": "New", "priority": 3, "created_at": "2026-04-01T10:00:00", "updated_at": "2026-04-01T10:00:00"},
            {"id": "b", "name": None, "status": "Accepted", "priority": 1, "created_at": "2026-04-02T10:00:00", "updated_at": "2026-04-02T10:00:00"},
        ],
    )
    records = issue_store.list_issues(proj)
    assert [r.id for r in records] == ["a", "b"]
    assert records[0].name == "A"
    assert records[1].name is None
    assert records[1].priority == 1


def test_list_issues_empty_when_no_index(proj):
    assert issue_store.list_issues(proj) == []


def test_list_issues_full_loads_every_field(proj):
    _seed_issue(proj, "f1", description="d1", specification="s1")
    _seed_issue(proj, "f2", description="d2", plan="p2")
    _seed_index(
        proj,
        [
            {"id": "f1", "name": "Test issue", "status": "New", "priority": 3, "created_at": "2026-04-01T10:00:00", "updated_at": "2026-04-01T10:00:00"},
            {"id": "f2", "name": "Test issue", "status": "New", "priority": 3, "created_at": "2026-04-01T10:00:00", "updated_at": "2026-04-01T10:00:00"},
        ],
    )
    records = issue_store.list_issues_full(proj)
    by_id = {r.id: r for r in records}
    assert by_id["f1"].specification == "s1"
    assert by_id["f2"].plan == "p2"
    assert by_id["f1"].description == "d1"


def test_load_feedback_sorted_by_created_at(proj):
    feedback = [
        {"id": "fb2", "content": "second", "created_at": "2026-04-02T10:00:00"},
        {"id": "fb1", "content": "first", "created_at": "2026-04-01T10:00:00"},
    ]
    _seed_issue(proj, "i5", feedback=feedback)
    out = issue_store.load_feedback(proj, "i5")
    assert [f.id for f in out] == ["fb1", "fb2"]
    assert out[0].content == "first"


def test_load_feedback_empty_when_no_folder(proj):
    _seed_issue(proj, "i6")
    assert issue_store.load_feedback(proj, "i6") == []


def test_load_feedback_parses_frontmatter_and_body(proj):
    _seed_issue(proj, "i7", feedback=[{"id": "fb", "content": "body text\nline 2", "created_at": "2026-04-01T10:00:00"}])
    out = issue_store.load_feedback(proj, "i7")
    assert out[0].content == "body text\nline 2"
    assert out[0].issue_id == "i7"


class TestPrewarmCache:
    def test_prewarm_populates_all_issue_cache_keys(self, proj):
        _seed_issue(proj, "pw1", name="Issue 1", description="desc 1", specification="spec 1", plan="plan 1", recap="recap 1")
        _seed_issue(proj, "pw2", name="Issue 2", description="desc 2", specification="spec 2")
        _seed_issue(proj, "pw3", name="Issue 3", description="desc 3")

        from app.storage.cache import issue_cache
        issue_cache.clear()

        issue_store.prewarm_project_cache(proj)

        for iid, name, desc in [("pw1", "Issue 1", "desc 1"), ("pw2", "Issue 2", "desc 2"), ("pw3", "Issue 3", "desc 3")]:
            cached = issue_cache.get(f"{proj}:{iid}")
            assert cached is not None, f"{iid} should be cached"
            assert cached.name == name
            assert cached.description == desc

        # pw1 has all optional fields
        cached = issue_cache.get(f"{proj}:pw1")
        assert cached.specification == "spec 1"
        assert cached.plan == "plan 1"
        assert cached.recap == "recap 1"

        # pw2 has spec but no plan/recap
        cached = issue_cache.get(f"{proj}:pw2")
        assert cached.specification == "spec 2"
        assert cached.plan is None
        assert cached.recap is None

    def test_prewarm_skips_when_index_already_cached(self, proj):
        _seed_issue(proj, "pw-skip", name="Test", description="desc")

        from app.storage.cache import issue_cache
        issue_cache.clear()

        # First call populates cache
        issue_store.prewarm_project_cache(proj)
        assert issue_cache.get(f"{proj}:pw-skip") is not None

        # Second call: index cache is warm, should return early
        # Verify issue remains cached (second prewarm is no-op, not clearing)
        issue_store.prewarm_project_cache(proj)
        assert issue_cache.get(f"{proj}:pw-skip") is not None

    def test_prewarm_empty_project(self, proj):
        from app.storage.cache import issue_cache
        issue_cache.clear()

        # No issues seeded — should not raise
        issue_store.prewarm_project_cache(proj)

    def test_list_issues_full_uses_prewarm(self, proj):
        _seed_issue(proj, "pw-full", name="FullTest", description="full desc", specification="full spec")

        from app.storage.cache import issue_cache
        issue_cache.clear()

        results = issue_store.list_issues_full(proj)
        assert len(results) >= 1

        matches = [r for r in results if r.id == "pw-full"]
        assert len(matches) == 1
        assert matches[0].name == "FullTest"
        assert matches[0].description == "full desc"
        assert matches[0].specification == "full spec"

        # Should also be cached after list_issues_full
        cached = issue_cache.get(f"{proj}:pw-full")
        assert cached is not None
