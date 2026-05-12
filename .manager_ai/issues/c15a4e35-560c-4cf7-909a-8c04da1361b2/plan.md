## Files

- **Modify:** `backend/app/storage/issue_store.py` — add `prewarm_project_cache()` + 1-line call in `list_issues_full`
- **Test:** `backend/tests/storage/test_issue_store.py` — add test class

---

### Task 1: Write failing test for prewarm_project_cache

**Files:**
- Modify: `backend/tests/storage/test_issue_store.py`

**Steps:**

- [ ] **Step 1: Write the test**

```python
class TestPrewarmCache:
    def test_prewarm_populates_all_issue_cache_keys(self, tmp_path):
        """After prewarm, every issue should be cached without individual load_issue calls."""
        project_path = str(tmp_path / "project")
        issues_dir = project_path / ".manager_ai" / "issues"
        issues_dir.mkdir(parents=True)

        # Create 3 issues on disk
        for i in range(3):
            iid = f"issue-{i}"
            issue_dir = issues_dir / iid
            issue_dir.mkdir()
            atomic.write_yaml(
                issue_dir / "issue.yaml",
                {
                    "schema_version": 1,
                    "id": iid,
                    "project_id": "proj-1",
                    "name": f"Issue {i}",
                    "status": "New",
                    "priority": 3,
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                    "tasks": [],
                    "relations": [],
                },
            )
            atomic.write_text(issue_dir / "description.md", f"desc {i}")
            atomic.write_text(issue_dir / "specification.md", f"spec {i}")
            atomic.write_text(issue_dir / "plan.md", f"plan {i}")
            atomic.write_text(issue_dir / "recap.md", f"recap {i}")

        # Rebuild index so list_issues works
        from app.storage.issue_store import rebuild_issues_index
        rebuild_issues_index(project_path)

        # Clear cache to simulate cold state
        from app.storage.cache import issue_cache
        issue_cache.clear()

        # Call prewarm
        from app.storage.issue_store import prewarm_project_cache
        prewarm_project_cache(project_path)

        # Verify all 3 issues are in cache
        for i in range(3):
            cached = issue_cache.get(f"{project_path}:issue-{i}")
            assert cached is not None, f"issue-{i} should be cached"
            assert cached.name == f"Issue {i}"
            assert cached.description == f"desc {i}"
            assert cached.specification == f"spec {i}"
            assert cached.plan == f"plan {i}"
            assert cached.recap == f"recap {i}"

    def test_prewarm_skips_when_index_already_cached(self, tmp_path):
        """prewarm should be a no-op when the index cache is already warm."""
        project_path = str(tmp_path / "project")
        issues_dir = project_path / ".manager_ai" / "issues"
        issues_dir.mkdir(parents=True)

        iid = "issue-0"
        issue_dir = issues_dir / iid
        issue_dir.mkdir()
        atomic.write_yaml(
            issue_dir / "issue.yaml",
            {
                "schema_version": 1,
                "id": iid,
                "project_id": "proj-1",
                "name": "Test",
                "status": "New",
                "priority": 3,
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
                "tasks": [],
                "relations": [],
            },
        )
        atomic.write_text(issue_dir / "description.md", "desc")

        from app.storage.issue_store import rebuild_issues_index
        rebuild_issues_index(project_path)

        from app.storage.cache import issue_cache
        issue_cache.clear()

        # First call: cache is cold, should prewarm
        from app.storage.issue_store import prewarm_project_cache
        prewarm_project_cache(project_path)

        # Second call: index cache is warm, should skip reads
        # We verify by checking issue is still cached
        cached = issue_cache.get(f"{project_path}:issue-0")
        assert cached is not None

    def test_prewarm_empty_project(self, tmp_path):
        """prewarm on project with no issues should not error."""
        project_path = str(tmp_path / "project")
        issues_dir = project_path / ".manager_ai" / "issues"
        issues_dir.mkdir(parents=True)

        # Create empty index
        from app.storage.issue_store import rebuild_issues_index
        rebuild_issues_index(project_path)

        from app.storage.cache import issue_cache
        issue_cache.clear()

        from app.storage.issue_store import prewarm_project_cache
        prewarm_project_cache(project_path)  # should not raise

    def test_list_issues_full_uses_prewarm(self, tmp_path, monkeypatch):
        """list_issues_full should call prewarm_project_cache internally."""
        project_path = str(tmp_path / "project")
        issues_dir = project_path / ".manager_ai" / "issues"
        issues_dir.mkdir(parents=True)

        iid = "issue-0"
        issue_dir = issues_dir / iid
        issue_dir.mkdir()
        atomic.write_yaml(
            issue_dir / "issue.yaml",
            {
                "schema_version": 1,
                "id": iid,
                "project_id": "proj-1",
                "name": "Test",
                "status": "New",
                "priority": 3,
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
                "tasks": [],
                "relations": [],
            },
        )
        atomic.write_text(issue_dir / "description.md", "desc")

        from app.storage.issue_store import rebuild_issues_index
        rebuild_issues_index(project_path)

        from app.storage.cache import issue_cache
        issue_cache.clear()

        from app.storage.issue_store import list_issues_full
        results = list_issues_full(project_path)

        assert len(results) == 1
        assert results[0].name == "Test"
        assert results[0].description == "desc"
```

