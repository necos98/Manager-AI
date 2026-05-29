## Bug

`PUT /api/pipelines/{pipeline_id}` returns 500 Internal Server Error with `MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here`.

## Root Cause

In `backend/app/routers/pipelines.py:68-77`, `update_pipeline` route calls `_response(pipeline)` **before** `await db.commit()`. The `Pipeline` model uses `server_default=func.now()` with `onupdate=func.now()` on `updated_at`. After `update_pipeline()` service method flushes the name change, SQLAlchemy expires `updated_at` because the new value is generated server-side. Accessing the expired attribute triggers a lazy-load refresh, which requires async DB I/O inside a greenlet context — but in the route handler there is none, causing `MissingGreenlet`.

## Fix

Reorder the `update_pipeline` route to match the `create_pipeline` pattern: commit first, re-fetch, then build response.

```python
# BEFORE (broken)
async def update_pipeline(...):
    svc = PipelineService(db)
    pipeline = await svc.update_pipeline(pipeline_id, data.name)
    response = _response(pipeline)       # ← accesses expired updated_at
    await db.commit()
    return response

# AFTER (fixed)
async def update_pipeline(...):
    svc = PipelineService(db)
    await svc.update_pipeline(pipeline_id, data.name)
    await db.commit()                     # ← commit first
    return _response(await svc.get_pipeline(pipeline_id))  # ← re-fetch fresh
```

## Files Changed

- `backend/app/routers/pipelines.py:67-77` — swap commit and response construction

No model changes. No service changes. Single route fix.