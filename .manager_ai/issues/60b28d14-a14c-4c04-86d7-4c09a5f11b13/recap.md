## Pipeline Agent Execution Flow Fix — Complete

### Root causes fixed

1. **Agent intents empty** — All 6 DEFAULT_AGENTS now have actionable `intent`. Previously empty string caused `MANAGER_AI_AGENT_INTENT` env var to be empty, leaving agents with no direction.

2. **get_active_pipeline_run missing** — Implemented. run-pipeline.md step 2 now works.

3. **No explicit step lifecycle** — Added `run_pipeline_step` (claim step) and `finished_pipeline_step` (signal done) MCP tools. Agents now have clear entry/exit points.

4. **No step timeout** — 30-min default, `MANAGER_AI_PIPELINE_STEP_TIMEOUT` env var.

5. **Test merge conflicts** — All 7 resolved. All 8 tests pass.

6. **_safe_flush_session silent errors** — Now logs with exc_info.

### Files changed

| File | Change |
|------|--------|
| `backend/app/services/agent_service.py` | `intent` field in all 6 DEFAULT_AGENTS, passed to Agent() in seed |
| `backend/app/services/pipeline_run_service.py` | Event-based gating, timeout, `_step_completion_events`, `set_step_completed()`, `agent_intent` in step dicts, `_safe_flush_session` logging |
| `backend/app/mcp/server.py` | 3 new tools: `get_active_pipeline_run`, `run_pipeline_step`, `finished_pipeline_step`; enhanced `get_active_agent` with `run_id`+`agent_intent` |
| `backend/app/mcp/default_settings.json` | 2 new descriptions, 3 dead ones removed |
| `.claude/commands/run-pipeline.md` | Rewritten 8-step flow |
| `claude_resources/commands/run-pipeline.md` | Synced |
| `backend/tests/test_pipeline_run_service.py` | Merge conflicts resolved |

### Agent flow (new)

1. `get_active_agent` → discover role, intent, run_id
2. `get_active_pipeline_run` → full pipeline context
3. `get_issue_details` → get issue
4. `get_pipeline_messages` → read handoffs
5. `run_pipeline_step` → claim step
6. Execute intent (using MCP tools)
7. `finished_pipeline_step(issue_id, summary)` → signal done
8. Exit → orchestrator advances

### Tests

All 8 pipeline run service tests pass.