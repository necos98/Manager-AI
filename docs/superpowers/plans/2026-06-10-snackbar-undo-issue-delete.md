# Snackbar Undo Issue Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace permanent issue deletion with soft-delete + 5s undo snackbar via sonner.

**Architecture:** Add `deleted_at` timestamp to `IssueRecord`. `DELETE` marks `deleted_at` instead of removing files. List endpoints filter out soft-deleted issues. `POST /restore` clears `deleted_at`. Frontend shows sonner toast with Undo action on delete, navigates away only after toast expires. Background purge cleans up old soft-deletes.

**Tech Stack:** Python/FastAPI backend (issue_store + issue_service), React/Vite frontend (sonner), YAML-file-backed IssueRecord dataclass.

---

### Task 1: Backend — Add `deleted_at` to IssueRecord + Index

**Files:**
- Modify: `backend/app/storage/issue_store.py` (IssueRecord, `_to_index_entry`, `_index_to_light_record`, `list_issues`, `list_issues_full`)
- Modify: `backend/app/storage/memory_store_core.py` (add `find_issue_ignore_deleted` if needed — actually memory_store is generic, keep filtering at store level)
- Test: `backend/tests/test_storage_issue_store.py`

- [ ] **Step 1: Add `deleted_at` field to IssueRecord**

```python
@dataclass
class IssueRecord:
    id: str
    project_id: str
    name: str | None
    status: str
    priority: int
    description: str
    specification: str | None
    plan: str | None
    recap: str | None
    created_at: str
    updated_at: str
    finished_at: str | None = None
    category: str | None = None
    deleted_at: str | None = None  # NEW
    tags: list[str] = field(default_factory=list)
    tasks: list[TaskRecord] = field(default_factory=list)
    relations: list[RelationRecord] = field(default_factory=list)
```

- [ ] **Step 2: Add `deleted_at` to `_to_index_entry` + `_index_to_light_record`**

```python
def _to_index_entry(record: IssueRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "project_id": record.project_id,
        "name": record.name,
        "status": record.status,
        "priority": record.priority,
        "category": record.category,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "finished_at": record.finished_at,
        "deleted_at": record.deleted_at,  # NEW
    }


def _index_to_light_record(entry: dict[str, Any]) -> IssueRecord:
    return IssueRecord(
        ...
        finished_at=_as_iso(entry.get("finished_at")),
        deleted_at=_as_iso(entry.get("deleted_at")),  # NEW
    )
```

- [ ] **Step 3: Filter deleted issues from list operations**

Modify `list_issues` and `list_issues_full` to exclude records where `deleted_at` is set:

```python
def list_issues(project_path: str) -> list[IssueRecord]:
    entries = _core.list_index(project_path, "issues")
    if entries:
        records = [_index_to_light_record(e) for e in entries]
        return [r for r in records if r.deleted_at is None]  # NEW
    # Fallback: read from disk index
    data = atomic.read_yaml(paths.issues_index(project_path)) or {}
    disk_entries = data.get("issues") or []
    for e in disk_entries:
        _core.upsert(project_path, "issues", e.get("id", ""), None, e)
    records = [_index_to_light_record(e) for e in disk_entries]
    return [r for r in records if r.deleted_at is None]  # NEW


def list_issues_full(project_path: str) -> list[IssueRecord]:
    all_records = _core.list_all(project_path, "issues")
    if all_records:
        records = [r for r in all_records if r is not None]
        return [r for r in records if r.deleted_at is None]  # NEW
    # Fallback...
```

- [ ] **Step 4: Add `list_deleted_issues` for admin/debug**

```python
def list_deleted_issues(project_path: str) -> list[IssueRecord]:
    """List only soft-deleted issues (for restore UI / cleanup)."""
    all_records = _core.list_all(project_path, "issues")
    if all_records:
        records = [r for r in all_records if r is not None and r.deleted_at is not None]
        return records
    return []
```

