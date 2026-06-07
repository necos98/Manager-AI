## Recap: Fix PlanWriter pipeline stall

### Changes made
1. **Removed `accept_issue` from PlanWriter's allowed_tools** — Prevents PlanWriter from calling `accept_issue` even if intent text ever regresses. Lifecycle management stays in /run-pipeline command.

2. **Defensive fallback in `finished_pipeline_step` MCP tool** — `server.py:1286-1303`: when no RUNNING pipeline run found for issue, checks if issue status is ACCEPTED. If so, returns success with warning instead of error. Prevents silent stalls if the pattern recurs.

3. **Tests added** — Two new tests in `test_pipeline_run_service.py`:
   - `test_finished_pipeline_step_accepts_accepted_issue` — verifies ACCEPTED issue without RUNNING run returns success
   - `test_finished_pipeline_step_errors_for_new_issue` — verifies non-ACCEPTED issue still returns error

### Current state
- PlanWriter intent + allowed_tools both clean of `accept_issue`
- `finished_pipeline_step` handles the edge case defensively
- Existing memory `de943f40` updated to cover `allowed_tools` policy
- New memory `5904cf0c` documents defensive fallback

### What was NOT changed
- `agent_service.py` DEFAULT_AGENTS seed (already clean)
- `_run_step()` three-way wait mechanism (unchanged)
- `accept_issue` MCP tool itself (unchanged)
- Pipeline step completion protocol (unchanged)