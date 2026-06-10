Fix 503 "Queue service not initialized" on POST /api/queue/add.

**Root cause:** Two independent bugs combined:

1. **DB schema mismatch** — `metadata.create_all()` stamped DB as Alembic head without running migration chain. `pipeline_runs` missing `rejection_count`, `agents` missing `intent`, `agents` still had `system_prompt`. This caused `OperationalError` in startup cleanup, swallowed by broad except. `IssueQueueService()` never executed → ref stayed None.

2. **Module-level `from X import var`** — Python binds local copy at import time (None). `global ref = self` in __init__ modifies source module only — queue.py's binding stays None forever. Fix: lazy import inside each function body.

**Fixes:**
- queue.py: replaced module-level `from X import issue_queue_service_ref` with function-body lazy imports in all 4 queue endpoints
- New migration `fix_schema_001`: adds rejection_count to pipeline_runs, intent to agents, drops system_prompt from agents
- Verified all 4 queue endpoints return 200 (not 503): POST add, GET position, POST remove, POST auto-process
- 2 new project memories + updated existing singleton memory