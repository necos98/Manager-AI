# Pipeline Manual Start — Disable Auto-Trigger on Issue Acceptance

## Problem
When `accept_issue` is called via MCP, the default pipeline auto-starts (`trigger_type="issue_accepted"`). User wants manual control — pipeline should only start when user clicks "Start Pipeline" in the UI.

## Current State
- **MCP `accept_issue`** (`backend/app/mcp/server.py:297-314`): After accepting, calls `OrchestratorService.start_pipeline()`. Wrapped in try/except — failure does not block acceptance.
- **REST `POST /{issue_id}/accept`** (`backend/app/routers/issues.py:93-100`): Does NOT auto-start pipeline. Just accepts and returns.
- **REST `POST /{issue_id}/start-pipeline`** (`backend/app/routers/issues.py:123-135`): Manual endpoint, uses `trigger_type="manual"`. Already exists and works.
- **Frontend** (`frontend/src/features/issues/components/issue-actions.tsx:110-119`): "Start Pipeline" button already rendered for all non-terminal statuses. Calls `useStartPipeline` hook which hits the manual REST endpoint.

## Design

### Backend Change
**File:** `backend/app/mcp/server.py`
**Change:** Remove the auto-start pipeline block (lines 297-314) from `accept_issue`.

After the event emission (line 295), return the result directly instead of attempting pipeline auto-start.

Before:
```python
await event_service.emit({...})

# Auto-start default pipeline
try:
    orchestrator = OrchestratorService(session)
    pipeline_run = await orchestrator.start_pipeline(...)
    ...
except Exception:
    logger.warning(...)
```

After:
```python
await event_service.emit({...})

return {"id": issue_id, "status": issue_status}
```

### No Changes To
- `OrchestratorService.start_pipeline` — keeps working, `trigger_type` param unchanged
- `Pipeline` model — `trigger_type="issue_accepted"` stays as default for new pipeline creation
- `issue_service.py` — already has no orchestrator dependency, clean
- Frontend — "Start Pipeline" button already exists, already functional
- REST endpoints — already correct
- Tests — `test_mcp_tools.py` may need minor update if it asserts pipeline auto-start after accept

## Risk Assessment
- **Risk:** None. Memory `261c1ede` confirms auto-start is non-blocking (try/except wrapped). Removing it cannot break acceptance flow. If no default pipeline exists, acceptance already succeeded without pipeline start.
- **Rollback:** Trivial — add back the removed block.
- **Test impact:** Test `test_accept_issue_auto_starts_pipeline` in `test_mcp_tools.py` needs update to verify pipeline does NOT auto-start.