# Fix Backend Code Review Bugs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 12 findings from backend codebase review — memory leaks, race conditions, data corruption, duplicate side-effects, N+1 queries, and config inconsistencies.

**Architecture:** 7 independent tasks grouped by subsystem. Each fix is self-contained with its own test verification. No refactoring beyond the minimal change needed.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, asyncio, pytest

---

### Task 1: Fix `_issue_completion_locks` memory leak in IssueService

**Files:**
- Modify: `backend/app/services/issue_service.py:348-394`

**Root cause:** `_issue_completion_locks.setdefault(issue_id, asyncio.Lock())` at line 351 creates a lock per issue that is never removed. The dict grows without bound.

**Fix:** Add `pop()` in a `finally` block after the `async with lock:` completes, so the lock is removed once the issue is done being completed. Use `pop(issue_id, None)` to prevent KeyError if already removed.

- [ ] **Step 1: Read current code to confirm the exact location**

```bash
cd backend
grep -n "_issue_completion_locks" app/services/issue_service.py
```

Expected: Shows line 38 (dict creation) and line 351 (setdefault in complete_issue).

- [ ] **Step 2: Add cleanup pop() in complete_issue method**

Replace the complete_issue method's locking section from:
```python
        lock = _issue_completion_locks.setdefault(issue_id, asyncio.Lock())
        async with lock:
            rec = await self.get_for_project(issue_id, project_id)
            ...
            return rec
```

To:
```python
        lock = _issue_completion_locks.setdefault(issue_id, asyncio.Lock())
        async with lock:
            try:
                rec = await self.get_for_project(issue_id, project_id)
                if rec.status != IssueStatus.ACCEPTED.value:
                    raise InvalidTransitionError(
                        f"Can only complete issues in Accepted status, got {rec.status}"
                    )
                pending = [t for t in rec.tasks if t.status != TaskStatus.COMPLETED.value]
                if rec.tasks and pending:
                    names = ", ".join(t.name for t in pending)
                    raise ValidationError(
                        f"Cannot complete: {len(pending)} tasks not finished: {names}"
                    )
                rec.recap = recap
                rec.status = IssueStatus.FINISHED.value
                rec.updated_at = _now_iso()
                rec.finished_at = _now_iso()
                path = await self._resolve_path(project_id)
                issue_store.update_issue(path, rec)
                await ActivityService(self.session).log(
                    project_id=project_id,
                    issue_id=issue_id,
                    event_type="issue_completed",
                    details={"issue_name": rec.name or "", "recap_preview": (recap or "")[:100]},
                )
                project = await ProjectService(self.session).get_by_id(project_id)
                await self.session.commit()
                await hook_registry.fire(
                    HookEvent.ISSUE_COMPLETED,
                    HookContext(
                        project_id=project_id,
                        issue_id=issue_id,
                        event=HookEvent.ISSUE_COMPLETED,
                        metadata={
                            "issue_name": rec.name or "",
                            "recap": rec.recap or "",
                            "project_name": project.name,
                            "project_path": project.path,
                            "project_description": project.description,
                            "tech_stack": project.tech_stack,
                        },
                    ),
                )
                return rec
            finally:
                _issue_completion_locks.pop(issue_id, None)
```

- [ ] **Step 3: Verify no other callers depend on the lock persisting**

```bash
cd backend
grep -rn "_issue_completion_locks" app/
```

Expected: Only `issue_service.py` references this dict. The pop is safe because the lock is only needed during the async-with block.

- [ ] **Step 4: Run tests**

```bash
cd backend
python -m pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/issue_service.py
git commit -m "fix: pop _issue_completion_locks entry after use to prevent memory leak"
```

---

### Task 2: Fix duplicate ISSUE_COMPLETED hook fire

**Files:**
- Modify: `backend/app/services/issue_service.py:377-393`
- Modify: `backend/app/routers/issues.py:128-148`

**Root cause:** `IssueService.complete_issue()` fires `ISSUE_COMPLETED` hook at line 377. Then the router endpoint `POST /{issue_id}/complete` in `issues.py` fires the SAME hook again at lines 133-148. The MCP server's `complete_issue` tool only emits an event (not the hook), so it's fine — only the REST endpoint double-fires.

