## Summary

Built complete frontend UI for the agent orchestration pipeline system. All 7 tasks completed.

### Created Files (7)
- `frontend/src/features/agents/components/AgentsTab.tsx` — Agent list table with create/edit/delete dialogs, seed defaults, loading/empty/error states
- `frontend/src/features/pipelines/components/PipelinesTab.tsx` — Pipeline cards with expandable step builder (agent selector + command input, up/down reorder, add/remove steps), create/delete/rename pipelines
- `frontend/src/features/pipeline-runs/components/PipelineRunButton.tsx` — Pipeline selector dropdown + Run button with edge case handling (no agents/pipelines, run already active)
- `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx` — Live step status display with status badges, step output via readOnly TerminalPanel, cancel button, polling every 2s. Handles running/completed/failed states.
- `frontend/src/features/pipeline-runs/components/AgentChat.tsx` — Agent message thread with run selector, auto-scroll, markdown rendering, auto-refresh every 3s while run active
- `frontend/src/routes/projects/$projectId/agents.tsx` — Route page for /agents
- `frontend/src/routes/projects/$projectId/pipelines.tsx` — Route page for /pipelines

### Modified Files (5)
- `frontend/src/shared/components/app-sidebar.tsx` — Added Agents (Bot icon) and Pipelines (Workflow icon) nav links
- `frontend/src/features/issues/components/issue-actions.tsx` — Added PipelineRunButton next to Run Issue button
- `frontend/src/features/issues/components/issue-detail.tsx` — Added Agent Chat tab (visible when pipeline runs exist)
- `frontend/src/routes/projects/$projectId/issues/$issueId.tsx` — Added PipelineProgress in right panel with terminal/pipeline toggle tabs
- `frontend/src/shared/context/event-context.tsx` — Added WebSocket handlers for agent_step_started/completed/failed, pipeline_completed, agent_terminal_created with query invalidation

### Backend Schema Changes (for terminal output)
- `backend/app/schemas/pipeline_run.py` — Added `terminal_id: int | None` to `PipelineStepRunResponse`
- `backend/app/services/pipeline_run_service.py` — Stores terminal_id on step_run during execution, includes terminal_id in all step responses, added steps to get_runs_for_issue response
- `frontend/src/shared/types/index.ts` — Added `terminal_id: number | null` to `PipelineStepRun`
- `frontend/src/features/pipeline-runs/hooks.ts` — Added optional `refetchInterval` to `usePipelineRuns` and `usePipelineMessages`

### Verification
- TypeScript: `tsc --noEmit` — no errors
- Build: `vite build` — success (2781 modules, 6.36s)