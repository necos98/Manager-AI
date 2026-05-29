Added `get_active_agent(issue_id: str)` MCP tool to `backend/app/mcp/server.py` (lines 1105-1123).

**What changed:** New MCP tool that queries `PipelineRunService.get_runs_for_issue()` to find the currently RUNNING pipeline run for an issue and returns the current step's agent identity.

**Return shape:** `{agent_name, step_index, step_status, terminal_id}` or `{active: null}` when no active pipeline.

**Key decisions:**
- Reused existing `PipelineRunService.get_runs_for_issue()` — no new service methods needed
- Placed in Pipeline run tools section after `get_pipeline_run_status`
- `get_active_pipeline_run` tool was scoped out per user request (descriptions exist in default_settings.json but implementation deferred)
- No tests added — existing MCP/pipeline tests (20 tests) pass without regression

**Verification:** Syntax check passed. All 20 MCP and pipeline model tests green.