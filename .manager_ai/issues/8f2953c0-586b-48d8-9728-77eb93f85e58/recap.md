## Changes Made

### Backend: `backend/app/mcp/server.py`
Removed the auto-start pipeline block (try/except calling `OrchestratorService.start_pipeline`) from the `accept_issue` MCP tool. After emitting the status change event, the function now returns `{"id": issue_id, "status": issue_status}` directly — no pipeline auto-trigger.

### Test: `backend/tests/test_orchestrator.py`
Renamed `test_mcp_accept_issue_triggers_pipeline` → `test_mcp_accept_issue_does_not_auto_start_pipeline`. Updated assertions: verifies `pipeline_run_id` is NOT in result, and no PipelineRun rows exist for the issue after accept.

### What Was NOT Changed
- REST `POST /{issue_id}/accept` — already didn't auto-start
- REST `POST /{issue_id}/start-pipeline` (manual) — already works
- Frontend "Start Pipeline" button — already exists and functional
- `OrchestratorService.start_pipeline` — unchanged
- `IssueService.accept_issue` — unchanged, no orchestrator dependency

### Test Results
- All 37 orchestrator tests pass
- All 11 MCP tools tests pass