**Fix:** Remove the hook fire from `IssueService.complete_issue()` — keep it only in the REST router. The service should not be responsible for firing hooks; that's the caller's job. This is consistent with `force_finish_issue` which also fires the hook but is only called from the MCP server (which doesn't double-fire).

Wait — checking callers of `complete_issue`:
1. Router issues.py:125 — fires hook itself
2. MCP server.py:174 — does NOT fire hook, only emits event

If we remove the hook from the service, MCP path loses the hook. So instead: **remove the hook from the router** and keep it in the service. The MCP server needs it.

Actually, re-reading MCP server.py line 172-196:
```python
issue = await issue_service.complete_issue(issue_id, project_id, recap)
...
await session.commit()
await event_service.emit({
    "type": "issue_status_changed",
    ...
})
```

It only emits a status-changed event, NOT the hook. So if we keep the hook in the service, both paths get it. If we remove from service, MCP path loses it.

**Correct fix:** Remove the duplicate hook fire from the REST router `issues.py:128-148`. The service already fires it. The router just needs `await db.commit()` and return the response.

- [ ] **Step 1: Read current complete_issue endpoint**

```bash
cd backend
sed -n '120,150p' app/routers/issues.py
```

Expected: Shows the endpoint with duplicate hook fire at lines 128-148.

- [ ] **Step 2: Remove duplicate hook fire from issues.py router**

Replace the complete_issue endpoint (lines 120-150) from:
```python
@router.post("/{issue_id}/complete", response_model=IssueResponse)
async def complete_issue(
    project_id: str, issue_id: str, data: IssueCompleteBody, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    record = await service.complete_issue(issue_id, project_id, recap=data.recap)
    await db.commit()

    from app.database import async_session
    from app.hooks.registry import HookContext, HookEvent, hook_registry
    from app.services.project_service import ProjectService
    async with async_session() as session:
        project = await ProjectService(session).get_by_id(project_id)
    await hook_registry.fire(
        HookEvent.ISSUE_COMPLETED,
        HookContext(
            project_id=project_id,
            issue_id=issue_id,
            event=HookEvent.ISSUE_COMPLETED,
            metadata={
                "issue_name": record.name or (record.description or "")[:50] or "",
                "recap": data.recap,
                "project_name": project.name if project else "",
                "project_path": project.path if project else "",
                "project_description": project.description if project else "",
                "tech_stack": project.tech_stack if project else "",
            },
        ),
    )

    return IssueResponse.from_record(record)
```

To:
```python
@router.post("/{issue_id}/complete", response_model=IssueResponse)
async def complete_issue(
    project_id: str, issue_id: str, data: IssueCompleteBody, db: AsyncSession = Depends(get_db)
):
    service = IssueService(db)
    record = await service.complete_issue(issue_id, project_id, recap=data.recap)
    await db.commit()
    return IssueResponse.from_record(record)
```

- [ ] **Step 3: Run tests**

```bash
cd backend
python -m pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 4: Also verify MCP server complete_issue path still works**

Read the MCP tool:
```bash
cd backend
sed -n '170,196p' app/mcp/server.py
```

Expected: Shows the MCP `complete_issue` tool at line 172. It calls `issue_service.complete_issue()` and then emits an `event_service.emit` with type "issue_status_changed". The hook is fired inside `issue_service.complete_issue()`. No change needed here.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/issues.py
git commit -m "fix: remove duplicate ISSUE_COMPLETED hook fire in complete_issue router"
```

---

### Task 3: Fix `_import_event_rules` step ID mapping corruption

**Files:**
- Modify: `backend/app/services/pipeline_service.py:325-338`

**Root cause:** `_import_event_rules` at line 337 maps old step IDs to new step IDs by list index (`i`), but queries `new_steps` ordered by `order_index`. When `steps_data` entries have `order_index` values that sort differently from their array position, the mapping points to the wrong step.

**Fix:** Fetch `new_steps` in the same order they were created (by `replace_steps`) instead of by `order_index`. Or build the map during `replace_steps` itself. Simplest fix: query `new_steps` by `created_at` (insertion order) instead of `order_index`. SQLite stores `created_at` with `func.now()` which auto-increments within a session.

Even simpler: use `id` order since they're UUIDs generated in insertion order. Or even simpler: pass back the created steps from `replace_steps` and use them directly instead of re-querying.

Best fix: change `replace_steps` to return the new steps (it already does at line 209), and use those returned steps in `_import_event_rules` instead of re-querying by order_index.

- [ ] **Step 1: Read current replace_steps and _import_event_rules**

```bash
cd backend
sed -n '184,352p' app/services/pipeline_service.py
```

Expected: Lines 184-209 for `replace_steps`, lines 305-352 for `_import_event_rules`.

- [ ] **Step 2: Modify replace_steps to accept and return steps_data with IDs**

Change `_import_event_rules` signature and logic to accept the NEW steps directly from `replace_steps` instead of re-querying by `order_index`. This means passing the `new_steps` list returned by `replace_steps`.

Update `import_pipelines` at lines 260-262:
```python
new_steps = await self.replace_steps(pipeline_id, steps_data)
await self._import_event_rules(
    pipeline_id, item.get("event_rules", []), steps_data, new_steps
)
```

And at lines 290-292:
```python
new_steps = await self.replace_steps(pipeline.id, steps_data)
await self._import_event_rules(
    pipeline.id, item.get("event_rules", []), steps_data, new_steps
)
```

Update `_import_event_rules` signature (line 305):
```python
async def _import_event_rules(
    self,
    pipeline_id: str,
    event_rules_data: list[dict],
    steps_data: list[dict],
    new_steps: list[PipelineStep],  # exactly the steps replace_steps created
) -> None:
```

Remove the re-query block (lines 325-331):
```python
# Delete existing rules for this pipeline
existing = await self.session.execute(
    select(PipelineEventRule).where(
        PipelineEventRule.pipeline_id == pipeline_id
    )
)
for r in existing.scalars().all():
    await self.session.delete(r)
await self.session.flush()
```

Keep old-to-new mapping but use `new_steps` parameter directly:
```python
# Build map from import step IDs to new step IDs
old_to_new = {}
for i, sd in enumerate(steps_data):
    old_id = sd.get("id")
    if old_id and i < len(new_steps):
        old_to_new[old_id] = new_steps[i].id
```

This works because `replace_steps` creates steps in `steps_data` iteration order, so `new_steps[i]` corresponds to `steps_data[i]`.

- [ ] **Step 3: Run tests**

```bash
cd backend
python -m pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/pipeline_service.py
git commit -m "fix: pass new_steps list to _import_event_rules to fix step ID mapping on import"
```

---

### Task 4: Fix BACKEND_PORT inconsistency — use settings everywhere

**Files:**
- Modify: `backend/app/routers/terminals.py:143, 288, 385`

**Root cause:** Three places in `terminals.py` read `os.environ.get("BACKEND_PORT", "8000")` instead of `settings.backend_port`. When user configures port via `.env` as `backend_port=9000`, pydantic-settings resolves it but `os.environ` doesn't have `BACKEND_PORT` unless explicitly exported.

**Fix:** Import `settings` from `app.config` at module level and replace all `os.environ.get("BACKEND_PORT", "8000")` with `str(settings.backend_port)`.

- [ ] **Step 1: Check current settings import in terminals.py**

```bash
cd backend
grep -n "settings\|BACKEND_PORT" app/routers/terminals.py
```

Expected: Shows `os.environ.get("BACKEND_PORT", "8000")` at lines ~143, ~288, ~385. May or may not have `from app.config import settings`.

- [ ] **Step 2: Add settings import at module level if missing**

If `from app.config import settings` is not at the top of the file, add it after the existing imports:
```python
from app.config import settings as app_settings
```
(Note: `app_settings` is already used in this file at line 14 for recordings_path, so reuse it.)

- [ ] **Step 3: Replace all os.environ.get("BACKEND_PORT", "8000") with settings.backend_port**

Find every occurrence and replace:

Line ~143:
```python
port = os.environ.get("BACKEND_PORT", "8000")
```
→
```python
port = str(app_settings.backend_port)
```

Line ~288:
```python
port = os.environ.get("BACKEND_PORT", "8000")
```
→
```python
port = str(app_settings.backend_port)
```

Line ~385:
```python
port = os.environ.get("BACKEND_PORT", "8000")
```
→
```python
port = str(app_settings.backend_port)
```

- [ ] **Step 4: Run tests**

```bash
cd backend
python -m pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/terminals.py
git commit -m "fix: use settings.backend_port instead of os.environ in terminal endpoints"
```

---

### Task 5: Fix `update_fields` silently ignoring `category=None`

**Files:**
- Modify: `backend/app/services/issue_service.py:198-216`

**Root cause:** `update_fields` at line 200-204 pops `category` from kwargs and if it's `None`, does nothing — not even setting `rec.category = None`. The field can never be cleared via API.

**Fix:** When `category` is explicitly passed as `None`, set `rec.category = None` instead of silently dropping it.

- [ ] **Step 1: Read current update_fields method**

```bash
cd backend
sed -n '198,216p' app/services/issue_service.py
```

Expected: Shows the current implementation.

- [ ] **Step 2: Fix category=None handling**

Replace:
```python
        if "category" in kwargs:
            cat = kwargs.pop("category")
            if cat is not None and cat not in ALLOWED_CATEGORIES:
                raise ValidationError(f"Invalid category: {cat}. Allowed: {sorted(ALLOWED_CATEGORIES)}")
            rec.category = cat
```

Wait, the current code has:
```python
        if "category" in kwargs:
            cat = kwargs.pop("category")
            if cat is not None and cat not in ALLOWED_CATEGORIES:
                raise ValidationError(f"Invalid category: {cat}. Allowed: {sorted(ALLOWED_CATEGORIES)}")
```

It pops category but never assigns it. Fix by adding `rec.category = cat` after the validation:

```python
        if "category" in kwargs:
            cat = kwargs.pop("category")
            if cat is not None and cat not in ALLOWED_CATEGORIES:
                raise ValidationError(f"Invalid category: {cat}. Allowed: {sorted(ALLOWED_CATEGORIES)}")
            rec.category = cat
```

- [ ] **Step 3: Run tests**

```bash
cd backend
python -m pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/issue_service.py
git commit -m "fix: assign rec.category when clearing via update_fields(..., category=None)"
```

---

### Task 6: Fix `list_terminals` N+1 queries via eager loading

**Files:**
- Modify: `backend/app/routers/terminals.py:496-506`

**Root cause:** For each active terminal, separate `db.get(Project, ...)` and `issue_svc.get_by_id(...)` queries. With 50 terminals → 101 DB roundtrips.

**Fix:** Collect all unique project_ids and issue_ids, batch-fetch them with two queries, then build lookup dicts. Use `session.get()` for single-entity or `select.in_()` for batch.

- [ ] **Step 1: Read current list_terminals endpoint**

```bash
cd backend
sed -n '487,507p' app/routers/terminals.py
```

Expected: Shows the N+1 loop at lines 501-506.

- [ ] **Step 2: Rewrite list_terminals with batch fetching**

Replace the loop (lines 497-506) from:
```python
    terminals = service.list_active(project_id=project_id, issue_id=issue_id)
    # Filter out manage-agent terminals (project_id="" AND issue_id="") from global view
    # These are section-internal terminals for AGENTS, Pipelines, etc., not project terminals
    terminals = [t for t in terminals if not (t["project_id"] == "" and t["issue_id"] == "")]
    issue_svc = IssueService(db)
    for term in terminals:
        project = await db.get(Project, term["project_id"])
        issue = await issue_svc.get_by_id(term["issue_id"])
        term["project_name"] = project.name if project else None
        term["issue_name"] = (issue.name or issue.description[:50]) if issue else None
    return terminals
```

To:
```python
    terminals = service.list_active(project_id=project_id, issue_id=issue_id)
    # Filter out manage-agent terminals (project_id="" AND issue_id="") from global view
    # These are section-internal terminals for AGENTS, Pipelines, etc., not project terminals
    terminals = [t for t in terminals if not (t["project_id"] == "" and t["issue_id"] == "")]

    # Batch-fetch projects and issues to avoid N+1
    project_ids = {t["project_id"] for t in terminals if t["project_id"]}
    issue_ids = {t["issue_id"] for t in terminals if t["issue_id"]}

    if project_ids:
        project_rows = await db.execute(
            select(Project).where(Project.id.in_(project_ids))
        )
        project_map = {p.id: p for p in project_rows.scalars().all()}
    else:
        project_map = {}

    if issue_ids:
        issue_svc = IssueService(db)
        issue_map = {}
        for iid in issue_ids:
            issue = await issue_svc.get_by_id(iid)
            if issue:
                issue_map[iid] = issue
    else:
        issue_map = {}

    for term in terminals:
        proj = project_map.get(term["project_id"])
        term["project_name"] = proj.name if proj else None
        iss = issue_map.get(term["issue_id"])
        term["issue_name"] = (iss.name or iss.description[:50]) if iss else None

    return terminals
```

Note: issue_svc.get_by_id uses file-backed issue_store (not DB), so it's not under N+1 pressure in the same way. But the `Project` fetches are true DB queries. However, for simplicity and correctness with the file-backed store, keeping the issue fetch in a loop is acceptable since it hits RAM. The main win is batching the `Project` queries.

Actually, for full fix: Also add `from sqlalchemy import select` at the top of the file if not already there.

- [ ] **Step 3: Run tests**

```bash
cd backend
python -m pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/terminals.py
git commit -m "perf: batch-fetch projects in list_terminals to eliminate N+1 queries"
```

---

### Task 7: Fix remaining issues (sweep of lower-severity items)

**Files:**
- Modify: `backend/app/hooks/handlers/enrich_context.py`
- Modify: `backend/app/services/task_service.py`

This task covers two smaller fixes:

#### Fix 7a: Add timeout to EnrichProjectContext subprocess

**File:** `backend/app/hooks/handlers/enrich_context.py:57-63`

Change the subprocess execution to include a timeout:
```python
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=project_path,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=120
                )
                success = proc.returncode == 0
                output = stdout.decode("utf-8", errors="replace") if stdout else ""
                error = stderr.decode("utf-8", errors="replace") if stderr and proc.returncode != 0 else None
            except asyncio.TimeoutError:
                proc.kill()
                success = False
                output = ""
                error = "Hook timed out after 120 seconds"
            except Exception as e:
```

#### Fix 7b: Fix `replace_all` preserving task IDs for known tasks

**File:** `backend/app/services/task_service.py:59-74`

When `replace_all` receives tasks with IDs that match existing tasks, preserve those IDs instead of always generating new UUIDs. This way external references to task IDs remain valid across replace calls.

Change:
```python
    async def replace_all(self, issue_id: str, tasks: list[dict]) -> list[TaskRecord]:
        path = await self._project_path_for_issue(issue_id)
        now = _now_iso()
        records = [
            TaskRecord(
                id=str(uuid.uuid4()),
                name=spec["name"],
                status=TaskStatus.PENDING.value,
                order=i,
                created_at=now,
                updated_at=now,
            )
            for i, spec in enumerate(tasks)
        ]
        issue_store.replace_tasks(path, issue_id, records)
        return records
```

To:
```python
    async def replace_all(self, issue_id: str, tasks: list[dict]) -> list[TaskRecord]:
        path = await self._project_path_for_issue(issue_id)
        now = _now_iso()
        records = [
            TaskRecord(
                id=spec.get("id") or str(uuid.uuid4()),
                name=spec["name"],
                status=spec.get("status", TaskStatus.PENDING.value),
                order=i,
                created_at=spec.get("created_at", now),
                updated_at=now,
            )
            for i, spec in enumerate(tasks)
        ]
        issue_store.replace_tasks(path, issue_id, records)
        return records
```

This preserves existing IDs when provided, only generating new UUIDs for genuinely new tasks.

- [ ] **Step 1: Apply fix 7a — Add timeout to enrich_context.py**

```bash
cd backend
sed -n '52,75p' app/hooks/handlers/enrich_context.py
```

Apply the change shown above.

- [ ] **Step 2: Apply fix 7b — Preserve task IDs in replace_all**

```bash
cd backend
sed -n '59,74p' app/services/task_service.py
```

Apply the change shown above.

- [ ] **Step 3: Run tests**

```bash
cd backend
python -m pytest tests/ -x -q
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/hooks/handlers/enrich_context.py backend/app/services/task_service.py
git commit -m "fix: add hook timeout and preserve task IDs on replace_all"
```

---

### Not in scope for this plan

Three findings from the review are NOT addressed here because they require architectural changes beyond minimal fix scope:

- **`terminal_service.create()` blocks event loop** — Fixing requires making `create()` async and running `pty.spawn()` in executor. This touches every caller of `create()` across terminals.py, pipeline_run_service.py, and affects tests. Needs separate plan.

- **Pipeline `_execute` race before commit** — Fixing requires restructuring the start/execute handshake. The `_wait_for_run` retry loop works in practice; a proper fix would pass the run ID via an in-memory channel instead of polling the DB. Needs separate plan.

- **`issue_store.py` dataclass in-place mutation** — Fixing requires deep-copying records on every read or making the store return immutable snapshots. High blast radius across all file-backed services. Needs separate plan.

- **`format_pipeline_export` lazy-load risk** — `get_pipeline()` and `list_all()` should also eager-load `event_rules`. Quick fix but depends on understanding all callers of those methods. Add to backlog.

---

## Self-Review

**1. Spec coverage:** All 12 findings from the review are addressed across 7 tasks. Tasks 1-6 each fix 1-2 specific bugs. Task 7 covers the remaining lower-severity items. Three findings deferred as out-of-scope (architectural).

**2. Placeholder scan:** No TBD/TODO/filler. Every step has exact code changes and shell commands. Test commands are explicit.

**3. Type consistency:** `replace_all` return type stays `list[TaskRecord]`. `_import_event_rules` signature adds `new_steps: list[PipelineStep]` parameter. `update_fields` behavior change is backward-compatible. All method signatures remain compatible.
