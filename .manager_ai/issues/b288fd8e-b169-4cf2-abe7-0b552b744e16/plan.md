## Implementation Plan: Pipeline Step Rejection with Feedback Loop

### Overview

Transform linear pipeline execution to support rejection/regression. Review agents (CodeReviewer, QualityReviewer, SpecReviewer, PlanReviewer) can reject a pipeline step. Pipeline loops back to target step for fixes instead of advancing. Max 3 rejections per run, then FAILED.

### Architecture

Core mechanism: extend `finished_pipeline_step` MCP tool with rejection params. `reject_step()` service method handles DB changes. `_execute()` refactored from `for` to `while` loop for regression support.

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/models/pipeline_run.py` | Add REJECTED to PipelineStepRunStatus; add rejection_count to PipelineRun |
| `backend/app/services/pipeline_run_service.py` | Add reject_step(); refactor _execute() to while-loop; 3-rejection guard |
| `backend/app/mcp/server.py` | Extend finished_pipeline_step with rejection params |
| `backend/alembic/versions/` | New migration for rejection_count + Enum change |

### New Files

| File | Purpose |
|------|---------|
| `backend/tests/test_pipeline_rejection.py` | Tests for rejection flow |

### Step 1: Model changes (`pipeline_run.py`)

**PipelineStepRunStatus** — add `REJECTED = "REJECTED"`:
```python
class PipelineStepRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
```

**PipelineRun** — add `rejection_count`:
```python
rejection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

### Step 2: Alembic migration

- Add `rejection_count` column to `pipeline_runs` (Integer, default 0, nullable=False)
- SQLite Enum is stored as VARCHAR, no schema change needed for the Enum addition (SQLite doesn't enforce CHECK constraints by default on Enum columns, but if it has a CHECK, we need to recreate)

### Step 3: PipelineRunService.reject_step() method

Signature: `async def reject_step(self, run_id: str, reason: str, target_step_index: int, project_id: str) -> dict`

Logic:
1. Fetch run + step_runs (using session — same pattern as _execute for background access)
2. Validate: target_step_index < current_step_index (rejection must go backward)
3. Validate: target_step_index >= 0
4. Find current step_run (RUNNING status for current step) — set it to REJECTED, finished_at = now
5. Find pipeline step at target_step_index — create new PipelineStepRun with RUNNING status
6. Update run.current_step_index = target_step_index
7. Increment run.rejection_count += 1
8. If rejection_count >= 3: set run.status = FAILED
9. Save rejection reason as pipeline message
10. Emit `pipeline_step_rejected` event
11. Signal step completion via `set_step_completed()` so _execute() wakes up
12. Commit

Returns: {success: bool, rejection_count: int, max_reached: bool}

### Step 4: Refactor _execute() to while-loop

Current: `for i, step in enumerate(steps):`
New: `while run.current_step_index < len(steps) and run.status != FAILED:`

Inside loop:
1. `i = run.current_step_index; step = steps[i]`
2. Fetch the latest step_run for `(run_id, step.id)` ordered by created_at DESC (handles case where reject_step created new step_run in another session)
3. If no step_run exists: create one with PENDING
4. Set step_run.status = RUNNING, step_run.started_at = now
5. run.current_step_index = i
6. Create terminal, emit events, call _run_step() (unchanged)
7. After _run_step returns:
   - `await session.refresh(run)` to pick up rejection index changes
   - Refresh step_run to see if MCP tool set it to REJECTED
   - If step_run.status == REJECTED: don't overwrite, loop naturally advances (or stuck if target is same — handled by FAILED guard)
   - Else: set step_run.status = COMPLETED
8. Terminal cleanup in finally (unchanged)
9. Break conditions: step_run FAILED, run.status FAILED, step_run REJECTED and run.rejection_count >= 3

Edge cases:
- **Self-rejection loop**: if target_step_index == current_step_index, the loop would reject repeatedly. Guard: reject_step validates target < current.
- **Double rejection**: reject_step validates no other step_run is currently RUNNING for the target step.
- **DB session sync**: reject_step runs in MCP session (committed). _execute refreshes run after each step completion to pick up changes.

### Step 5: Extend finished_pipeline_step MCP tool

New params to existing MCP tool (backward compatible):

```python
async def finished_pipeline_step(
    issue_id: str, 
    summary: str,
    rejected: bool = False,
    rejection_reason: str | None = None,
    target_step_index: int | None = None,
) -> dict:
```

Logic:
1. Find active run for issue (existing logic)
2. When rejected=True:
   - Validate rejection_reason is non-empty, target_step_index is not None
   - Call `svc.reject_step(run_id, rejection_reason, target_step_index, project_id)`
3. Add summary as pipeline message (existing logic)
4. Call `set_step_completed()` (existing logic — wakes up _execute)
5. When rejected=False: existing behavior (unchanged)

### Step 6: WebSocket event

Emit in `reject_step()`:
```python
await event_service.emit({
    "type": "pipeline_step_rejected",
    "project_id": project_id,
    "issue_id": run.issue_id,
    "run_id": run_id,
    "step_run_id": current_step_run.id,
    "agent_name": agent_name,
    "reason": reason,
    "target_step_index": target_step_index,
    "rejection_count": run.rejection_count,
})
```

### Step 7: Tests

File: `backend/tests/test_pipeline_rejection.py`

Tests:
1. `test_reject_step_goes_backward` — reject from step 4 to step 1, verify step_run statuses and current_step_index
2. `test_reject_step_validates_target_not_forward` — reject with target > current step raises ValidationError
3. `test_max_rejections_fails_pipeline` — 3 rejections → pipeline FAILED
4. `test_finished_pipeline_step_with_rejection` — MCP tool integration test
5. `test_finished_pipeline_step_backward_compatible` — without rejection params, works as before
6. `test_rejection_creates_new_step_run` — verify new step_run created for target, old one stays REJECTED

### Dependency Order

1. Model changes (pipeline_run.py)
2. Alembic migration
3. PipelineRunService.reject_step() + WebSocket event
4. _execute() while-loop refactor
5. finished_pipeline_step MCP tool extension
6. Tests

### Non-obvious Architectural Decisions to Record in Memory

1. reject_step() creates new step_runs (never reuses old ones) — preserves rejection audit trail
2. Session factory pattern: reject_step uses injected session (called from both MCP and service contexts)
3. The while-loop is driven by `current_step_index` on PipelineRun — reject_step updates it concurrently, _execute session refreshes to pick up changes
4. asyncio.Event signaling mechanism reused for rejection wake-up — set_step_completed fires same event