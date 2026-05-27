# Implementation Plan

**Goal:** Fix pipeline run so terminal appears immediately and Claude Code launches correctly.

**Architecture:** Align `_run_step()` with proven `enrich_context.py` pattern (create_subprocess_exec + arg list). Emit WebSocket events from `_execute()` so frontend reacts in real-time (events already handled by frontend EventProvider). Add meaningful default terminal_command per agent.

**Tech Stack:** Python FastAPI, asyncio subprocess, WebSocket events

---

## Task 1: Fix `_run_step()` — replace `create_subprocess_shell` with `create_subprocess_exec`

**File:** `backend/app/services/pipeline_run_service.py:220-280`

Replace shell string interpolation with proper arg list. Match pattern from `enrich_context.py`.

- Remove `full_cmd` string construction
- Build prompt as Python string with actual newlines
- Use `["claude", "-p", prompt]` as arg list
- Use `create_subprocess_exec` instead of `create_subprocess_shell`
- Split stdout/stderr (not merged) — stream stdout, log stderr
- Keep `push_output()` streaming via `stream_output()` task
- Keep CancelledError/TimeoutError handling

## Task 2: Emit WebSocket events during step execution

**File:** `backend/app/services/pipeline_run_service.py:104-211`

Add event emission in `_execute()`:

- Import `event_service` from `app.services.event_service`
- After terminal creation and step RUNNING: emit `agent_step_started` with `{project_id, issue_id, agent_name, step_run_id, terminal_id}`
- On step success: emit `agent_step_completed`
- On step failure: emit `agent_step_failed` with error info
- After all steps complete: emit `pipeline_completed`
- Frontend EventProvider already handles these event types and invalidates queries

## Task 3: Add default `terminal_command` per agent

**File:** `backend/app/services/agent_service.py:7-50`

Add `terminal_command` to each DEFAULT_AGENTS entry:

- CodebaseExplorer: "Explore the codebase to understand the context of issue $issue_id in project $project_id"
- BrainstormingAgent: "Brainstorm and refine requirements for issue $issue_id"
- SpecWriter: "Write a detailed specification for issue $issue_id"
- PlanWriter: "Create an implementation plan for issue $issue_id"
- Developer: "Implement the code changes described in the plan for issue $issue_id"
- Reviewer: "Review the code changes made for issue $issue_id"

Also update `seed_defaults()` to pass `terminal_command` to each step.

## Task 4: Frontend — ensure PipelineProgress connects to terminal on events

**File:** `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx`

The EventProvider already invalidates pipeline-runs queries on agent events. But add explicit subscription to auto-select running step when event arrives:

- Import `useEvents` from event-context
- Subscribe to `agent_step_started` events
- When event fires for current issue, set selectedStepId to the running step
- This provides immediate terminal connection without waiting for polling refetch

## Execution Order

Task 1 → Task 2 → Task 3 → Task 4

Each task is independent enough to be committed separately. Task 1 is critical — without it Claude never launches. Task 2 makes the UX real-time. Tasks 3-4 are quality improvements.
