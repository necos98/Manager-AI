## Summary

Created `AgentService` and `PipelineService` following the `CredentialService` pattern (DB-backed, `AsyncSession` per instance, SQLAlchemy ORM with `flush()` on mutations, `commit()` in routers).

## Files created

| File | Description |
|------|-------------|
| `backend/app/schemas/agent.py` | AgentCreate, AgentUpdate, AgentResponse |
| `backend/app/schemas/pipeline.py` | PipelineCreate, PipelineUpdate, PipelineResponse, PipelineStepCreate/Response, StepReorderRequest |
| `backend/app/services/agent_service.py` | CRUD + seed_defaults() with 6 default agents |
| `backend/app/services/pipeline_service.py` | CRUD pipeline/step + seed_defaults() with 6-step pipeline |
| `backend/app/routers/agents.py` | REST endpoints for agents CRUD + seed |
| `backend/app/routers/pipelines.py` | REST endpoints for pipeline/step CRUD + seed |

## Files modified

| File | Change |
|------|--------|
| `backend/app/schemas/__init__.py` | Added exports for Agent and Pipeline schemas |
| `backend/app/main.py` | Registered agents/pipelines routers; added seed trigger in lifespan |

## Key decisions

- **DB-backed not file-backed**: Agent/Pipeline are SQLAlchemy ORM models, unlike Issue which is file-backed. Followed CredentialService pattern.
- **terminal_command defaults to ""**: Model field is NOT NULL, so all empty values use empty string, not None.
- **Seed is idempotent**: `seed_defaults()` checks for existing data — no-op if agents/pipelines already exist.
- **Seed in lifespan**: Runs automatically on startup after DB init and project load. Wrapped in try/except, rollback on failure — non-fatal.
- **Seed order matters**: `PipelineService.seed_defaults()` depends on `AgentService.seed_defaults()` having already created agents. In lifespan, agents always seed before pipelines.

## 6 default agents

CodebaseExplorer, BrainstormingAgent, SpecWriter, PlanWriter, Developer, Reviewer — all with basic role descriptions, model=None, allowed_tools=None.

## Default pipeline

"Default Pipeline" with all 6 agents mapped in order, terminal_command="" for each step.
