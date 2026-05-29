## Issue: Pipeline PTY not spawning like RUN ISSUE flow

### Problem
`_run_step()` used `asyncio.create_subprocess_shell()` (headless) + `create_log()` (virtual terminal) instead of real PTY terminals. User wanted pipeline steps to use `claude --dangerously-skip-permissions "/run-pipeline $issue_id"` in real PTY like "RUN ISSUE" flow.

### Changes

**`backend/app/services/pipeline_run_service.py`:**
- `_execute()`: replaced `terminal_service.create_log()` with `terminal_service.create()` for real PTY
- `_execute()`: removed all `destroy_log()` calls (PTY auto-cleans via `mark_closed()` on process exit)
- `_execute()`: added `terminal_service.kill(term_id)` in CancelledError handler
- `_run_step()`: complete rewrite — uses PTY instead of `asyncio.create_subprocess_shell`
  - Creates `TerminalSession` with `pty_dead` Event for completion detection
  - Starts reader via `_ensure_reader()`
  - Injects env vars in correct shell dialect (set/export)
  - Injects command + shell exit (`; exit` / `& exit`)
  - Awaits `session.pty_dead.wait()` for process completion
- Removed unused `import os` and `DEFAULT_STEP_TIMEOUT` constant

**`backend/app/services/agent_service.py`:**
- All 6 DEFAULT_AGENTS: `terminal_command` changed from `claude -p "task description"` to `claude --dangerously-skip-permissions "/run-pipeline $issue_id"`

### Test results
- All 8 pipeline run service tests pass
- No regressions in pipeline-related tests

### Runtime steps for user
1. Restart backend
2. Delete existing pipeline (UI or API)
3. Restart backend again to reseed agents + pipeline with new DEFAULT_AGENTS
4. Pipeline steps now use real PTY terminals with `claude --dangerously-skip-permissions "/run-pipeline $issue_id"`
