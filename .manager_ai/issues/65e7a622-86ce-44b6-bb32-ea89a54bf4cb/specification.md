## Problem

When launching a pipeline from the issue UI, the `/run-pipeline` command executed in the PTY calls `get_active_agent(issue_id)` via MCP, which always returns `{"active": null}`. The pipeline run exists in the database, but the lookup fails.

## Root Cause

`backend/app/mcp/server.py` line 1110:

```python
active = next((r for r in runs if r["status"] == "running"), None)
```

`PipelineRunStatus` is a `str` enum with **uppercase** values (`"RUNNING"`, `"COMPLETED"`, `"FAILED"`). `get_runs_for_issue()` returns `r.status.value` = `"RUNNING"`. But the comparison uses lowercase `"running"`, which never matches.

## Scope

- Single file: `backend/app/mcp/server.py`
- Single line change: `"running"` → `"RUNNING"`

## Acceptance Criteria

- `get_active_agent(issue_id)` returns agent info when a pipeline is RUNNING for that issue
- Frontend uses uppercase `"RUNNING"` consistently — no changes needed there
