## Root cause

`_run_step()` hardcoded `["claude", "-p", prompt]`, ignoring user's configurable `terminal_command`. The `terminal_command` field was only used as a "Task" description embedded inside the prompt. User cannot choose what command runs. Also:
- stderr went to Python logger only (invisible in terminal)
- `_safe_flush_session` silently swallowed flush errors

## Changes made

### 1. `_safe_flush_session` error logging (`pipeline_run_service.py:252-258`)
Added `logger.warning(..., exc_info=True)` in the except block so flush failures are visible.

### 2. `DEFAULT_AGENTS` executable commands (`agent_service.py:7-73`)
Changed `terminal_command` from bare task descriptions to actual shell commands:
- Before: `"Write a detailed specification for issue $issue_id..."`
- After: `claude -p "Write a detailed specification for issue $issue_id..."`

### 3. `_run_step()` rewrite (`pipeline_run_service.py:260-316`)
- Removed hardcoded `prompt` building and `["claude", "-p", prompt]`
- Executes `command` (the step's `terminal_command`) directly via `asyncio.create_subprocess_shell`
- Merged stderr into stdout (`stderr=asyncio.subprocess.STDOUT`) so errors are visible
- Passes `system_prompt`, `issue_id`, `run_id` as environment variables (`MANAGER_AI_SYSTEM_PROMPT`, `MANAGER_AI_ISSUE_ID`, `MANAGER_AI_RUN_ID`)
- Agent name and role still passed as `MANAGER_AI_AGENT_NAME` / `MANAGER_AI_AGENT_ROLE`
- Single pipe reader (no separate stderr drain) — simpler, all output visible

### 4. Reseed needed
Existing pipelines still have old task-description `terminal_command` values. Delete the default pipeline and restart backend to trigger reseed with new executable commands.

## Tests
All 8 tests pass (`tests/test_pipeline_run_service.py`).