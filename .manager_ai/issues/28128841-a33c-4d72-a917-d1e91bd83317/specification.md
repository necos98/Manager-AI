## Specification: Pipeline Backend - Pydantic Schemas + REST Routers

### Overview
Create Pydantic schemas and FastAPI REST routers for the Agent Pipeline system: Agents, Pipelines, and Pipeline Runs. These follow existing project patterns for prefix, dependency injection, and async session management.

### Schemas

**agent.py**
- `AgentCreate`: name (required, 1-255), system_prompt (required, min 1), model (optional), allowed_tools (optional list[str])
- `AgentUpdate`: all fields optional
- `AgentResponse`: id, project_id, name, system_prompt, model, allowed_tools, created_at, updated_at

**pipeline.py**
- `PipelineStepCreate`: agent_id (required), order_index (int, default 0), terminal_command (str, default "")
- `PipelineStepResponse`: id, pipeline_id, agent_id, order_index, terminal_command
- `PipelineCreate`: name (required, 1-255), steps (list[PipelineStepCreate], default [])
- `PipelineUpdate`: name (required, 1-255)
- `PipelineResponse`: id, project_id, name, steps (list[PipelineStepResponse]), created_at, updated_at
- `StepReorderRequest`: step_ids (list[str], min 1)

**pipeline_run.py**
- `PipelineRunStart`: pipeline_id (required), issue_id (required)
- `PipelineStepRunResponse`: id, pipeline_run_id, pipeline_step_id, agent_name, status, started_at, finished_at
- `PipelineRunResponse`: id, pipeline_id, issue_id, status, current_step_index, steps (list[PipelineStepRunResponse]), started_at, finished_at, created_at
- `PipelineMessageCreate`: sender_agent_name (required), content (required)
- `PipelineMessageResponse`: id, pipeline_run_id, sender_agent_name, content, created_at

### Routers

All routers follow pattern: `prefix="/api/projects/{project_id}/..."`, `Depends(get_db)` for async session, commit after mutations, HTTPException for error translation.

**agents.py** — `/agents`
- GET / — list agents for project
- POST / — create agent (201)
- GET /{agent_id} — get agent detail
- PUT /{agent_id} — update agent
- DELETE /{agent_id} — delete agent (204)
- POST /seed — seed 6 default agents (201)

**pipelines.py** — `/pipelines`
- GET / — list pipelines with steps
- POST / — create pipeline with steps (201)
- GET /{pipeline_id} — get pipeline detail
- PUT /{pipeline_id} — update pipeline name
- DELETE /{pipeline_id} — delete pipeline (204)
- POST /{pipeline_id}/steps — add step (201)
- DELETE /{pipeline_id}/steps/{step_id} — remove step (204)
- PUT /{pipeline_id}/steps/reorder — reorder steps
- POST /seed — seed default 6-step pipeline (201)

**pipeline_runs.py** — `/pipeline-runs`
- POST / — start pipeline run (201)
- GET /?issue_id=X — list runs for issue
- GET /{run_id} — get run status + step runs
- DELETE /{run_id} — cancel run (204)
- GET /{run_id}/messages — get chat messages
- POST /{run_id}/messages — send message (201)

### Wiring
- `schemas/__init__.py` exports all new schemas
- `main.py` registers agents.router, pipelines.router, pipeline_runs.router
- Services already referenced: AgentService, PipelineService, PipelineRunService