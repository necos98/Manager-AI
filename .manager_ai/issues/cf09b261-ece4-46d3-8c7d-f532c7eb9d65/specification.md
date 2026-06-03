# Fix Terminal Leak in Pipeline: \_sessions Dict Not Cleaned Up

## Scope

Fix memory leak where `pipeline_run_service.py` creates `TerminalSession` objects per pipeline step inside `_run_step()` but never removes them. Each pipeline run with N steps leaks N `TerminalSession` instances (with reader tasks, pty_dead events) in the module-level `_sessions` dict.

## Root Cause

`backend/app/services/pipeline_run_service.py` — `_execute()` finally block (lines 234-236):

```python
finally:
    _save_recording(term_id, terminal_service.get_buffered_output(term_id))
    terminal_service.kill(term_id)
```

This calls `kill()` on the PTY but does **not** call `_stop_reader(term_id)` (which cancels the background asyncio reader task) nor `_sessions.pop(term_id, None)` (which removes the leaked `TerminalSession` object).

Compare with proper cleanup patterns:
- `_teardown_terminal()` in `terminals.py:35-52`
- `delete_terminal()` REST endpoint in `terminals.py:547-562`

Both do the full sequence: get_buffered_output → _save_recording → _stop_reader → _sessions.pop → kill.

## What to Build

### Fix 1 — Pipeline `_execute()` finally block

In `pipeline_run_service.py`, add `_stop_reader(term_id)` and `_sessions.pop(term_id, None)` to the `_execute()` finally block at lines 234-236. Sequence must be:

```python
finally:
    _save_recording(term_id, terminal_service.get_buffered_output(term_id))
    _stop_reader(term_id)
    _sessions.pop(term_id, None)
    terminal_service.kill(term_id)
```

**IMPORTANT — import requirement:** `pipeline_run_service.py` line 21 currently imports only `_save_recording` from `terminal_session`:
```python
from app.services.terminal_session import _save_recording
```
Must update to also import `_sessions` and `_stop_reader`:
```python
from app.services.terminal_session import _save_recording, _sessions, _stop_reader
```
The `_stop_reader` function is NOT currently imported anywhere in this file — it is only imported in `terminals.py`. The `_sessions` dict is imported inside `_run_step()` at line 294 but that scope doesn't cover the finally block in `_execute()`. Both must be added to the module-level import.

### Fix 2 — `delete_project` terminal session cleanup

In `projects.py` (lines 354-358), after `terminal_service.kill(term["id"])`, also clean up the `_sessions` dict. Currently the loop only calls `kill()`:

```python
for term in terminal_service.list_active(project_id=project_id):
    try:
        terminal_service.kill(term["id"])
    except KeyError:
        pass
```

Add `_stop_reader()` and `_sessions.pop()` before `kill()`:

```python
from app.services.terminal_session import _sessions, _stop_reader

# ... in delete_project:
for term in terminal_service.list_active(project_id=project_id):
    try:
        _stop_reader(term["id"])
        _sessions.pop(term["id"], None)
        terminal_service.kill(term["id"])
    except KeyError:
        pass
```

The import must be added at the top of `projects.py` alongside other `terminal_session` imports if any, or at module level.

### Fix 3 — Question FK constraint for file-backed issues

`Question.issue_id` (models/question.py:16) has `ForeignKey("issues.id")` which fails for file-backed issues stored in `.manager_ai/issues/` instead of the DB `issues` table.

**Recommended: Option A — Remove the FK constraint only**

Change from:
```python
issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id"), nullable=False)
```
To:
```python
issue_id: Mapped[str] = mapped_column(String(36), nullable=False)
```

The `ForeignKey` import can remain unused (no harm, will be flagged by linters but not an error) or be removed if desired. This is the simplest fix — no migration needed for SQLite (FK constraints are not enforced by default in SQLite unless `PRAGMA foreign_keys = ON` is set). We keep the column type (`String(36)`) and constraint (`nullable=False`) intact.

If a migration is desired for non-SQLite databases, add an Alembic revision that drops the FK on `issue_id`.

## Constraints

- Pipeline still runs sequentially — cleanup must not break step ordering
- No new dependencies
- Terminal recordings must still be saved before cleanup
- Fix must not introduce race with the reader task (stop reader before pop)

## Acceptance Criteria

1. After each pipeline step completes, `_sessions` dict contains one fewer entry (no leak)
2. Reader task for the step's terminal is explicitly cancelled, not just abandoned
3. `delete_project` cleans up `_sessions` dict for all project terminals
4. `ask_user_question` MCP tool works for file-backed issues (no FK constraint failure)
5. All existing tests pass
6. Pipeline execution with N steps does not accumulate N `TerminalSession` objects in memory

## Non-Goals

- Not changing the PTY lifecycle for non-pipeline terminals (WebSocket terminals are handled correctly already)
- Not introducing a general GC for `_sessions` — only fixing the known leak points
- Not rewriting the pipeline execution model