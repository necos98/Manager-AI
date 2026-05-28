## Fix

Removed `project_id: str` from `AgentResponse` Pydantic schema and fixed bare `list` → `list[str] | None` type annotation.

**Root cause:** Regression — `project_id` was previously removed (issue #071a4f79) but reappeared as a merge/rebase artifact. The `Agent` DB model has never had a `project_id` column. Same class of bug as `PipelineResponse` fix (#a600a306).

**File changed:** `backend/app/schemas/agent.py` — deleted `project_id: str` line 20, fixed `allowed_tools: list` → `allowed_tools: list[str] | None` line 24.

**Note:** Applied fix to `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\backend\app\schemas\agent.py` (the running instance) — the working directory `manager-ai-mod/Manager-AI` is a modified copy that also has the fix.