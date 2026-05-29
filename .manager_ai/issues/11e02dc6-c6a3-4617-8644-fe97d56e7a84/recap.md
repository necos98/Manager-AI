## Fix

Changed `PipelineService.add_step()` in `backend/app/services/pipeline_service.py` to auto-compute the next available `order_index` by querying `MAX(order_index)` for the pipeline and using `max + 1` (or `0` if no steps exist), instead of using the passed value directly.

## Root Cause

`PipelineStepCreate.order_index` defaults to `0`. The frontend never sends `order_index`. When adding a second step to a pipeline, the default `0` collides with the existing step at position 0, violating the `UNIQUE(pipeline_id, order_index)` constraint.

## Files Changed

- `backend/app/services/pipeline_service.py:1` — added `func` to sqlalchemy imports
- `backend/app/services/pipeline_service.py:81-105` — `add_step` now queries max index, auto-assigns next
- `backend/tests/test_models_pipeline.py:148-168` — new test `test_add_step_auto_assigns_next_order_index`
- `backend/tests/test_models_pipeline.py:180` — fixed unrelated merge conflict markers
- `venv/Lib/site-packages/_manager_ai_proactor.pth` — updated path to new project location

## Verification

All 9 pipeline model tests pass, including the new test that reproduces the original bug.