# Fix MissingGreenlet in pipeline routes

## Problem
`PUT /api/pipelines/{id}` (update pipeline name) returns 500 Internal Server Error with `sqlalchemy.exc.MissingGreenlet`. Same pattern exists in `add_step` and `reorder_steps` routes.

## Root Cause
In `backend/app/routers/pipelines.py`, three routes call `await db.commit()` BEFORE building their Pydantic response objects. After commit, SQLAlchemy expires all ORM objects. When `_response()` or `_step_response()` accesses model attributes (e.g., `pipeline.updated_at`), it triggers an async lazy load from a synchronous function — no greenlet context exists → `MissingGreenlet`.

## Routes affected
1. **`update_pipeline`** (line 75-76): commits, then `_response(pipeline)` accesses `updated_at`, `created_at`, `steps`
2. **`add_step`** (line 103-104): commits, then `_step_response(step)` accesses `id`, `pipeline_id`, etc.
3. **`reorder_steps`** (line 129-130): commits, then `[_step_response(s) for s in steps]`

## Routes safe (no change needed)
- `create_pipeline`, `seed_pipeline`: commit, then fresh `get_pipeline()` query
- `list_pipelines`, `get_pipeline`: no commit, read-only
- `delete_pipeline`, `remove_step`: 204 No Content, no response body built

## Fix
Reorder each affected route to build the Pydantic response object **before** `await db.commit()`, while the ORM objects are still active in the session. One-line reorder per route. No model changes, no new abstractions.

## Verification
- `PUT /api/pipelines/{id}` with `{"name": "new name"}` → 200, response includes updated name
- `POST /api/pipelines/{id}/steps` → 201
- `PUT /api/pipelines/{id}/steps/reorder` → 200