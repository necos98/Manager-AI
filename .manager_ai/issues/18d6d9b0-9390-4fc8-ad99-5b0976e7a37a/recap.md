## Fix
Swapped `_response()` and `await db.commit()` in `update_pipeline` route (`backend/app/routers/pipelines.py:67-77`). Now commits first, re-fetches pipeline, then builds response — matching the `create_pipeline` pattern.

## Root Cause
`Pipeline.updated_at` uses `server_default=func.now()` with `onupdate=func.now()`. After `update_pipeline()` flush, SQLAlchemy expires this attribute. Accessing expired attribute triggers lazy-load → `MissingGreenlet` in async context.

## Verification
17/17 pipeline tests pass. No model or service changes.