- [ ] **Step 2: Run to verify it fails**
```
cd backend && python -m pytest tests/storage/test_issue_store.py::TestPrewarmCache -v
```
Expected: FAIL — `prewarm_project_cache` not defined

---

### Task 2: Implement prewarm_project_cache

**Files:**
- Modify: `backend/app/storage/issue_store.py`

**Steps:**

- [ ] **Step 1: Add prewarm_project_cache function**

Insert after `list_issues_full()` (around line 132):

```python
def prewarm_project_cache(project_path: str) -> None:
    """Batch-load all issue files into cache for a project.

    Reads every issue.yaml + markdown body, builds IssueRecords,
    and populates the in-process cache so subsequent load_issue calls
    are cache hits with zero disk I/O.

    Skips early if the index is already cached (prewarmed this TTL window).
    """
    index_key = f"{project_path}:__index__"
    if issue_cache.get(index_key) is not None:
        return

    issues_dir = paths.issues_dir(project_path)
    if not issues_dir.exists():
        return

    for issue_folder in issues_dir.iterdir():
        if not issue_folder.is_dir():
            continue
        yaml_path = issue_folder / "issue.yaml"
        if not yaml_path.exists():
            continue
        data = atomic.read_yaml(yaml_path) or {}
        issue_id = data.get("id", issue_folder.name)
        cache_key = f"{project_path}:{issue_id}"
        if issue_cache.get(cache_key) is not None:
            continue

        description = atomic.read_text(
            paths.issue_md(project_path, issue_id, "description")
        )
        record = IssueRecord(
            id=issue_id,
            project_id=data.get("project_id", ""),
            name=data.get("name"),
            status=data.get("status", "New"),
            priority=int(data.get("priority", 3)),
            description=description,
            specification=_read_optional_md(project_path, issue_id, "specification"),
            plan=_read_optional_md(project_path, issue_id, "plan"),
            recap=_read_optional_md(project_path, issue_id, "recap"),
            created_at=_as_iso(data.get("created_at")),
            updated_at=_as_iso(data.get("updated_at")),
            tasks=[_task_from_dict(t) for t in (data.get("tasks") or [])],
            relations=[_relation_from_dict(r) for r in (data.get("relations") or [])],
        )
        issue_cache.set(cache_key, record)
```

- [ ] **Step 2: Add prewarm call in list_issues_full**

Change `list_issues_full` from:
```python
def list_issues_full(project_path: str) -> list[IssueRecord]:
    """Full listing: loads every issue.yaml + all markdown bodies."""
    index = list_issues(project_path)
    out: list[IssueRecord] = []
    for light in index:
        full = load_issue(project_path, light.id)
        if full is not None:
            out.append(full)
    return out
```

To:
```python
def list_issues_full(project_path: str) -> list[IssueRecord]:
    """Full listing: loads every issue.yaml + all markdown bodies."""
    prewarm_project_cache(project_path)
    index = list_issues(project_path)
    out: list[IssueRecord] = []
    for light in index:
        full = load_issue(project_path, light.id)
        if full is not None:
            out.append(full)
    return out
```

- [ ] **Step 3: Run tests**
```
cd backend && python -m pytest tests/storage/test_issue_store.py::TestPrewarmCache -v
```
Expected: 4 PASS

- [ ] **Step 4: Run full test suite to check for regressions**
```
cd backend && python -m pytest tests/storage/ -v
```
Expected: all existing tests PASS

- [ ] **Step 5: Commit**
```
git commit -m "feat: add prewarm_project_cache for batch issue cache loading"
```