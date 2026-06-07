## Implementation Plan: Windows PTY Exit Race Fix

**Goal:** Fix race condition where separate `exit` write kills Windows PTY before agent finishes.

**Architecture:** Single-line change in `pipeline_run_service.py:_run_step()` — merge two `pty.write()` calls into one using `&` chaining for cmd.exe. Identical semantics to existing bash `;` path.

**Scope:** 1 file, ~3 lines changed. No new files, no schema changes, no DB migrations.

---
### Task 1: Fix exit chaining in _run_step()

- [ ] **Read _run_step() to confirm exact code**
      Read `backend/app/services/pipeline_run_service.py` lines ~565-572 to verify the current Windows/Linux branching.

- [ ] **Apply fix: merge exit into same write for Windows**
      Change Windows path from two writes to single write with `& exit`:
      ```python
      # Before:
      pty.write(f"{command}\r\n")
      pty.write("exit\r\n")
      
      # After:
      pty.write(f"{command} & exit\r\n")
      ```

- [ ] **Run existing tests to verify no regression**
      `cd backend && python -m pytest tests/ -v --timeout=60`
      Expected: all tests pass

- [ ] **Commit**
      `git add backend/app/services/pipeline_run_service.py`
      `git commit -m "fix: merge exit into same pty.write() for Windows pipeline steps"`
