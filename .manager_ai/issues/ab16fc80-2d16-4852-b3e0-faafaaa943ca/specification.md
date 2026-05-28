## Root Cause

`AgentResponse` Pydantic schema (`backend/app/schemas/agent.py:20`) has `project_id: str` as a required field. But the `Agent` DB model (`backend/app/models/agent.py`) has no `project_id` column — agents are not project-scoped. The `_response()` helper in `agents.py` doesn't pass `project_id`, causing a Pydantic `ValidationError` on `GET /api/agents`.

This is a **regression**. Memory `40a6575a` confirms `project_id` was previously removed from `AgentResponse` (issue #071a4f79) but reappeared — the same class of merge/rebase artifact that hit `PipelineResponse` (issue #a600a306).

## Fix

1. **Remove `project_id: str`** from `AgentResponse` schema (line 20).
2. **Fix `allowed_tools` type annotation** from bare `list` to `list[str] | None` for type consistency with the rest of the schema.

## Files changed

| File | Change |
|------|--------|
| `backend/app/schemas/agent.py:20` | Delete `project_id: str` |
| `backend/app/schemas/agent.py:24` | `allowed_tools: list` → `allowed_tools: list[str] \| None` |

No router, model, or service changes needed.