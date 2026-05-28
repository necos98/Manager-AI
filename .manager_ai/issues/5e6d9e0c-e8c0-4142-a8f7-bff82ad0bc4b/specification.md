# Pipeline: use PTY terminal with configurable command instead of hardcoded `claude -p`

## Problem

Pipeline `_run_step()` in `PipelineRunService` hardcodes `["claude", "-p", prompt]`. The agent's `terminal_command` (configurable per pipeline step) is only used as the "Task" field inside the constructed prompt — the actual executable is always `claude -p`.

This means:
1. User cannot configure what command runs per agent step
2. If `claude -p` fails or produces only stderr, terminal stays blank (stderr goes to logger, not terminal)
3. `_safe_flush_session` silently swallows errors, hiding root causes

"Run Issue" already works correctly: it creates a PTY terminal with a real shell, injects TerminalCommand entries (with variable substitution), and streams output. Pipeline should follow the same pattern.

## Root Cause

`_run_step()` at `pipeline_run_service.py:259-338`:
- Builds a prompt string from `system_prompt + command + issue_id + run_id`
- Hardcodes `cmd = ["claude", "-p", prompt]`
- Uses `create_subprocess_exec` (arg list, no shell)
- stdout → terminal via `push_output()`; stderr → Python logger only

This is fundamentally different from the proven "Run Issue" pattern.

## Fix

### 1. Replace log terminal with PTY terminal for pipeline steps

In `_execute()`, replace `terminal_service.create_log()` with `terminal_service.create()` to spawn a real PTY terminal (shell). The PTY handles command execution, output streaming, and lifecycle.

### 2. Inject `terminal_command` into the PTY (same logic as `create_terminal`)

After creating the PTY, write the step's `terminal_command` (with `$issue_id`, `$project_id`, `$project_path` substituted) into the PTY, followed by `\r\n`. The shell executes it. This matches the exact logic in `create_terminal()` at `terminals.py:310-352`.

The user controls the full command via the agent/pipeline step `terminal_command` field. Example:
```
claude -p "Write specification for issue $issue_id"
```
Or any other CLI tool.

### 3. Remove `_run_step()` subprocess logic

With PTY executing the command, `_run_step()`'s `create_subprocess_exec`, `stream_output()`, and `drain_stderr()` are no longer needed. PTY reader already streams output to WebSocket. Command completion is detected via PTY EOF (`pty_dead` event).

### 4. Keep `_safe_flush_session` error logging

Add `logger.warning` in the except block of `_safe_flush_session` so future flush failures are visible.

## Files to change

- `backend/app/services/pipeline_run_service.py` — main change: switch from log terminal + subprocess to PTY terminal + command injection
- `backend/app/services/terminal_service.py` — no changes needed (already supports `create()` with shell)
- `backend/app/routers/terminals.py` — no changes needed (PTY reader and command injection already exist)

## Behavior after fix

1. User clicks "Start Pipeline"
2. For each step: PTY terminal spawns with shell (cmd.exe or bash per project config)
3. `terminal_command` is written to the PTY as shell input
4. Shell executes the command; output streams to frontend via existing PTY reader
5. When command exits, PTY closes, step marked complete
6. User sees full terminal output including errors

## Edge cases

- **WSL projects**: PTY already supports WSL shells (`is_wsl_shell` check in `create_terminal`)
- **Empty terminal_command**: Step completes immediately with no output (graceful no-op)
- **Long-running commands**: Existing `DEFAULT_STEP_TIMEOUT` (1800s) applies — kill PTY on timeout
- **Command failure**: Non-zero exit code → step marked FAILED (detectable from PTY exit)