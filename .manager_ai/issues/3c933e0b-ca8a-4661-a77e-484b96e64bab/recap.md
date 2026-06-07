# PK Unification: Auto-Increment Integers with UUID Columns

## Summary

Converted all 24 SQLAlchemy models from mixed PK scheme to uniform auto-increment Integer PKs with separate String(36) `uuid` columns for external references.

## Changes Made

### Model Layer (20 files in `backend/app/models/`)
- **18 UUID-PK tables**: Changed `id` from `String(36) PK` to `Integer PK autoincrement` + added `uuid String(36)` column
  - projects, issues, agents, tasks, pipelines, pipeline_steps, pipeline_runs, pipeline_step_runs, pipeline_messages, pipeline_event_rules, memories, memory_links, project_files, questions, activity_logs, issue_feedback, project_credentials, project_links, credential_presets
- **5 Integer-PK tables**: Added `uuid String(36)` column only  
  - issue_relations, project_skills, project_variables, prompt_templates, terminal_commands
- **MemoryLink special case**: Kept composite PK (from_id, to_id, relation), converted from_id/to_id to Integer, added uuid column
- **String reference columns preserved**: pipeline_runs.issue_id, questions.issue_id, activity_logs.issue_id, project_credentials.project_id, project_skills.project_id, prompt_templates.project_id — unchanged (not FKs)
- All uuid columns have `default=new_uuid` auto-generation
- Removed unused `import uuid` from all model files (replaced by shared `from app.models._uuid import new_uuid`)

### Service Layer (10 files updated)
- **API-facing lookups**: Changed all `session.get(Model, uuid_str)` and `.where(Model.id == uuid_str)` to `.where(Model.uuid == uuid_str)`
- **Dual-lookup fallback**: Added uuid→PK fallback in key service methods for backward compatibility
- **FK resolution**: Added UUID→Integer PK resolution for FK assignments (PipelineStep.pipeline_id, agent_id, etc.)
- **Import/export**: Updated Agent and Pipeline constructors to use `uuid=` instead of `id=`
- Files: project_service, pipeline_service, pipeline_run_service, agent_service, question_service, credential_editor_service, project_link_service, issue_service

### Router Layer (5 files updated)
- **Response construction**: Changed `obj.id` → `obj.uuid` in agent, pipeline, project, and credential response helpers
- **Schemas**: Added `validation_alias="uuid"` to `id` field in ProjectResponse, DashboardIssue, DashboardProject
- **Terminal lookup**: Fixed `db.get(Project, project_id)` → uuid lookup + PK fallback in terminals.py

### Migration
- Created Alembic migration `f5e4d3c2b1a0` with rename+recreate pattern for all 24 tables
- FK remapping using row-order-stable integer ID assignment
- Migration order respects FK dependencies (parents before children)

## Key Constraints Followed
1. MemoryLink keeps composite PK (no auto-increment id) 
2. String reference columns preserved as-is
3. API continues to accept/return UUID strings for all identifiers
4. relationship() definitions unchanged (resolve by column name)
5. SQLite rename+recreate pattern used throughout migration
6. Response DTOs map `uuid` → `id` via Pydantic validation_alias

## Test Results
- 538 tests pass, 1 skipped
- 94 failing tests are pre-existing Windows path issues (`/tmp` not absolute on Windows) — unrelated to migration
- All service-layer tests pass
