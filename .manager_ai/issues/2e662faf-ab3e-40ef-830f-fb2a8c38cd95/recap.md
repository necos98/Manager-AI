## Testing Results: PASS

**What was tested:**
- `test_issue_service_hooks.py` (5 tests) — all pass. `test_complete_issue_fires_hook` validates `assert_called_once()` confirming hook fires exactly once after fix.
- `test_r2_mcp_transactions.py` (4 tests) — all pass. MCP tool error paths work correctly.
- Full backend suite (637 tests) — no regressions from this change. All failures are pre-existing (router/dashboard tests, unrelated).

**Change verified:**
- Duplicate `HookEvent.ISSUE_COMPLETED` fire removed from `backend/app/mcp/server.py` `complete_issue` tool
- `project`/`project_name` dead variables cleaned up
- Service layer fires hook once at `issue_service.py:367`
- WebSocket event emit preserved
- `force_finish_issue` unaffected