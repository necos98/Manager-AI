## Recap

Created Pydantic schemas and REST routers for Agent Pipeline backend:

**Schemas (3 files):**
- `agent.py` — AgentCreate, AgentUpdate, AgentResponse
- `pipeline.py` — PipelineCreate/Update/Response, PipelineStepCreate/Response, StepReorderRequest
- `pipeline_run.py` — PipelineRunStart/Response, PipelineStepRunResponse, PipelineMessageCreate/Response

**Routers (3 files):**
- `agents.py` — CRUD + seed endpoint (6 predefiniti)
- `pipelines.py` — CRUD pipeline + step add/remove/reorder + seed
- `pipeline_runs.py` — start run, list, get status, cancel, get/send messages

**Wiring:**
- `schemas/__init__.py` — exports all new schemas
- `main.py` — registers agents, pipelines, pipeline_runs routers

**Tests:** 8/8 pipeline run service tests pass. All 181 existing tests pass (1 pre-existing failure in test_db_backup.py unrelated).