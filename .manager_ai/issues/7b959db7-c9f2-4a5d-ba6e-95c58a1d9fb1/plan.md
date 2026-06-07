## Plan: Fix PlanWriter pipeline stall

**Goal:** Remove `accept_issue` from PlanWriter's allowed_tools and add defensive handling in `finished_pipeline_step` to prevent pipeline stalls.

**Architecture:** Two changes: (1) update PlanWriter agent config to remove `accept_issue` tool access; (2) add a graceful path in `finish_step()` when no active step run exists but issue is ACCEPTED.

**Tech Stack:** Python/FastAPI backend, SQLAlchemy async

### Files
- Modify: `backend/app/services/pipeline_run_service.py` — `finish_step()` method
- Modify: `backend/app/services/agent_service.py` — DEFAULT_AGENTS PlanWriter allowed_tools (if present)
- DB: Update PlanWriter agent via `update_agent` MCP tool

### Tasks
1. Remove `accept_issue` from PlanWriter's allowed_tools (MCP update + DEFAULT_AGENTS if needed)
2. Add defensive check in `finish_step()`: when no active step run found, check issue ACCEPTED status
3. Write tests for the defensive fix
4. Run tests to verify
5. Write memory documenting the changes
