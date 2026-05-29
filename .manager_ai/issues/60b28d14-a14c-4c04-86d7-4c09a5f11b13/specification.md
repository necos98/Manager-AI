# Pipeline Agent Execution Flow Fix

## Problem

User ran pipeline manually. Agent was confused — tried calling tools without success, no clear direction. Pipeline flow is broken at multiple levels.

## Root Causes

1. **Agent intents empty** — All 5 `DEFAULT_AGENTS` seed with `intent=""`. `MANAGER_AI_AGENT_INTENT` env var written to PTY is empty string. Agent has zero guidance on what to do.

2. **`get_active_pipeline_run` not implemented** — Description exists in `default_settings.json` (L74), but no `@mcp.tool` implementation in `server.py`. run-pipeline.md step 2 calls it → agent gets tool-not-found error.

3. **`run_pipeline_step` / `finished_pipeline_step` do not exist** — No explicit step lifecycle tools. Currently step advance is implicit (PTY exit). Agent has no way to claim or complete a step explicitly.

4. **No step timeout** — `_run_step()` does `await session.pty_dead.wait()` with no timeout. Agent can hang indefinitely if it gets stuck.

5. **Test file has git merge conflicts** — `test_pipeline_run_service.py` contains `<<<<<<<` / `=======` / `>>>>>>>` markers. Tests unparseable.

6. **`_safe_flush_session` swallows errors** — Catches all exceptions, rolls back, re-flushes without logging. Debugging impossible when DB writes fail silently.

## Design

### 1. Populate agent intents

In `agent_service.py` DEFAULT_AGENTS, add clear, actionable `intent` for each agent:

| Agent | Intent |
|-------|--------|
| SpecWriter | Analyze the issue description, ask clarifying questions if needed, write a detailed specification covering requirements, constraints, and success criteria. Save via `create_issue_spec`. Set issue name via `set_issue_name`. |
| Architect | Review the specification. Design an implementation plan with concrete steps, identify files to create/modify, and define atomic tasks. Save via `create_issue_plan` and `create_plan_tasks`. |
| Developer | Read the plan tasks via `get_plan_tasks`. Implement each task sequentially — update status to "In Progress" when starting, "Completed" when done. Follow existing codebase patterns. Make autonomous decisions. Do NOT ask for confirmations. |
| Reviewer | Review all code changes for bugs, logic errors, security issues, and adherence to project conventions. Run the test suite. Report findings via `send_agent_message` with specific, actionable feedback for the QA agent. |
| QA | Run tests, verify behavior against the specification, check edge cases. If issues found, report them. If all passes, confirm ready for completion. Report via `send_agent_message`. |

### 2. New MCP tools (server.py)

**`get_active_pipeline_run(issue_id)`**
- Already described in `default_settings.json` L74, just needs implementation
- Returns: `{run_id, pipeline_id, issue_id, status, current_step_index, steps: [{step_run_id, agent_name, status, order_index, terminal_id}], started_at}`
- Returns `null` if no running pipeline for this issue

**`run_pipeline_step(issue_id)`**
- Agent calls this to claim its current step
- Marks `PipelineStepRun.status = RUNNING` in DB
- Returns: `{run_id, step_run_id, agent_name, agent_intent, step_index, terminal_id}`
- Returns `{active: null}` if no active pipeline for this issue

**`finished_pipeline_step(issue_id, summary)`**
- Agent calls this to signal step completion
- Sets the `asyncio.Event` that `_run_step()` awaits (unblocks orchestrator)
- Marks step as COMPLETED in DB
- Saves `summary` as a `PipelineMessage` (handoff to next agent)
- Returns: `{success: true, step_completed: true, pipeline_finished: false/true}`

### 3. Orchestrator: event-based step gating (pipeline_run_service.py)

Replace `await session.pty_dead.wait()` with:

```python
_step_completion_events: dict[tuple[str, int], asyncio.Event] = {}

# In _run_step():
event = asyncio.Event()
_step_completion_events[(run_id, step_index)] = event
try:
    await asyncio.wait_for(event.wait(), timeout=step_timeout)
    success = True
except asyncio.TimeoutError:
    logger.error("Step %s timed out after %ds", agent_name, step_timeout)
    success = False
finally:
    _step_completion_events.pop((run_id, step_index), None)
```

PTY death monitored as secondary signal: if PTY dies before event is set, treat as failure (agent crashed).

Add method: `set_step_completed(run_id, step_index)` — called by `finished_pipeline_step` MCP tool.

### 4. Updated run-pipeline.md

Rewrite to match actual available tools:

1. Call `get_active_agent(issue_id)` — discover agent name, intent, step_index, terminal_id, run_id
2. Call `get_active_pipeline_run(issue_id)` — see full pipeline context (all steps, statuses, agent names)
3. Call `get_issue_details(project_id, issue_id)` — get the issue
4. Call `get_pipeline_messages(run_id)` — read handoff messages from prior agents
5. **Call `run_pipeline_step(issue_id)`** — claim this step, get back agent_intent
6. Execute intent — follow agent_intent to the letter using available MCP tools
7. **Call `finished_pipeline_step(issue_id, summary)`** — signal completion with summary for next agent
8. Exit — orchestrator auto-advances to next step

Also sync `claude_resources/commands/run-pipeline.md`.

### 5. Step timeout

- Default: 30 minutes (1800s) per step
- Configurable via `MANAGER_AI_PIPELINE_STEP_TIMEOUT` env var (seconds)
- On timeout: mark step as FAILED, kill terminal, mark run as FAILED

### 6. Fix test merge conflicts

Resolve conflict markers in `backend/tests/test_pipeline_run_service.py` by accepting the current/stashed version that matches the implemented code.

### 7. _safe_flush_session logging

Add `logger.warning("_safe_flush_session: flush failed, rolling back", exc_info=True)` in the except block for debuggability.

### 8. Cleanup: remove dead MCP tool descriptions

Remove from `default_settings.json`:
- `tool.get_agent.description` (L65) — described, never implemented, unreferenced
- `tool.update_agent.description` (L66) — described, never implemented, unreferenced
- `tool.delete_agent.description` (L67) — described, never implemented, unreferenced

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/agent_service.py` | Populate `intent` in DEFAULT_AGENTS |
| `backend/app/mcp/server.py` | Add `get_active_pipeline_run`, `run_pipeline_step`, `finished_pipeline_step` tools |
| `backend/app/mcp/default_settings.json` | Add 2 new tool descriptions, remove 3 dead ones |
| `backend/app/services/pipeline_run_service.py` | Event gating, timeout, `set_step_completed()`, `_safe_flush_session` logging |
| `.claude/commands/run-pipeline.md` | Rewrite for explicit step tools |
| `claude_resources/commands/run-pipeline.md` | Sync copy |
| `backend/tests/test_pipeline_run_service.py` | Fix merge conflicts |

## Out of Scope

- `terminal_command` model/DB column mismatch (cosmetic, engine hardcodes correctly)
- `MANAGER_AI_AGENT_ROLE` = `MANAGER_AI_AGENT_NAME` redundancy (minor)
- Stale RUNNING run cleanup on startup (separate issue)
- Implementing `get_agent`/`update_agent`/`delete_agent` MCP tools (not needed for pipeline flow)
