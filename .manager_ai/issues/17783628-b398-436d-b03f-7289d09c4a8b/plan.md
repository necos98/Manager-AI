## Implementation Plan

### Problem
3 endpoints in `backend/app/routers/agents.py` call `await db.commit()` then access ORM attributes synchronously in `_response()`. After commit, SQLAlchemy async session expires all attributes, so sync access triggers lazy-load which fails with `MissingGreenlet`.

### Files to modify
- `backend/app/routers/agents.py` — fix 3 endpoints

### Changes
1. **`create_agent` (line 38-40)**: Build response BEFORE commit
2. **`update_agent` (line 66-68)**: Build response BEFORE commit
3. **`seed_agents` (line 81-83)**: Build response list BEFORE commit

Each fix follows same pattern: capture `_response()` result into variable, then `await db.commit()`, then return the captured result.
