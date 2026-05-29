# Spec: Fix UNIQUE constraint violation on pipeline step reorder

## Problem

`PUT /api/pipelines/{id}/steps/reorder` throws 500 Internal Server Error due to `UNIQUE constraint failed: pipeline_steps.pipeline_id, pipeline_steps.order_index`.

**Root cause:** `PipelineService.reorder_steps()` at `backend/app/services/pipeline_service.py:109` iterates step_ids, setting `order_index = i` on each step one at a time. SQLAlchemy's autoflush fires during the next `session.execute(select(...))` call inside the loop, and if a step's new `order_index` temporarily conflicts with another step's still-unchanged `order_index`, the UNIQUE constraint on `(pipeline_id, order_index)` is violated.

### Reproduction

Given pipeline steps with order_index [0, 1, 2], reorder them to [2, 0, 1]:
1. Set step[2].order_index = 0 → two rows now have order_index=0
2. `session.execute(select(...step[0]...))` → autoflush → IntegrityError

## Fix

Wrap the reorder loop in `async with self.session.no_autoflush:`. This prevents SQLAlchemy from flushing dirty state mid-loop. All `order_index` values are updated in memory, then a single explicit `await self.session.flush()` at the end writes all changes atomically.

### Code Change

**File:** `backend/app/services/pipeline_service.py`
**Method:** `reorder_steps` (lines 109-126)

Add `async with self.session.no_autoflush:` context manager around the loop body, keeping the explicit `await self.session.flush()` at the end.

## Scope

- Single method change: `reorder_steps` in `pipeline_service.py`
- No model changes needed
- No migration needed
- No frontend changes needed
- No new dependencies

## Testing

- Unit test: reorder 3 steps, verify order_index values are correct after call
- Unit test: reorder that previously caused UNIQUE violation, verify no error
- Verify GET pipeline returns steps in new order