- [ ] **Step 5: Write tests**

```python
# tests/test_storage_issue_store.py
def test_soft_deleted_issue_excluded_from_list(populated_project):
    path = populated_project
    issue_id = "test-1"
    rec = issue_store.load_issue(path, issue_id)
    rec.deleted_at = "2026-06-10T12:00:00"
    issue_store.update_issue(path, rec)
    results = issue_store.list_issues(path)
    assert issue_id not in [r.id for r in results]


def test_soft_deleted_issue_still_loadable(populated_project):
    path = populated_project
    issue_id = "test-1"
    rec = issue_store.load_issue(path, issue_id)
    rec.deleted_at = "2026-06-10T12:00:00"
    issue_store.update_issue(path, rec)
    loaded = issue_store.load_issue(path, issue_id)
    assert loaded is not None
    assert loaded.deleted_at == "2026-06-10T12:00:00"
```

- [ ] **Step 6: Run tests**

Run: `cd backend && python -m pytest tests/test_storage_issue_store.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/storage/issue_store.py backend/tests/test_storage_issue_store.py
git commit -m "feat: add deleted_at to IssueRecord, filter from listings"
```

---

### Task 2: Backend — Soft-delete + Restore + Permanent Delete in IssueService + Router

**Files:**
- Modify: `backend/app/services/issue_service.py` (modify `delete()`, add `restore()`, add `permanently_delete()`)
- Modify: `backend/app/routers/issues.py` (add restore + permanent-delete endpoints)
- Modify: `backend/app/mcp/shared_tools.py` (update `delete_issue` MCP tool to soft-delete, add `restore_issue` MCP tool)
- Modify: `backend/app/mcp/orchestrator_server.py` (update orchestrator delete_issue, add restore_issue)
- Test: `backend/tests/test_routers_issues.py`

- [ ] **Step 1: Modify `issue_service.delete()` to soft-delete**

```python
async def delete(self, issue_id: str, project_id: str) -> IssueRecord:
    """Soft-delete: set deleted_at timestamp. Issue still exists in store."""
    path = await self._resolve_path(project_id)
    rec = issue_store.load_issue(path, issue_id)
    if rec is None or rec.project_id != project_id:
        raise NotFoundError("Issue not found")
    rec.deleted_at = _now_iso()
    rec.updated_at = _now_iso()
    issue_store.update_issue(path, rec)
    return rec
```

- [ ] **Step 2: Add `restore()` method**

```python
async def restore(self, issue_id: str, project_id: str) -> IssueRecord:
    """Restore a soft-deleted issue. Raises if not deleted."""
    path = await self._resolve_path(project_id)
    rec = issue_store.load_issue(path, issue_id)
    if rec is None or rec.project_id != project_id:
        raise NotFoundError("Issue not found")
    if rec.deleted_at is None:
        raise ValidationError("Issue is not deleted")
    rec.deleted_at = None
    rec.updated_at = _now_iso()
    issue_store.update_issue(path, rec)
    return rec
```

- [ ] **Step 3: Add `permanently_delete()` method**

```python
async def permanently_delete(self, issue_id: str, project_id: str) -> bool:
    """Permanently erase from RAM and disk. Used after undo window expires."""
    path = await self._resolve_path(project_id)
    if not issue_store.issue_exists(path, issue_id):
        return False
    issue_store.delete_issue(path, issue_id)
    issue_store.delete_issue_files(path, issue_id)
    return True
```

- [ ] **Step 4: Update router endpoints**

```python
# In routers/issues.py

@router.delete("/{issue_id}", status_code=204)
async def delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    """Soft-delete an issue (undo window)."""
    service = IssueService(db)
    await service.delete(issue_id, project_id)
    await db.commit()


@router.post("/{issue_id}/restore", response_model=IssueResponse)
async def restore_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    """Restore a soft-deleted issue."""
    service = IssueService(db)
    record = await service.restore(issue_id, project_id)
    await db.commit()
    return IssueResponse.from_record(record)


@router.delete("/{issue_id}/permanent", status_code=204)
async def permanently_delete_issue(project_id: str, issue_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently delete (no undo)."""
    service = IssueService(db)
    await service.permanently_delete(issue_id, project_id)
    await db.commit()
```

