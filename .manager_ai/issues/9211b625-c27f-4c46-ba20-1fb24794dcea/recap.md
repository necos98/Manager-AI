## Changes

### Backend
**`orchestrator_service.py`** — `_emit()` now takes `project_id` keyword arg and includes it in payload. `_run_pipeline()` resolves `project_id` from pipeline record and passes it to both `pipeline_paused`/`pipeline_completed` emits. `_run_agent_step()` accepts `project_id`, passes to all three `agent_step_*` emits. Also passes `MANAGER_AI_AGENT_NAME` and `MANAGER_AI_AGENT_ROLE` env vars to Claude Code subprocess.

**`server.py`** — `send_agent_message` reads agent identity from `MANAGER_AI_AGENT_NAME`/`MANAGER_AI_AGENT_ROLE` env vars (was hardcoded `"agent"/"unknown"`). Adds `project_id` to event payload from `MANAGER_AI_PROJECT_ID`. Added `import os`.

### Frontend
**`hooks.ts`** — `usePipelineRunsForIssue` now has `refetchInterval: 3000` (was 0 — no polling).

**`pipeline-progress.tsx`** — Replaced summary-only view with vertical timeline step stepper. Uses `usePipelineRun(latestRun.id)` for step-level data. Shows agent name, role, status icon (spinner/check/X/dot), colored connector lines, summary on hover, error text. Keeps previous runs list.

**`agent-chat.tsx`** — Added discriminated union `Message = ChatMessage | SystemMessage`. Subscribes to `agent_step_started/completed/failed` events. Renders system messages as muted italic `[Pipeline] <Agent> <action>` entries. Deduplicates by `eventType-stepId`.

**`issue-detail.tsx`** — Pipeline status badge above tabs: shows "Pipeline: Running (Step X/Y — Agent)" during run, "Pipeline: Completed/Failed" otherwise. Clickable to switch to pipeline tab. Tabs now controlled via `activeTab` state.

**`event-context.tsx`** — Added `agent_step_started/completed/failed`, `pipeline_completed`, `pipeline_paused` to silent case block. These events now trigger React Query invalidation (because `project_id` is now in payload) without producing toasts.

### Root cause chain fixed
1. Backend `_emit()` missing `project_id` → EventProvider line 299 `if (projectId && issueId)` was false → no React Query invalidation
2. No polling on `usePipelineRunsForIssue` → stale data even after manual refresh
3. PipelineProgress had TODO for step stepper → only colored dot
4. AgentChat ignored step lifecycle events → no progress visibility in chat
5. No pipeline indicator outside Pipeline tab → user had to manually navigate
6. `send_agent_message` hardcoded identity → all messages showed "agent (unknown)"

### Test results
- Backend: 181 passed, 1 pre-existing failure (test_db_backup unrelated)
- Orchestrator: 36/37 passed, 1 pre-existing failure (fixture issue)
- Frontend: TypeScript compiles clean, no errors