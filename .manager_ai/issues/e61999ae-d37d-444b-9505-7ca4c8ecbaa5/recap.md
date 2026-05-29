## Fix
3 routes in `backend/app/routers/pipelines.py` had `await db.commit()` before building Pydantic response objects. After commit, SQLAlchemy expires ORM objects → accessing attributes triggers async lazy load from sync helper → MissingGreenlet.

**Fix:** Build response before commit in all 3 routes:
1. `update_pipeline`: `response = _response(pipeline)` before `await db.commit()` (line 75-77)
2. `add_step`: `response = _step_response(step)` before `await db.commit()` (line 104-106)
3. `reorder_steps`: `response = [_step_response(s) for s in steps]` before `await db.commit()` (line 131-133)

## Verification
All 17 existing pipeline tests pass. `create_pipeline` and `seed_pipeline` were already safe (fresh `get_pipeline()` query after commit).