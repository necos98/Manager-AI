## Recap

Created 6 SQLAlchemy models for the pipeline orchestration system:

**New files:**
- `backend/app/models/agent.py` — Agent model (reusable agent definition, unique name per project)
- `backend/app/models/pipeline.py` — Pipeline + PipelineStep models (ordered step sequence)
- `backend/app/models/pipeline_run.py` — PipelineRun, PipelineStepRun, PipelineMessage models + PipelineRunStatus/PipelineStepRunStatus enums

**Modified files:**
- `backend/app/models/__init__.py` — registered all 6 models and enums
- `backend/app/models/project.py` — added `agents` and `pipelines` relationships with cascade delete
- `backend/tests/conftest.py` — imported new models for test metadata registration

**Migration:** `04d6489a8fd4_add_agent_pipeline_tables.py` — creates all 6 tables with indexes, unique constraints, FKs, and enum types.

**Tests:** `backend/tests/test_models_pipeline.py` — 10 tests passing:
- Table creation verification (sqlite_master query)
- Agent unique constraint (same project + cross-project)
- Full chain insert (Agent → Pipeline → PipelineStep → PipelineRun → PipelineStepRun → PipelineMessage)
- Cascade deletes (pipeline → steps, pipeline_run → step_runs + messages, project → agents)
- Pipeline step unique order constraint
- Enum value verification

**Note:** Project has two directories on disk — `manager-ai/Manager-AI` (Python venv target) and `manager-ai/manager-ai-mod/Manager-AI` (working directory). Changes were applied to both.