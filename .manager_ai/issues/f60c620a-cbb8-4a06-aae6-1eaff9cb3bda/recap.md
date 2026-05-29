## Change

One-line change in `_run_step()` (`pipeline_run_service.py:324-328`): when agent PTY dies before calling `finished_pipeline_step`, step now **FAILED** instead of succeeding.

Before:
```python
success = session.pty_died_naturally  # always True for natural PTY exit
```

After:
```python
success = False
```

Also changed log level from `warning` to `error`.

## Rationale

`finished_pipeline_step` is the documented protocol for step completion. PTY death without the event means the agent didn't complete its work. Previously the step succeeded anyway because `pty_died_naturally` was always `True` for natural PTY exits — this masked agents that crashed, skipped protocol, or had network issues.

All 8 existing tests pass. Memory cb0b9511 updated to reflect the new strict behavior.