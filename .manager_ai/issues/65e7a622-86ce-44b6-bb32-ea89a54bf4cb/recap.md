## Fix

Changed `"running"` → `"RUNNING"` on line 1110 of `backend/app/mcp/server.py`.

## Root Cause

`get_active_agent(issue_id)` used lowercase `"running"` in status comparison, but `PipelineRunStatus` enum values are uppercase (`"RUNNING"`). `get_runs_for_issue()` returns `r.status.value` = `"RUNNING"`, so the comparison always failed and the tool always returned `{"active": null}`.

## Why it was missed

Frontend consistently uses uppercase `"RUNNING"`. Single-character typo with no runtime error — just silent null return.

## Verification

- Grep confirmed no other lowercase `"running"` comparisons in `server.py`
- Backend tests: 181 passed (1 unrelated pre-existing failure in test_db_backup.py)
