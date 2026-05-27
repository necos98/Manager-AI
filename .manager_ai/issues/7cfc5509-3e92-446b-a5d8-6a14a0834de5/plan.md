# Pipeline DB Schema & Models — Implementation Plan

## Approach

Create 6 SQLAlchemy 2.0 models across 3 new files, following existing codebase patterns (UUID PKs, `Mapped[]` + `mapped_column()`, `server_default=func.now()`, enum-as-String). Generate Alembic migration via autogenerate. Unit tests use async in-memory SQLite with schema inspection + integrity checks.

## File grouping

- `agent.py` — Agent model (standalone, reusable across pipelines)
- `pipeline.py` — Pipeline + PipelineStep (pipeline definition)
- `pipeline_run.py` — PipelineRun + PipelineStepRun + PipelineMessage (execution records) + PipelineRunStatus/PipelineStepRunStatus enums

## Dependencies

1. Agent — no dependencies on other new models
2. Pipeline — no dependencies on other new models
3. PipelineStep — depends on Agent + Pipeline
4. PipelineRun — depends on Pipeline
5. PipelineStepRun — depends on PipelineRun + PipelineStep + TerminalCommand
6. PipelineMessage — depends on PipelineRun

All models depend on Project (existing FK).

## Migration

Single `alembic revision --autogenerate` captures all 6 tables, indexes, unique constraints, and FKs. SQLite stores enums as VARCHAR.

## Testing

Async in-memory SQLite test:
- Verify all 6 tables exist via SQLAlchemy inspector
- Insert full chain: Agent → Pipeline → PipelineStep → PipelineRun → PipelineStepRun → PipelineMessage
- Verify cascade: delete pipeline → steps deleted; delete pipeline_run → step_runs + messages deleted
- Verify unique constraint: duplicate agent name per project raises IntegrityError