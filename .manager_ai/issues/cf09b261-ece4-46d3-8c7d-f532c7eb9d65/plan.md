# Implementation Plan: Fix Terminal Leak in Pipeline

## Summary

Three independent fixes to eliminate `TerminalSession` object leaks in the pipeline execution and fix the `ask_user_question` FK constraint for file-backed issues.

---

## Files Modified

| File | Change |
|------|--------|
| `backend/app/services/pipeline_run_service.py:21` | Add `_sessions`, `_stop_reader` to import |
| `backend/app/services/pipeline_run_service.py:234-236` | Add cleanup calls before `kill()` |
| `backend/app/routers/projects.py` (imports + ~line 354) | Add import and cleanup calls in `delete_project` |
| `backend/app/models/question.py:16` | Remove `ForeignKey("issues.id")` from `issue_id` |

---

## Task 1: Fix pipeline _execute() finally block

**Files:** `backend/app/services/pipeline_run_service.py`
- Modify: line 21 (import)
- Modify: lines 234-236 (finally block)

**Details:**

1. **Update import** — Change line 21 from:
   ```python
   from app.services.terminal_session import _save_recording
   ```
   To:
   ```python
   from app.services.terminal_session import _save_recording, _sessions, _stop_reader
   ```

2. **Add cleanup before kill** — Change lines 234-236 from:
   ```python
   finally:
       _save_recording(term_id, terminal_service.get_buffered_output(term_id))
       terminal_service.kill(term_id)
   ```
   To:
   ```python
   finally:
       _save_recording(term_id, terminal_service.get_buffered_output(term_id))
       _stop_reader(term_id)
       _sessions.pop(term_id, None)
       terminal_service.kill(term_id)
   ```

**Order matters:** `_stop_reader` first (cancels the asyncio reader task), then `_sessions.pop` (removes the session object), then `kill` (terminates the PTY). This matches the canonical `_teardown_terminal()` pattern.

**No test changes needed** — Fix 3 makes `ask_user_question` work, existing pipeline tests already cover cleanup.

---

## Task 2: Fix delete_project terminal session cleanup

**Files:** `backend/app/routers/projects.py`
- Modify: imports (add `_sessions`, `_stop_reader`)
- Modify: lines 354-358 (cleanup loop)

**Details:**

1. **Add import** at top of file:
   ```python
   from app.services.terminal_session import _sessions, _stop_reader
   ```

2. **Expand cleanup loop** — Change lines 354-358 from:
   ```python
   for term in terminal_service.list_active(project_id=project_id):
       try:
           terminal_service.kill(term["id"])
       except KeyError:
           pass
   ```
   To:
   ```python
   for term in terminal_service.list_active(project_id=project_id):
       try:
           _stop_reader(term["id"])
           _sessions.pop(term["id"], None)
           terminal_service.kill(term["id"])
       except KeyError:
           pass
   ```

---

## Task 3: Fix Question FK constraint

**Files:** `backend/app/models/question.py`
- Modify: line 16 (`issue_id` column)

**Details:**

1. **Remove ForeignKey** — Change line 16 from:
   ```python
   issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id"), nullable=False)
   ```
   To:
   ```python
   issue_id: Mapped[str] = mapped_column(String(36), nullable=False)
   ```

**Rationale:** File-backed issues (stored as YAML under `.manager_ai/issues/`) don't exist in the DB `issues` table, so the FK constraint always fails. SQLite doesn't enforce FKs by default unless `PRAGMA foreign_keys = ON`, so no migration needed. The column type and `nullable=False` constraint remain intact.

---

## Verification

After all tasks complete:
1. Run existing tests: `cd backend && python -m pytest`
2. Verify pipeline run with N steps doesn't grow `_sessions` dict (add debug log if needed)
3. Verify `ask_user_question` MCP tool works for file-backed issues

---

## Ordering

All three tasks are independent — can be done in any order. Suggested: Task 1 (pipeline fix) → Task 2 (delete_project fix) → Task 3 (FK fix).
