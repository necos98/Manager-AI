## Implementation Plan: Decompose main.py Lifespan

### Target
`backend/app/main.py`, lines 326-496. Single file refactor. Only decomposition — no behavior/logic changes beyond one documented deviation (project loading switches from continue-on-error to fail-fast, user-approved).

### File changes
Only `backend/app/main.py`. No new files, no changes to other modules.

---

### Phase 1: Preliminaries (move local imports to module level)

Before extracting functions, lift local imports currently inside the lifespan body to module-level scope. These are used by the extracted functions:

1. `from cryptography.fernet import Fernet` — used in `_startup_resolve_secret_key` (line 343). Move to top.
2. `from sqlalchemy import select, update` — used in `_startup_fixup_statuses` (line 372). Move to top.
3. `from sqlalchemy import select` (second use, line 405) — used in `_startup_load_projects`. Move to top.
4. `from app.models.issue import Issue` — used in fixup (line 373). Move to top.
5. `from app.models.project import Project` — used in load_projects (line 406). Move to top.
6. `from app.services.agent_service import AgentService` — used in seed block (line 433). Move to top.
7. `from app.services.pipeline_service import PipelineService` — used in seed block (line 434). Move to top.
8. `from sqlalchemy import select as _select` — used in cleanup (line 453). Rename to `select` at top.
9. `from app.models.pipeline_run import PipelineRun, PipelineRunStatus` — used in cleanup (line 454). Move to top.
10. `from datetime import timezone` — used in cleanup (line 455). Already imported at module level? Check. Add if not.

**Constraint**: Keep `from app.storage.issue_store import TaskRecord` inside `_task_from_dict` (line 305-306) and `_relation_from_dict` (line 317-318) — they're for the helper functions, not lifespan.

### Phase 2: Extract fail-fast startup functions (Sync)

These throw on failure — app does not start.

#### 2a. `_startup_resolve_secret_key()`
- Lines 336-351. Sync.
- Check env var → check data/secret.key → generate+persist.
- No try/except (fail-fast per spec).

#### 2b. `_startup_log_hooks()`
- Lines 353-356. Sync.
- Log hook registry entries.
- No try/except (logging is best-effort, no exception path expected).

### Phase 3: Extract async continue-on-error startup functions

#### 3a. `_startup_migrate(async_session)`
- Lines 358-361. Async.
- `await migrate_all_projects(async_session)` wrapped in existing try/except → logger.exception.

#### 3b. `_startup_fixup_statuses(async_session)`
- Lines 364-392. Async.
- Full block including `_STATUS_FIXUP_MAP` dict, select, update, commit.
- try/except → logger.exception. Keep map inside function.

### Phase 4: Extract sync infrastructure functions

#### 4a. `_startup_init_write_queue()` → `(WriteQueue, BackgroundWriter)`
- Lines 395-401. Sync.
- Instantiate WriteQueue, BackgroundWriter. Inject into store modules.
- Returns tuple. No try/except (fail-fast).

### Phase 5: Extract async fail-fast core function

#### 5a. `_startup_load_projects(async_session, write_queue, background_writer)` → `list[Project]`
- Lines 403-418. Async.
- Query non-archived projects, load each into memory via `_load_project_into_memory`.
- Start background writer if any projects loaded.
- **This is the intentional behavior change**: original wraps in try/except (continue-on-error), spec says fail-fast. Remove the outer try/except. The write_queue injection (lines 399-401) moves into this function since it's part of the project-loading sequence.

### Phase 6: Extract async continue-on-error functions

These all execute after `_startup_load_projects` succeeds, so they receive `rows`.

#### 6a. `_startup_recover_transcriptions(rows)`
- Lines 420-424. Async.
- `recover_pending_transcriptions(p.path)` per-project in loop. Existing try/except preserved.

#### 6b. `_startup_load_catalog()`
- Line 425. Sync.
- `catalog_loader.load()`. Existing try/except via outer block.

#### 6c. `_startup_plugins(rows, mcp)`
- Lines 426-430. Async.
- `plugin_manager.start_plugins_for_project` per-project in loop. `mcp` is module-level import.

#### 6d. `_startup_seed_defaults(async_session)`
- Lines 432-449. Async.
- Seeds agents then pipelines, each with own try/except/rollback per call.
- Consolidate to single `async with async_session()` block.