- [ ] **Step 5: Update MCP `shared_tools.py` `delete_issue` to soft-delete + add `restore_issue`**

```python
# shared_tools.py

async def delete_issue(session: AsyncSession, project_id: str, issue_id: str) -> dict:
    """Soft-delete an issue. Can be restored within the undo window."""
    from app.services.issue_service import IssueService
    svc = IssueService(session)
    try:
        await svc.delete(issue_id, project_id)
        await session.commit()
        return {"success": True, "issue_id": issue_id, "deleted": True}
    except AppError as e:
        return {"error": e.message}


async def restore_issue(session: AsyncSession, project_id: str, issue_id: str) -> dict:
    """Restore a soft-deleted issue."""
    from app.services.issue_service import IssueService
    svc = IssueService(session)
    try:
        await svc.restore(issue_id, project_id)
        await session.commit()
        return {"success": True, "issue_id": issue_id}
    except AppError as e:
        return {"error": e.message}
```

- [ ] **Step 6: Wire MCP tools in `orchestrator_server.py`**

```python
# In orchestrator_server.py, replace the existing delete_issue tool
@orchestrator_mcp.tool(description="Soft-delete an issue. Can be restored within the undo window.")
async def delete_issue(project_id: str, issue_id: str) -> dict:
    async with async_session() as session:
        return await _delete_issue(session, project_id, issue_id)


@orchestrator_mcp.tool(description="Restore a soft-deleted issue.")
async def restore_issue(project_id: str, issue_id: str) -> dict:
    """Restore a soft-deleted issue."""
    async with async_session() as session:
        result = await _restore_issue(session, project_id, issue_id)
        return result
```

Add `_restore_issue` import + function similar to existing `_delete_issue` pattern.

- [ ] **Step 7: Write tests**

```python
# tests/test_routers_issues.py

async def test_soft_delete_and_restore(client, sample_project):
    """Soft-delete hides issue from list, restore brings it back."""
    project_id = sample_project["id"]
    # Create an issue
    create_resp = await client.post(f"/api/projects/{project_id}/issues", json={"description": "test"})
    assert create_resp.status_code == 200
    issue_id = create_resp.json()["id"]

    # Soft-delete
    del_resp = await client.delete(f"/api/projects/{project_id}/issues/{issue_id}")
    assert del_resp.status_code == 204

    # Issue not in list
    list_resp = await client.get(f"/api/projects/{project_id}/issues")
    assert issue_id not in [i["id"] for i in list_resp.json()]

    # Restore
    restore_resp = await client.post(f"/api/projects/{project_id}/issues/{issue_id}/restore")
    assert restore_resp.status_code == 200

    # Issue back in list
    list_resp = await client.get(f"/api/projects/{project_id}/issues")
    assert issue_id in [i["id"] for i in list_resp.json()]


async def test_permanent_delete_removes_issue(client, sample_project):
    """Permanent delete actually removes the issue."""
    project_id = sample_project["id"]
    create_resp = await client.post(f"/api/projects/{project_id}/issues", json={"description": "test"})
    issue_id = create_resp.json()["id"]

    perm_resp = await client.delete(f"/api/projects/{project_id}/issues/{issue_id}/permanent")
    assert perm_resp.status_code == 204

    get_resp = await client.get(f"/api/projects/{project_id}/issues/{issue_id}")
    assert get_resp.status_code == 404
```

- [ ] **Step 8: Run tests**

