## Recap: Refactor mcp/server.py — Extract Duplicated Patterns

### What was done

Pure extraction refactor of `backend/app/mcp/server.py` (~1486→~1215 lines):

1. **`_issue_display_name(issue, max_len=50)`** — Extracted 11 inline `issue.name or (issue.description or "")[:N] or ""` expressions into one helper function. Signatures all preserved. The `max_len=100` variant at the `complete_issue` data extraction dict stays correct.

2. **`_serialize_agent(agent)`** — Replaced 4 identical agent-serialization dicts (in create_agent, list_agents, get_agent, update_agent). Preserves `str()` format for timestamps (not `.isoformat()`).

3. **`_serialize_pipeline(pipeline)`** — Replaced 6 identical pipeline-serialization dicts (in create_pipeline, list_pipelines, get_pipeline, update_pipeline, add_step, reorder_steps). Uses `pipeline.steps or []`.

4. **`@mcp_tool_wrapper` decorator** — Applied to 23 tools that fit the async-session/try/except/commit pattern. Handles session creation + AppError conversion. Inner function receives `session` as first param. Tools with before-commit extraction (complete_issue, accept_issue, cancel_issue, force_finish_issue) call `commit()` inside the body. Decorator not applied to tools with complex shapes (create_issue, task tools, memory tools, plugin tools, question tools, pipeline-run tools).

### Verification

- Python syntax check: OK
- All 22 MCP-specific tests pass (test_mcp_tools.py, test_mcp_events.py, test_mcp_memory_tools.py)
- 1 pre-existing failure in test_db_backup.py (unrelated backup assertion)
- 32 pre-existing failures in REST API tests (KeyError: 'id', unrelated to MCP server)

### Key constraints preserved

- No behavioral changes — output dicts byte-identical for same inputs
- No new files — all helpers in server.py
- Event emission stayed inline per tool
- Tools not using the decorator continue unchanged