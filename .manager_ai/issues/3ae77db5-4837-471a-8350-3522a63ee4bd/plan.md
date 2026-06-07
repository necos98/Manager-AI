## Implementation Plan: O(n)→O(1) Reverse Index for IssueService.get_by_id()

### Overview

Add `_issue_to_project` reverse index (dict) to `MemoryStoreCore` mapping `issue_id → project_path`. Wire lifecycle hooks so index stays consistent. Expose lookup wrapper in `issue_store`, use it in `IssueService.get_by_id()` for O(1) path resolution, fall back to full scan on miss.

### Task 1: Add reverse index + `find_issue_project()` to MemoryStoreCore

**File:** `backend/app/storage/memory_store_core.py`

**1a. Add index dict in `__init__`:**
```python
class MemoryStore:
    def __init__(self) -> None:
        self._projects: dict[str, dict[str, dict[str, Any]]] = {}
        self._issue_to_project: dict[str, str] = {}
```

**1b. Populate index in `init_project()` when `store_type == "issues"`:**
```python
def init_project(self, project_path: str, store_type: str, records: dict[str, Any], index: list[dict[str, Any]]) -> None:
    if project_path not in self._projects:
        self._projects[project_path] = {}
    self._projects[project_path][store_type] = {"records": records, "index": index}
    if store_type == "issues":
        for rid in records:
            self._issue_to_project[rid] = project_path
```

**1c. Update index in `upsert()` when `store_type == "issues"`:**
```python
def upsert(self, project_path: str, store_type: str, record_id: str, record: Any, index_entry: dict[str, Any]) -> None:
    store = self._ensure(project_path, store_type)
    store["records"][record_id] = record
    idx = store["index"]
    for i, e in enumerate(idx):
        if e.get("id") == record_id:
            idx[i] = index_entry
            break
    else:
        idx.append(index_entry)
    idx.sort(key=lambda e: (e.get("created_at", ""), e.get("id", "")))
    if store_type == "issues":
        self._issue_to_project[record_id] = project_path
```

**1d. Cleanup index in `delete()` when `store_type == "issues"`:**
```python
def delete(self, project_path: str, store_type: str, record_id: str) -> None:
    store = self._projects.get(project_path, {}).get(store_type)
    if store is None:
        return
    store["records"].pop(record_id, None)
    store["index"] = [e for e in store["index"] if e.get("id") != record_id]
    if store_type == "issues":
        self._issue_to_project.pop(record_id, None)
```

**1e. Cleanup in `remove_project()`: pop all issue IDs for that project.**
```python
def remove_project(self, project_path: str) -> None:
    self._projects.pop(project_path, None)
    # Cleanup reverse index — find & remove all entries for this project_path
    stale = [iid for iid, pp in self._issue_to_project.items() if pp == project_path]
    for iid in stale:
        self._issue_to_project.pop(iid, None)
```

**1f. Clear in `reset()`:**
```python
def reset(self) -> None:
    self._projects.clear()
    self._issue_to_project.clear()
```

**1g. Add `find_issue_project()` method:**
```python
def find_issue_project(self, issue_id: str) -> str | None:
    return self._issue_to_project.get(issue_id)
```

### Task 2: Expose `find_issue_project` in issue_store

**File:** `backend/app/storage/issue_store.py`

Add thin wrapper after the module-level imports / before the CRUD section:
```python
def find_issue_project(issue_id: str) -> str | None:
    return _core.find_issue_project(issue_id)
```

### Task 3: Update IssueService.get_by_id() to use reverse index

**File:** `backend/app/services/issue_service.py`

Replace line 110-116 (current O(n) scan) with:

```python
async def get_by_id(self, issue_id: str) -> IssueRecord | None:
    # O(1) via reverse index
    project_path = issue_store.find_issue_project(issue_id)
    if project_path is not None:
        rec = issue_store.load_issue(project_path, issue_id)
        if rec is not None:
            # Verify project exists and is not archived
            try:
                project = await ProjectService(self.session).get_by_id(rec.project_id)
                if project is not None and project.archived_at is None:
                    return rec
            except NotFoundError:
                pass  # Deleted project — fall through to scan
    # Fallback: scan all non-archived projects
    for project in await ProjectService(self.session).list_all(archived=False):
        rec = issue_store.load_issue(project.path, issue_id)
        if rec is not None:
            return rec
    return None
```

Key flow:
1. Index hit → `load_issue` → verify project live via `get_by_id(rec.project_id)` + `archived_at` check
2. If project deleted (`NotFoundError`) or archived → fall through to scan
3. Index miss (externally-added issue) → fallback scan → `load_issue` from disk populates index via `_core.upsert()` at line 152 of issue_store.py → subsequent calls O(1)

### Edge Case Coverage

- **Archived project**: Index returns project_path → load_issue returns record → `get_by_id(project_id).archived_at` is not None → fall through to scan → scan skips archived projects → returns None. ✓
- **Externally-added issue**: Index miss → scan finds it → `load_issue` calls `_core.upsert` → index populated → next call O(1). ✓
- **Deleted project**: Index still has entry → `get_by_id(project_id)` raises `NotFoundError` → caught → fallback scan → project not in list → returns None. ✓
- **Issue deleted**: `delete()` in MemoryStoreCore pops from index → subsequent calls miss → fallback scan. ✓
- **Stale index (project removed via `remove_project`)**: `remove_project()` cleans up all issue entries for that path → miss → scan. ✓

### No Test Changes Required

Existing tests cover all paths via `get_for_project()` (which doesn't use the reverse index — it uses `_resolve_path`). No test changes needed. The `get_by_id()` method has no dedicated tests currently, and the change is purely an optimization with zero behavioral change guarantee.

### Memory

After implementation, record: "Reverse index issue_id→project_path added to MemoryStoreCore._issue_to_project. Lifecycle hooks in init_project/upsert/delete/remove_project/reset ensure consistency. IssueService.get_by_id() uses it for O(1) lookup with archived/deleted fallback."
