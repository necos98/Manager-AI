# Specification: Replace PTY with direct subprocess for agent step execution

## Problem

`OrchestratorService._run_agent_step()` creates a real PTY terminal to run `claude -p` for each pipeline step. PTY terminals are designed for interactive sessions, not one-shot command execution. This adds unnecessary overhead: PTY process management, temp file I/O for prompt passing, fragile marker-based completion detection via buffer polling, and WSL shell translation logic.

## Solution

Replace the PTY-based execution with a **log terminal + `ClaudeCodeExecutor.run_streaming()`** pattern. The log terminal provides the same frontend streaming experience without a PTY process. The executor (already used by the hook system) handles subprocess management, streaming, timeout, and error handling.

## Design

### New `_run_agent_step()` flow

1. Resolve agent, project, issue (no change)
2. Mark step `RUNNING`, emit `agent_step_started` (no change)
3. **Create log terminal** via `terminal_service.create_log(project_id, issue_id, project_path, label=f"Agent: {agent.name}")` instead of `terminal_service.create()`
4. Start reader loop via `_ensure_reader(term_id, terminal_service)` (no change — reader reads from queue in log mode)
5. Emit `agent_terminal_created` (no change — frontend connects to same WebSocket)
6. Build prompt via `_build_prompt()` (no change)
7. Build env vars dict with `MANAGER_AI_TERMINAL_ID`, `MANAGER_AI_ISSUE_ID`, `MANAGER_AI_PROJECT_ID`, `MANAGER_AI_AGENT_NAME`, `MANAGER_AI_AGENT_ROLE`, `MANAGER_AI_BASE_URL`
8. Call `ClaudeCodeExecutor().run_streaming(prompt, project_path, env_vars, on_output=callback)` where callback does `terminal_service.push_output(term_id, text)`
9. Call `terminal_service.destroy_log(term_id)` — sends `None` sentinel, reader loop exits cleanly
10. Check `result.success` → emit `agent_step_completed` or `agent_step_failed`

### Removed code

- `terminal_service.create()` call and PTY retrieval
- Temp file creation (`mkstemp`) and cleanup (`os.unlink`)
- Success/fail marker generation and injection into prompt
- `cat`/`type` pipe command construction for WSL/Windows
- WSL path translation (`win_to_wsl_path`) and `cd` command
- PTY env var injection (`_inject_env_vars` writes to PTY stdin)
- 1-second sleep poll loop with `get_buffered_output()` marker scanning
- `is_alive()` check

### Preserved contracts

- **Agent identity** (memory `2100c231`): `MANAGER_AI_AGENT_NAME` and `MANAGER_AI_AGENT_ROLE` env vars passed to executor
- **Events**: `agent_step_started`, `agent_terminal_created`, `agent_step_completed`, `agent_step_failed` — all with `project_id` in payload (memory `694bf6fb`)
- **Log terminal pattern** (memory `996bfe7f`): `create_log` → `push_output` → `destroy_log` with `None` sentinel
- **No worktree flag** (memory `36db79f7`): executor runs without `--worktree`

### Error handling

Executor already handles all failure modes: timeout (process tree kill), claude not found, non-zero exit code. All return `ExecutorResult(success=False, error=...)`. The step is marked `FAILED` with the error message from the executor result.

### WSL

WSL shell handling is removed. The executor runs `claude` as a Windows process with `cwd=project_path`. Claude Code on Windows accesses project files directly via Windows paths — no translation needed. This is correct because `claude` is a Windows executable; the project shell setting is for interactive terminals, not agent execution.

## Files changed

- `backend/app/services/orchestrator_service.py` — `_run_agent_step()` method (lines 331-473)

## Files referenced (no changes)

- `backend/app/hooks/executor.py` — `ClaudeCodeExecutor.run_streaming()` (already supports streaming with `on_output` callback)
- `backend/app/services/terminal_service.py` — `create_log()`, `push_output()`, `destroy_log()` (already implemented)