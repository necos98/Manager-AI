## Fix: UNIQUE constraint violation on pipeline step reorder

### Root cause
`PipelineService.reorder_steps()` in `backend/app/services/pipeline_service.py:109` iterated step_ids and set `order_index = i` one at a time. SQLAlchemy autoflush fired on the next `session.execute(select(...))`, creating a temporary duplicate `(pipeline_id, order_index)` that violated the UNIQUE constraint.

### Fix
Two-pass approach wrapped in `self.session.sync_session.no_autoflush`:
1. First pass: assign temporary indices (`offset + i`) to avoid conflicts
2. Flush
3. Second pass: assign final indices (`0, 1, 2, ...`)
4. Flush

The `no_autoflush` on the sync session prevents autoflush during the select queries inside the loop.

### Files changed
- `backend/app/services/pipeline_service.py` — `reorder_steps` method
- `backend/tests/test_models_pipeline.py` — added `test_reorder_steps_no_constraint_violation`

### Test results
- Pipeline tests: 8/8 pass (including new reorder test)
- No regressions in existing tests