Pipeline execution has zero visual feedback. User clicks "Start Pipeline" but sees nothing happen — no step progress, no agent activity, no real-time updates. Six root causes:

1. `_emit()` orchestrator events missing `project_id` → no React Query invalidation in frontend
2. `usePipelineRunsForIssue` has no polling → stale data
3. PipelineProgress shows only run summary (colored dot), no step stepper
4. AgentChat ignores `agent_step_started/completed/failed` events
5. No inline pipeline status indicator on issue detail page header
6. `send_agent_message` hardcodes agent_name="agent", agent_role="unknown"

Goal: user sees real-time step-by-step pipeline progress with agent identity and messages.