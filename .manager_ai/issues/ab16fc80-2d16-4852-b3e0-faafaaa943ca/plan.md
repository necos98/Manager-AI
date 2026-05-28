## Plan

Single-file fix. Two lines changed in `backend/app/schemas/agent.py`.

### Task 1: Remove `project_id` and fix `allowed_tools` type in AgentResponse

**Files:**
- Modify: `backend/app/schemas/agent.py:20,24`

**Step 1: Remove `project_id: str` (line 20)**
Delete the field. The Agent model has no `project_id` column — agents are not project-scoped.

**Step 2: Fix `allowed_tools` type annotation (line 24)**
Change `allowed_tools: list` → `allowed_tools: list[str] | None` for type consistency.

**Step 3: Verify**
Run existing agent tests to confirm no regressions:
```
cd backend && python -m pytest tests/ -k "agent" -v
```

**Step 4: Commit**
```
git commit -m "fix: remove stale project_id from AgentResponse schema

Regression from merge/rebase artifact — same class as PipelineResponse
fix in #a600a306. Agent model has no project_id column.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```