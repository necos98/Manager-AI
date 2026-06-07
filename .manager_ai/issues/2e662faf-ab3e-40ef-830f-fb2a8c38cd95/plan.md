## Implementation Plan: Remove Duplicate ISSUE_COMPLETED Hook

### File to modify
`backend/app/mcp/server.py` — `complete_issue` MCP tool (lines 130-182)

### Changes

**1. Remove redundant hook fire (lines 162-178)**
Delete lines 162-178: the `from app.hooks.registry import HookContext, HookEvent, hook_registry` import and the `hook_registry.fire(HookEvent.ISSUE_COMPLETED, ...)` call. This is a local import used only in this block — both go together.

**2. Remove dead project/project_name variables (lines 146-150)**
After removing the hook block, `project` and `project_name` are computed but never read. Remove the `try/except` block and the two variable assignments. Also remove the `from app.services.project_service import ProjectService` reference since it's imported at module level (line 18) — the local reference on line 147 can just be deleted.

### What stays unchanged
- `event_service.emit(...)` on lines 153-160 (WebSocket notification — separate from hook system)
- The `except AppError` handler on lines 181-182
- The `return` statement on line 180
- `issue_service.py` — the service correctly fires the hook once
- `force_finish_issue` — confirmed not affected
- All other MCP tools

### File after change (complete_issue function outline)
```python
@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.complete_issue(issue_id, project_id, recap)
            issue_data = {
                "name": issue.name or (issue.description or "")[:100],
                "specification": issue.specification,
                "plan": issue.plan,
                "recap": issue.recap,
            }
            issue_id_val = issue.id
            issue_name = issue.name or (issue.description or "")[:50] or ""
            issue_status = issue.status
            await session.commit()

            await event_service.emit({
                "type": "issue_status_changed",
                "new_status": issue_status,
                "project_id": project_id,
                "issue_id": issue_id_val,
                "issue_name": issue_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            return {"id": issue_id_val, "status": issue_status, "recap": issue.recap}
        except AppError as e:
            return {"error": e.message}
```

### Verification
- `HookEvent.ISSUE_COMPLETED` fires exactly once per `complete_issue` call (via `issue_service.complete_issue()`)
- No new imports needed (all required imports exist at module level)
- No test changes needed — existing tests verify behavior, not hook count