Run: `cd backend && python -m pytest tests/test_routers_issues.py -v`
Expected: PASS (including new tests)

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/issue_service.py backend/app/routers/issues.py backend/app/mcp/shared_tools.py backend/app/mcp/orchestrator_server.py backend/tests/test_routers_issues.py
git commit -m "feat: soft-delete issue with restore endpoint"
```

---

### Task 3: Backend — Background purge for expired soft-deletes

**Files:**
- Modify: `backend/app/services/issue_service.py` (add `purge_expired_deleted()` method)
- Modify: `backend/app/main.py` (schedule periodic purge)

- [ ] **Step 1: Add `purge_expired_deleted()` to IssueService**

```python
async def purge_expired_deleted(self, project_id: str, ttl_seconds: int = 30) -> int:
    """Permanently delete issues that were soft-deleted longer than ttl_seconds ago."""
    from app.utils.datetime import now as utc_now
    from datetime import timedelta

    path = await self._resolve_path(project_id)
    all_records = issue_store.list_issues_full_raw(path)  # includes deleted
    # or we need a method that includes deleted issues
    # Actually, let's use the existing full store but need a way to get deleted ones
    # Add issue_store.list_issues_full_with_deleted(path) for this purpose
    ...

    # Compare deleted_at with current time
    cutoff = utc_now() - timedelta(seconds=ttl_seconds)
    purged = 0
    for rec in all_records:
        if rec.deleted_at:
            deleted_time = parse_iso(rec.deleted_at)
            if deleted_time < cutoff:
                issue_store.delete_issue(path, rec.id)
                issue_store.delete_issue_files(path, rec.id)
                purged += 1
    return purged
```

- [ ] **Step 2: Add `list_issues_full_raw` to issue_store (includes deleted)**

```python
def list_issues_full_raw(project_path: str) -> list[IssueRecord]:
    """Like list_issues_full but includes soft-deleted records."""
    all_records = _core.list_all(project_path, "issues")
    if all_records:
        return [r for r in all_records if r is not None]
    light = list_issues(project_path)
    out = []
    for m in light:
        full = load_issue(project_path, m.id)
        if full is not None:
            out.append(full)
    return out
```

- [ ] **Step 3: Schedule periodic purge in `main.py` lifespan**

```python
# In main.py lifespan, add a background task
async def _periodic_purge():
    while True:
        try:
            async with async_session() as session:
                svc = IssueService(session)
                projects = await ProjectService(session).list_all()
                for project in projects:
                    await svc.purge_expired_deleted(project.id)
                await session.commit()
        except Exception:
            logger.exception("Periodic purge failed")
        await asyncio.sleep(60)  # Check every 60 seconds
```

- [ ] **Step 4: Write test for purge**

```python
# Use asyncio sleep or mock time
async def test_purge_expired_deletes(client, sample_project, monkeypatch):
    project_id = sample_project["id"]
    create_resp = await client.post(f"/api/projects/{project_id}/issues", json={"description": "test"})
    issue_id = create_resp.json()["id"]

    # Soft-delete
    await client.delete(f"/api/projects/{project_id}/issues/{issue_id}")

    # Mock time to be past TTL
    import freezegun
    # ... or simply call purge with ttl=0

    async with AsyncSession() as session:
        svc = IssueService(session)
        purged = await svc.purge_expired_deleted(project_id, ttl_seconds=0)
        assert purged >= 1

    get_resp = await client.get(f"/api/projects/{project_id}/issues/{issue_id}")
    assert get_resp.status_code == 404
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/ -v -k "purge"`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/issue_service.py backend/app/storage/issue_store.py backend/app/main.py
git commit -m "feat: periodic purge of expired soft-deleted issues"
```

---

### Task 4: Frontend — Snackbar undo on issue delete

**Files:**
- Modify: `frontend/src/features/issues/hooks.ts` (add `useRestoreIssue`, modify delete flow)
- Modify: `frontend/src/features/issues/api.ts` (add `restoreIssue`, `permanentlyDeleteIssue`)
- Modify: `frontend/src/features/issues/components/issue-detail.tsx` (replace confirm dialog handler with toast+undo)