#### 6e. `_startup_cleanup_orphaned_runs(async_session)`
- Lines 451-474. Async.
- Query RUNNING PipelineRuns, mark FAILED, commit. Existing try/except.

#### 6f. `_startup_install_claude_resources(rows)`
- Lines 476-484. Async.
- Per-project `install_claude_resources_to`. Existing try/except per-project.

### Phase 7: Extract shutdown

#### 7a. `_shutdown(rows, background_writer, write_queue)`
- Lines 490-496. Async.
- Stop plugins per-project, stop background writer, close write queue. Existing try/except per operation.

### Phase 8: Rewrite lifespan body

New body (per spec Section 5, ~40 lines):

```python
@asynccontextmanager
async def lifespan(app):
    if sys.platform == "win32":
        asyncio.get_running_loop().set_exception_handler(_suppress_windows_accept_noise)

    _startup_resolve_secret_key()
    _startup_log_hooks()
    await _startup_migrate(async_session)
    await _startup_fixup_statuses(async_session)
    wq, bw = _startup_init_write_queue()
    rows = await _startup_load_projects(async_session, wq, bw)
    try:
        await _startup_recover_transcriptions(rows)
        _startup_load_catalog()
        await _startup_plugins(rows, mcp)
        await _startup_seed_defaults(async_session)
        await _startup_cleanup_orphaned_runs(async_session)
        await _startup_install_claude_resources(rows)
    except Exception:
        logger.exception("Non-critical startup ops failed; continuing")

    async with mcp.session_manager.run():
        try:
            yield
        finally:
            await _shutdown(rows, bw, wq)
```

---

### Ordering & Dependencies

```
_startup_resolve_secret_key()           [sync, fail-fast]
  → _startup_log_hooks()                [sync, fail-fast]
    → await _startup_migrate(async_session)  [continue-on-error]
      → await _startup_fixup_statuses(async_session)  [continue-on-error]
        → _startup_init_write_queue()   [sync, fail-fast] → (wq, bw)
          → await _startup_load_projects(async_session, wq, bw)  [fail-fast] → rows
            │
            ├→ await _startup_recover_transcriptions(rows)
            ├→ _startup_load_catalog()
            ├→ await _startup_plugins(rows, mcp)
            ├→ await _startup_seed_defaults(async_session)
            ├→ await _startup_cleanup_orphaned_runs(async_session)
            └→ await _startup_install_claude_resources(rows)
              └── (yield) ──→ finally:
                                await _shutdown(rows, bw, wq)
```

Critical: `_startup_init_write_queue` MUST complete before `_startup_load_projects` because `_load_project_into_memory` triggers write-queue injection in store modules.

---

### Gotchas & Constraints

1. **`mcp` is module-level** — imported at line 18. `_startup_plugins` receives it as param for clarity but it's already in scope.
2. **`async_session` is module-level** — imported at line 14. Passed as param to async functions.
3. **`_STATUS_FIXUP_MAP`** — keep as local constant inside `_startup_fixup_statuses`. No reason to extract to module level.
4. **Shutdown access to `mcp`** — shutdown calls `plugin_manager.stop_plugins_for_project(p.id)`. `plugin_manager` is module-level (line 20). Not affected by extraction.
5. **`rows` variable** — must be in scope for shutdown. New lifespan keeps `rows` in scope naturally.
6. **Seed rollback pattern** — each seed call (agents, pipelines) has its own try/except with rollback. This is intentional — one can fail while the other succeeds. Preserve this in `_startup_seed_defaults`.
7. **Local imports in helpers (lines 305-323)** — `_task_from_dict` and `_relation_from_dict` have local imports that stay where they are. Not touched by this refactor.
8. **`datetime import`** — in cleanup code, `datetime.now(_timezone.utc)` is used. Check if `datetime` is imported at module level — it's used throughout main.py. Confirm import exists or add it.

---

### Verification

1. `lifespan()` body reduced from 170 to ~40 lines.
2. Each extracted function is a named, single-purpose unit.
3. Error strategy per function matches spec: fail-fast vs continue-on-error.
4. Startup order preserved.
5. Shutdown order preserved: stop plugins → stop background writer → close write queue.
6. Internal logic of each operation unchanged (exact same code moved).
7. `_load_project_into_memory` and module-level helpers (lines 110-323) unchanged.
8. App starts, routes respond, session manager lifecycle works.
