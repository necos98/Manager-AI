# Plan: PTY death without finished_pipeline_step = FAILED

## Files

- **Modify:** `backend/app/services/pipeline_run_service.py:324-328`
- **Verify:** `backend/tests/test_pipeline_run_service.py` (existing tests must still pass)

## Tasks

### Task 1: Change PTY-death fallback from success to failure

**File:** `backend/app/services/pipeline_run_service.py`

Lines 324-328, change:

```python
elif pty_task in done:
    logger.warning(
        "Step %s PTY died before finished_pipeline_step called", agent_name
    )
    success = session.pty_died_naturally
```

To:

```python
elif pty_task in done:
    logger.error(
        "Step %s failed: PTY died before finished_pipeline_step called", agent_name
    )
    success = False
```

### Task 2: Run existing tests

Command: `cd backend && python -m pytest tests/test_pipeline_run_service.py -v`

All existing tests must pass.

### Task 3: Verify TerminalSession.pty_died_naturally still functional

`pty_died_naturally` field remains on `TerminalSession`. Still set in `_terminal_reader()` at lines 119 and 143. Still read by `routers/terminals.py:604`. The only consumer removed is `_run_step()` in `pipeline_run_service.py`. No other code paths affected.