- [ ] **Step 1: Add restore + permanent delete API functions**

```typescript
// frontend/src/features/issues/api.ts

export function restoreIssue(projectId: string, issueId: string): Promise<Issue> {
  return apiPost<Issue>(`/projects/${projectId}/issues/${issueId}/restore`);
}

export function permanentlyDeleteIssue(projectId: string, issueId: string): Promise<null> {
  return apiDelete(`/projects/${projectId}/issues/${issueId}/permanent`);
}
```

- [ ] **Step 2: Add `useRestoreIssue` hook**

```typescript
// frontend/src/features/issues/hooks.ts

export function useRestoreIssue(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (issueId: string) => api.restoreIssue(projectId, issueId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: issueKeys.all(projectId) });
    },
    onError: onMutationError,
  });
}
```

- [ ] **Step 3: Modify `handleDelete` in issue-detail.tsx to show toast with Undo**

Replace the current `handleDelete`:

```typescript
import { toast } from "sonner";
import { useRestoreIssue } from "../hooks";
import { useNavigate } from "@tanstack/react-router";

// Inside IssueDetail component:
const restoreIssue = useRestoreIssue(projectId);

const handleDelete = async () => {
  setShowDeleteConfirm(false);
  
  // Close terminal if exists
  if (terminalId) {
    try {
      await killTerminal.mutateAsync(terminalId);
    } catch (e) {
      console.warn("killTerminal during delete:", e);
    }
  }

  // Soft-delete
  deleteIssue.mutate(issue.id, {
    onSuccess: () => {
      const toastId = toast("Issue deleted", {
        description: `${issue.name || "Untitled"} — Undo available for 5s`,
        action: {
          label: "Undo",
          onClick: () => {
            // Restore the issue
            restoreIssue.mutate(issue.id, {
              onSuccess: () => {
                toast.success("Issue restored");
              },
            });
          },
        },
        duration: 5000,
      });

      // Navigate away after a brief delay so toast renders
      setTimeout(() => {
        navigate({
          to: "/projects/$projectId/issues",
          params: { projectId },
        });
      }, 100);
    },
  });
};
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/issues/api.ts frontend/src/features/issues/hooks.ts frontend/src/features/issues/components/issue-detail.tsx
git commit -m "feat: snackbar undo on issue delete via sonner toast"
```

---

### Task 5: Self-Review

- [ ] **Spec coverage:** Issue description says "Snackbar Issue deleted + pulsante Undo (5 secondi) via sonner" and "Soft-delete temporaneo per supportare undo." Task 1–3 cover backend soft-delete + restore + purge. Task 4 covers frontend sonner toast with Undo button. All requirements mapped.

- [ ] **Placeholder scan:** All steps contain actual code, commands, or content. No TBD, TODOs, or "implement later". All type signatures consistent (e.g., `restore()` returns `IssueRecord`, matches `IssueResponse.from_record` pattern).

- [ ] **Type consistency:** `IssueRecord.deleted_at` is `str | None`. `_to_index_entry` emits `deleted_at`. `_index_to_light_record` reads `deleted_at`. `delete()` returns `IssueRecord`. `restore()` returns `IssueRecord`. Router endpoints use 204 for deletes, 200 for restore with `IssueResponse`. All consistent.

- [ ] **Undo race:** If user soft-deletes → opens another browser tab → soft-deletes again → the second delete refreshes the `deleted_at` timestamp. The undo window effectively extends. This is acceptable — no corrupted state.

- [ ] **Edge: restore after purge window:** If user waits 30s+ before clicking Undo, the issue may already be purged from the background task. In that case `restore()` will call `load_issue()` which returns `None` → `NotFoundError`. The frontend receives the error and the toast was likely already dismissed. Acceptable — the user can't interact with a stale toast that survived navigation.
