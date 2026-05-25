## Recap

Replaced PTY terminal usage in `OrchestratorService._run_agent_step()` with direct subprocess execution via `ClaudeCodeExecutor.run_streaming()`.

### What changed

**`backend/app/services/orchestrator_service.py`:**
- Removed imports: `shlex`, `tempfile`, `uuid`, `Path`, `is_wsl_shell`, `win_to_wsl_path`, `_inject_env_vars`
- Added import: `ClaudeCodeExecutor` from `app.hooks.executor`
- `_run_agent_step()` went from 143 lines to 83 lines (-42%)

**Removed code paths:**
- PTY terminal creation (`terminal_service.create()`) — replaced with `terminal_service.create_log()`
- WSL shell handling (`is_wsl_shell`, `win_to_wsl_path`, PTY-based `cd`, `_inject_env_vars`) — executor runs claude as Windows process with `cwd=project_path`
- Temp file I/O for prompt passing (`mkstemp`, `os.unlink`) — executor sends prompt via stdin
- Success/fail marker generation and buffer polling loop (`asyncio.sleep(1)` + `get_buffered_output()`) — replaced with `ExecutorResult.success` return code check
- `cat`/`type` pipe command construction

**New flow:**
1. `terminal_service.create_log()` — creates log terminal entry with asyncio.Queue, no PTY
2. `_ensure_reader()` — same reader loop, reads from queue instead of PTY
3. `ClaudeCodeExecutor.run_streaming(prompt, project_path, env_vars, on_output=push_output)` — streams stdout line-by-line to log terminal via callback
4. `terminal_service.destroy_log()` — sends None sentinel, reader exits cleanly
5. Check `result.success` for completion/failure

### Preserved contracts
- Agent identity env vars (`MANAGER_AI_AGENT_NAME`, `MANAGER_AI_AGENT_ROLE`) — memory 2100c231
- All WebSocket events with `project_id` in payload — memory 694bf6fb
- Log terminal pattern (`create_log` → `push_output` → `destroy_log`) — memory 996bfe7f
- No `--worktree` flag in executor — memory 36db79f7
- `_build_prompt()` method unchanged

### Test results
- 37/37 existing orchestrator tests pass with no modifications