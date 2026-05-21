# Pipeline Visual Feedback — Implementation Plan

## Backend: Fix WebSocket events and agent identity

### 1. Add `project_id` to `_emit()` payloads

`orchestrator_service.py:437-460`: `_emit()` missing `project_id` in payload — `EventProvider` line 299 checks `if (projectId && issueId)` and skips invalidation without it.

**Changes:**
- Add `project_id: str` param to `_emit()`
- Include `project_id` in payload dict
- In `_run_pipeline()`: load pipeline at start via `self.session.get(Pipeline, pipeline_run.pipeline_id)` to get `pipeline.project_id`, pass to all `_emit()` calls
- In `_run_agent_step()`: `project` already resolved at line 300, pass `project.id` as `agent.project_id` (same value)
- Update 5 call sites: `agent_step_started`, `agent_step_completed`, `agent_step_failed` in `_run_agent_step()`, `pipeline_paused` and `pipeline_completed` in `_run_pipeline()`

### 2. Fix agent identity in `send_agent_message`

`server.py:1096-1109`: hardcoded `agent_name="agent"`, `agent_role="unknown"`, event missing `project_id`.

**Changes:**
- In `_run_agent_step()`: add `MANAGER_AI_AGENT_NAME` and `MANAGER_AI_AGENT_ROLE` to `env_vars` dict passed to `executor.run()`
- In `send_agent_message`: read `os.environ.get("MANAGER_AI_AGENT_NAME", "agent")` and `"MANAGER_AI_AGENT_ROLE"`; add `project_id` from `os.environ.get("MANAGER_AI_PROJECT_ID")` to event payload

## Frontend: Real-time visual feedback

### 3. Add `refetchInterval` to `usePipelineRunsForIssue`

`hooks.ts:120-126`: no polling. Component stays stale after initial load.

**Changes:**
- Add `refetchInterval: 3000` to `usePipelineRunsForIssue` (always poll when hook is mounted — simple and safe; `usePipelineRun` already polls at 3s)

### 4. Build step stepper in `PipelineProgress`

`pipeline-progress.tsx`: currently shows only colored dot + status text. Has `// TODO` comment.

**Changes:**
- Use `usePipelineRun(latestRun.id)` to fetch full step data (already has `refetchInterval: 3000`)
- Render vertical timeline stepper with step name, role, colored dot + status icon
- Completed steps: green check, line to next step green; running: blue spinner; pending: gray; failed: red X
- Agent name + role label per step, summary on hover for completed steps
- Keep summary card for prior runs

### 5. AgentChat subscribes to step lifecycle events

`agent-chat.tsx:58`: only listens for `agent_message_added`.

**Changes:**
- Subscribe to `agent_step_started`, `agent_step_completed`, `agent_step_failed`
- Render as system-style messages: muted/italic, prefix like "[Pipeline] SpecWriter started", "[Pipeline] SpecWriter completed — summary"
- Use distinct visual style (border-l-gray-400, italic text) to differentiate from agent messages

### 6. Inline pipeline status badge on issue detail header

`issue-detail.tsx`: pipeline status only visible inside Pipeline tab.

**Changes:**
- Add compact status bar above `<Tabs>` when pipeline run is active or last completed
- Text: "Pipeline: Running (Step 2/5 — Architect)" or "Pipeline: Completed"
- Clickable → switches to "pipeline" tab
- Uses `usePipelineRunsForIssue` + `usePipelineRun` (or a lightweight hook)
- Hides when no runs exist

### 7. EventProvider: silent events for pipeline types

`event-context.tsx:170-189`: pipeline events not in silent block → fall through to default → bare toast with raw event type.

**Changes:**
- Add `agent_step_started`, `agent_step_completed`, `agent_step_failed`, `pipeline_completed`, `pipeline_paused` to silent case block
- With `project_id` now in events (backend fix #1), line 299's `if (projectId && issueId)` will auto-invalidate React Query caches