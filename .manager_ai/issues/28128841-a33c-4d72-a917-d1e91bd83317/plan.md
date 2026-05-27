## Implementation Plan

### Architecture
Standard FastAPI pattern: Pydantic schemas in `schemas/`, async REST routers in `routers/`, business logic in `services/`. Routers use `Depends(get_db)` for session injection, commit after mutations, `HTTPException` for error translation. All endpoints under `/api/projects/{project_id}/...`.

### File Structure
- Create: `backend/app/schemas/agent.py`, `pipeline.py`, `pipeline_run.py`
- Modify: `backend/app/schemas/__init__.py` (add exports)
- Create: `backend/app/routers/agents.py`, `pipelines.py`, `pipeline_runs.py`
- Modify: `backend/app/main.py` (register 3 routers)

### Tasks

1. Write Pydantic schemas (agent.py, pipeline.py, pipeline_run.py)
2. Update schemas/__init__.py exports
3. Write agents router (CRUD + seed)
4. Write pipelines router (CRUD pipeline + steps + reorder + seed)
5. Write pipeline_runs router (start, status, cancel, messages)
6. Register routers in main.py
7. Run tests and verify