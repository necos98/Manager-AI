# Implementation Plan

## Files
- **Modify:** `backend/app/routers/pipelines.py` — reorder 3 routes to build response before `await db.commit()`

## Task 1: Fix `update_pipeline` route
Move `_response(pipeline)` call before `await db.commit()` at lines 74-76.

**Before:**
```python
pipeline = await svc.update_pipeline(pipeline_id, data.name)
await db.commit()
return _response(pipeline)
```

**After:**
```python
pipeline = await svc.update_pipeline(pipeline_id, data.name)
response = _response(pipeline)
await db.commit()
return response
```

## Task 2: Fix `add_step` route
Move `_step_response(step)` call before `await db.commit()` at lines 102-104.

**Before:**
```python
step = await svc.add_step(...)
await db.commit()
return _step_response(step)
```

**After:**
```python
step = await svc.add_step(...)
response = _step_response(step)
await db.commit()
return response
```

## Task 3: Fix `reorder_steps` route
Build response list before `await db.commit()` at lines 128-130.

**Before:**
```python
steps = await svc.reorder_steps(pipeline_id, data.step_ids)
await db.commit()
return [_step_response(s) for s in steps]
```

**After:**
```python
steps = await svc.reorder_steps(pipeline_id, data.step_ids)
response = [_step_response(s) for s in steps]
await db.commit()
return response
```

## Task 4: Manual verification
- Restart backend: `python start.py`
- Test: `PUT /api/pipelines/{id}` with `{"name": "test rename"}` → expect 200
- Test: `POST /api/pipelines/{id}/steps` → expect 201
- Test: `PUT /api/pipelines/{id}/steps/reorder` → expect 200