# get_active_agent MCP Tool — Implementation Plan

**Goal:** Add `get_active_agent(issue_id)` MCP tool to server.py so pipeline agents can discover their identity.

**Architecture:** Single tool function in existing `server.py`, placed in the Pipeline run tools section. Uses existing `PipelineRunService.get_runs_for_issue()` — no new service methods, no DB changes. Description already in `default_settings.json`.

**Tech Stack:** Python, FastMCP, SQLAlchemy async

---

## Implementation

### Task 1: Add `get_active_agent` MCP tool

**Files:**
- Modify: `backend/app/mcp/server.py` — add tool after `get_pipeline_run_status` (after line 1102)

**Steps:**

1. Add tool function in server.py Pipeline run tools section:

```python
@mcp.tool(description=_desc["tool.get_active_agent.description"])
async def get_active_agent(issue_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "running"), None)
        if not active:
            return {"active": None}
        steps = active["steps"]
        idx = active["current_step_index"]
        if idx >= len(steps):
            return {"active": None}
        step = steps[idx]
        return {
            "agent_name": step["agent_name"],
            "step_index": idx,
            "step_status": step["status"],
            "terminal_id": step.get("terminal_id"),
        }
```

2. Restart backend and verify the tool appears in MCP tool list.