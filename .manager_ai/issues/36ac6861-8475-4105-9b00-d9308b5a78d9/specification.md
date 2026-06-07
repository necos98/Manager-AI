## Scope

Refactor `PipelineRunService._execute()` (lines 245-454, ~210 lines) in `backend/app/services/pipeline_run_service.py`. Extract distinct phases into separate private methods. The function orchestrates the entire pipeline run lifecycle — too long, too many responsibilities, hard to test and reason about.

## Extracted Methods

1. **`_wait_for_run(run_id, session)`** — Retry loop fetching the PipelineRun. Waits up to 5s (50 × 100ms) for the run to appear after commit. Returns `(run, pipeline, steps)` or aborts if not found.

2. **`_setup_step_environment(step, run, session, project_id, project_path)`** — Fetches latest step_run via `ORDER BY started_at DESC NULLS LAST` + `scalars().first()`, marks it RUNNING, creates a terminal, handles WSL `cd` if needed, emits `agent_step_started` and `terminal_created` events. Returns `(term_id, agent_name, step_run)`.

3. **`_handle_step_completion(run, step_run, session, success, agent_name, project_id, issue_id)`** — Routes step outcome: REJECTED → continue loop, success → increment `current_step_index` and emit `agent_step_completed`, failure → mark FAILED and break. Updates `step_run.finished_at`.

4. **`_cleanup_step(term_id)`** — Saves buffered output via `_save_recording()`, stops reader via `_stop_reader()`, pops session, kills terminal via `terminal_service.kill()`. Called in `finally` block.

5. **`_finalize_run(run, session, project_id, issue_id, run_id)`** — Sets run to COMPLETED (or leaves FAILED), sets `finished_at`, commits, emits `pipeline_completed` event. Also handles the outer `except` fallback that sets FAILED and emits on unexpected errors.

## Constraints

- Step_run query for rejection support **must** use `scalars().first()` with `ORDER BY started_at DESC NULLS LAST` — NOT `scalar_one_or_none()` — because `reject_step()` creates duplicate rows for the same `pipeline_step_id`
- Session factory pattern: prod uses own session via `self.session_factory()`, tests inject shared session. Extracted methods must accept session as parameter to preserve this.
- WSL `cd` must happen after terminal creation but before `_run_step()` — order is sensitive
- Cleanup sequence is critical: `_save_recording()` → `_stop_reader()` → `_sessions.pop()` → `terminal_service.kill()`. Historical fix — don't reorder.
- Outer exception handler (lines 433-449) catches unexpected errors during the entire `_execute()` — must still set FAILED + emit `pipeline_completed`
- asyncio.CancelledError must propagate, not be caught

## Acceptance Criteria

1. All 5 extracted methods exist as `async def` private methods on `PipelineRunService`
2. `_execute()` calls them in sequence: `_wait_for_run` → per-step loop with `_setup_step_environment` → `_run_step` → `_handle_step_completion` → `_cleanup_step` → after loop `_finalize_run`
3. Outer try/except still catches unexpected errors and sets FAILED
4. All existing functionality preserved — no behavior changes
5. Cleanup always runs in `finally` block per step
6. Session factory pattern preserved
7. Pipeline with rejection still works (step_run ordering, continue on REJECTED)
8. Pipeline with failure still marks run FAILED and stops
9. CancelledError propagates correctly
10. Tests pass (existing test suite)

## Non-goals

- NO changes to `reject_step()`, `_run_step()`, `_get_run_with_session()`, `_safe_flush_session()`, `_safe_commit_session()`, or any other method
- NO changes to models, schemas, or database
- NO changes to the frontend
- NO new features or behavior changes — pure refactoring
- NO extraction of helper utilities into separate modules — keep methods on PipelineRunService
- NO changes to error handling semantics, only reorganization

## Out of Scope

- Any changes outside `pipeline_run_service.py`
- Renaming or restructuring public API methods
- Adding type hints beyond what already exists
- Adding tests (existing tests must still pass, but no new test files required)
