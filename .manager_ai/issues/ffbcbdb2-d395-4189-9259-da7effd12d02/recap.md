Extracted duplicated project-scan loop from 3 MCP tools (`update_task_status`, `update_task_name`, `delete_task`) into shared `_find_task_issue(session, task_id)` helper in `backend/app/mcp/server.py`.

**Changes:**
- Added `from typing import Any` for return type annotation
- Inserted `_find_task_issue` helper (lines 69-80) between `_serialize_pipeline` and `mcp_tool_wrapper`
- Replaced 3 × 9-line inline scan blocks with 1-line helper calls
- Removed redundant `# Find owning issue before deletion` comment in `delete_task`
- Preserved `issue_rec` variable name in `update_task_status` (matches existing scope)
- Lazy import `from app.storage import issue_store as _is` kept inside helper body

**Results:** 27 lines removed (12-line helper + 3 one-liners replace 27 lines of duped code). MCP tests pass (test_mcp_events.py 5/5, test_mcp_tools.py 16/16). Return dict shapes identical. No behavioral changes.