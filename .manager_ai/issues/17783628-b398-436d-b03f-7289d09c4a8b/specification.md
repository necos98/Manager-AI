## Bug Analysis

### Symptom
`PUT /api/agents/{id}` returns HTTP 500 with `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`. Crashes when saving any agent update.

### Root Cause

**File:** `backend/app/routers/agents.py` lines 67-68

```python
await db.commit()
return _response(agent)
```

After `db.commit()`, SQLAlchemy's async session **expires all attributes** on managed ORM objects. When `_response(agent)` then accesses `agent.updated_at` (line 19), SQLAlchemy tries to lazy-load the expired attribute from the database. Lazy-loading requires an async greenlet context, but `_response()` is a synchronous function — hence `MissingGreenlet`.

**Same bug exists in 2 more endpoints in the same file:**
- `create_agent` (lines 39-40): `await db.commit(); return _response(agent)`
- `seed_agents` (lines 82-83): `await db.commit(); return [_response(a) for a in agents]`

### Fix

Move `_response()` BEFORE `db.commit()` so all ORM attributes are accessed while still loaded. Store the result, commit, then return.

For `update_agent` (line 66-68):
```python
agent = await svc.update(agent_id, **kwargs)
resp = _response(agent)
await db.commit()
return resp
```

For `create_agent` (line 38-40):
```python
agent = await svc.create(...)
resp = _response(agent)
await db.commit()
return resp
```

For `seed_agents` (line 81-83):
```python
agents = await svc.seed_defaults()
resp = [_response(a) for a in agents]
await db.commit()
return resp
```

### Impact
- Blocks ALL agent CRUD operations (create, update) — users cannot create or edit agents
- Regression — likely introduced when the agents router was first built
- Only affects endpoints that `commit()` then access ORM attributes synchronously
- `get_agent` and `list_agents` are NOT affected (no commit, or attributes loaded in async context)

### Verification
- Create an agent via POST /api/agents
- Update an agent via PUT /api/agents/{id}
- Verify both return 200 with valid JSON (not 500)
