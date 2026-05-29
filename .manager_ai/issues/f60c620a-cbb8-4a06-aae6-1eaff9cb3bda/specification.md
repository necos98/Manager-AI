# Spec: Distinguish clean vs dirty PTY death in pipeline step completion

## Problem

In `_run_step()`, when an agent exits the PTY without calling `finished_pipeline_step`, the pipeline still advances. The `pty_task` wins the `asyncio.wait()` race, and the step is treated as success because `success = session.pty_died_naturally` — which is always `True` when the PTY exits on its own.

This masks agents that:
- Don't follow the documented `finished_pipeline_step` protocol
- Crash or exit prematurely without completing work
- Have network issues that prevent the MCP call

## Design Decision

**Approach: Always FAIL when PTY dies without `finished_pipeline_step`.**

Rejected alternatives:
- **Exit code check**: pywinpty on Windows doesn't expose subprocess exit codes cleanly. Not viable.
- **Grace period**: Agent runs inside PTY and calls `finished_pipeline_step` via MCP before claude exits. If PTY dies first, agent never signaled — extra wait won't help. Adds complexity for no gain.

## Change

**File:** `backend/app/services/pipeline_run_service.py` ~line 324-328

```python
# Before
elif pty_task in done:
    logger.warning(
        "Step %s PTY died before finished_pipeline_step called", agent_name
    )
    success = session.pty_died_naturally

# After
elif pty_task in done:
    logger.error(
        "Step %s failed: PTY died before finished_pipeline_step called", agent_name
    )
    success = False
```

**Rationale:**
- `finished_pipeline_step` is the documented, explicit protocol for step completion
- PTY death without the event means the agent didn't finish its work
- Crash, network issue, agent bug = step should fail so user can investigate
- One-line change, no new configuration needed

**What stays unchanged:**
- `TerminalSession.pty_died_naturally` field — still set in `_terminal_reader()`, still used by `routers/terminals.py:604` for WebSocket endpoint logic
- Event path: `event_task` wins → `success = True` (unchanged)
- Timeout path: timeout → `success = False` (unchanged)
- `_step_completion_events` dict management (unchanged)

**Test impact:**
- Any test that asserts PTY-death-without-event = step success must be updated to expect failure