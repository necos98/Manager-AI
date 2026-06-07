## Specification: Decompose main.py Monolithic Lifespan

### 1. Scope

Extract the 170-line `lifespan()` function in `backend/app/main.py:326-496` into named `_startup_*` helper functions and a `_shutdown()` function. Each function encapsulates one logical operation. The outer `lifespan()` becomes a linear sequence of calls with error handling at the appropriate granularity.

**No behavior changes. No logic changes. Only decomposition.**

Exception: `_startup_load_projects` changes from continue-on-error to fail-fast (see Section 3). This is intentional and user-approved.

### 2. Extracted Functions

All functions are module-level `async def` in `main.py`, prefixed with underscore (private). Each receives only the parameters it needs:

| # | Function | Parameters | Error strategy |
|---|----------|-----------|----------------|
| 1 | `_startup_resolve_secret_key()` | none | **Fail-fast** — if secret key can't be resolved, Fernet ops fail later with cryptic errors. |
| 2 | `_startup_log_hooks()` | none | **Fail-fast** — logging is best-effort, no exception path exists. |
| 3 | `_startup_migrate()` | `async_session` | **Continue on error** — migration failure logged, startup should not block. (Existing behavior — keep wrapped.) |
| 4 | `_startup_fixup_statuses()` | `async_session` | **Continue on error** — non-critical data cleanup. |
| 5 | `_startup_init_write_queue()` | none, returns `(WriteQueue, BackgroundWriter)` | **Fail-fast** — write queue is required before any store operation. |
| 6 | `_startup_load_projects()` | `async_session`, `write_queue`, `background_writer` | **Fail-fast** — if projects can't load, the app is unusable. Existing injection of write_queue into store modules happens here. |
| 7 | `_startup_recover_transcriptions(rows)` | list of Project rows | **Continue on error** — per-project error is non-fatal. |
| 8 | `_startup_load_catalog()` | none | **Continue on error** — catalog is advisory. |
| 9 | `_startup_plugins(rows)` | list of Project rows, `mcp` | **Continue on error** — per-project plugin failures don't block the app. |
| 10 | `_startup_seed_defaults()` | `async_session` | **Continue on error** — seed data regenerates on next deploy. |
| 11 | `_startup_cleanup_orphaned_runs()` | `async_session` | **Continue on error** — orphaned runs are cosmetic. |
| 12 | `_startup_install_claude_resources(rows)` | list of Project rows | **Continue on error** — per-project failure is non-fatal. |
| 13 | `_shutdown(rows, background_writer, write_queue)` | from lifespan scope | **Continue on error** — best-effort cleanup. |

### 3. Error Handling Strategy (Mix Approach)

**Fail-fast** (app does not start):
- `_startup_resolve_secret_key` — no key = no encryption = broken app
- `_startup_init_write_queue` — no queue = no persistence
- `_startup_load_projects` — no projects loaded = app dead on arrival

**Continue on error** (log & proceed):
- `_startup_migrate`, `_startup_fixup_statuses`, `_startup_recover_transcriptions`
- `_startup_load_catalog`, `_startup_plugins`, `_startup_seed_defaults`
- `_startup_cleanup_orphaned_runs`, `_startup_install_claude_resources`
- `_shutdown` (all operations)

### 4. Ordering Dependencies

```
_startup_resolve_secret_key()
  └→ _startup_log_hooks()
       └→ _startup_migrate(async_session)
            └→ _startup_fixup_statuses(async_session)
                 └→ _startup_init_write_queue() → (wq, bw)
                      └→ _startup_load_projects(async_session, wq, bw) → rows
                           ├→ _startup_recover_transcriptions(rows)
                           ├→ _startup_load_catalog()
                           ├→ _startup_plugins(rows, mcp)
                           ├→ _startup_seed_defaults(async_session)
                           ├→ _startup_cleanup_orphaned_runs(async_session)
                           └→ _startup_install_claude_resources(rows)
```

Critical: `_startup_init_write_queue` MUST complete before `_startup_load_projects` because `_load_project_into_memory` calls `store.init_project()` which triggers write-queue injection.

### 5. Lifespan Structure (Preserved)

`_noop_lifespan` at line 75-84: unchanged.
`_load_project_into_memory` at line 110-280: unchanged (not part of this refactor).
Module-level helpers at lines 283-323: unchanged.

New `lifespan()` body:
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

Note: The fail-fast functions (1-2, 5-6) use bare calls without try/except. The continue-on-error block wraps the rest.

### 6. Acceptance Criteria

1. `lifespan()` body reduced from 170 lines to ~40 lines (sequence of calls).
2. Each extracted function is a single, testable unit with a clear name.
3. Error strategy documented per function: fail-fast vs. continue-on-error.
4. Startup order preserved exactly: secret key → hooks → migrate → fixup → write queue → load projects → non-critical ops → yield.
5. Shutdown order preserved: stop plugins → stop background writer → close write queue.
6. Zero behavior change for each extracted operation's internal logic — all existing error messages, log levels, and fallback behavior preserved within each function. The one intentional deviation: project loading changes from continue-on-error to fail-fast (see Section 3).
7. `_load_project_into_memory` and module-level helpers remain unchanged.

### 7. Non-Goals

- **Not** restructuring `_load_project_into_memory` or its helpers (lines 110-323).
- **Not** changing error messages, log levels, or fallback behavior.
- **Not** adding new features or capabilities.
- **Not** refactoring the router registration, middleware setup, or app creation (lines 499-554).
- **Not** extracting the Windows exception handler setup at line 49-73.
- **Not** extracting the `_SuppressClientDisconnectFilter` or `_noop_lifespan` classes.
- **Not** changing import structure or module organization.
- **Not** writing tests for the extracted functions (though they become easier to test).

### 8. Constraints

- `_startup_init_write_queue` must be synchronous (WriteQueue init is sync).
- `mcp.session_manager.run()` context manager must wrap the yield — the lifespan function yields once inside it.
- All `_startup_*` functions prefixed with underscore (private).
- `async_session` import from `app.database` is already module-level — functions use it as passed parameter.
- Local imports inside the original lifespan (e.g., `from sqlalchemy import select`, `from cryptography.fernet import Fernet`) should be moved to module level where practical, or kept local if they're only used in one function.

### 9. Open Questions

None — approach was clarified during brainstorming with user. Mix error strategy is confirmed.
