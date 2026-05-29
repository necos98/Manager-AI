# Specification: get_active_agent MCP Tool

## Problem

When an agent runs inside a pipeline step via terminal, it has no way to discover which agent role it's currently acting as. The `MANAGER_AI_AGENT_NAME` env var is set in the PTY, but the Claude Code MCP client cannot read env vars from within the terminal session. An MCP tool is needed so the agent can query its own identity.

## Design

Add a single MCP tool `get_active_agent(issue_id: str) -> dict` to the Manager AI MCP server.

### Query Logic

1. Look up all pipeline runs for the given `issue_id` via `PipelineRunService.get_runs_for_issue()`
2. Filter for the run with `status == "running"`
3. Read `current_step_index` from the run
4. Get the step at that index from the run's steps array
5. Return agent identity details

### Return Shape

```json
{
  "agent_name": "SpecWriter",
  "step_index": 0,
  "step_status": "running",
  "terminal_id": "abc123..."
}
```

Returns `{"active": null}` when no pipeline is running for the issue.

### Implementation

- **File**: `backend/app/mcp/server.py`
- **Lines**: ~15 lines, placed in the existing Pipeline run tools section (after line 1122)
- **Dependencies**: `PipelineRunService` already imported; `async_session` already available
- **Description**: Already defined in `default_settings.json` at key `tool.get_active_agent.description`

### Edge Cases

- No pipeline run exists for issue → return `{"active": null}`
- Pipeline exists but status is COMPLETED/FAILED → return `{"active": null}`
- `current_step_index` out of bounds (shouldn't happen, but guard) → return `{"active": null}`

### What This Does NOT Cover

- `get_active_pipeline_run` tool (descriptions exist in settings but explicitly scoped out per user request)
- Multi-agent concurrent steps (current design assumes one step running at a time)