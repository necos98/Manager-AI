# Bug: UNIQUE constraint failed when adding pipeline step

## Problem

`POST /api/pipelines/{pipeline_id}/steps` fails with 500 when adding a second step to a pipeline:

```
sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: pipeline_steps.pipeline_id, pipeline_steps.order_index
```

## Root Cause

`PipelineStepCreate.order_index` defaults to `0`. `PipelineService.add_step()` inserts the passed value directly without checking existing steps. When a pipeline already has step at `order_index=0`, the second insert conflicts with the `UNIQUE(pipeline_id, order_index)` constraint.

The frontend (`PipelinesTab.tsx:123-129`) never sends `order_index`, so it always defaults to `0`.

## Fix

In `PipelineService.add_step()`, query the maximum existing `order_index` for the pipeline and assign `max + 1` (or `0` if no steps exist). Ignore the passed `order_index` value — append-only behavior.

### Call sites analysis

Both callers work correctly with auto-increment:

1. **`POST /pipelines/{id}/steps`** — user adding step to existing pipeline. Appends to end. **Fixes the bug.**
2. **`POST /pipelines` (`create_pipeline`)** — creates initial steps in a loop. Each `add_step()` call flushes, incrementing max. Sequential indices (0,1,2,...) preserved.

### Files changed

- `backend/app/services/pipeline_service.py` — `add_step` method only
