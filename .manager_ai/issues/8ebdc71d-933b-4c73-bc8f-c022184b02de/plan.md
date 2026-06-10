## Implementation Plan

### Task 1: Fix queue.py — lazy imports for issue_queue_service_ref
Replace the module-level `from app.services.issue_queue_service import issue_queue_service_ref` with lazy imports inside each endpoint function. Affected lines: 21 (remove), and update functions at lines 248, 277, 305, 334.

### Task 2: Fix DB schema — create Alembic migration
Create a new Alembic migration that:
- Adds `rejection_count` column to `pipeline_runs`
- Adds `intent` column to `agents`
- Drops `system_prompt` column from `agents`

### Task 3: Verify
- Kill current backend
- Apply migration
- Restart backend
- Test POST /api/queue/add
- Verify all queue operations work

### Task 4: Write project memory
Save facts about:
- The module-level import gotcha (from X import var creates local copy)
- The DB schema mismatch fix
- The pattern for lazy imports in routers

### Task 5: Complete issue with recap
