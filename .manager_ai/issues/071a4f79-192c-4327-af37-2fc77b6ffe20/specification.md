# Move Pipelines and Agents to Software Level

## Summary

Remove `project_id` from `Agent` and `Pipeline` models. Both become global resources shared across all projects — "software level" entities, not project-scoped. PipelineRun and PipelineStepRun remain project-scoped via their issue relationship.

## Motivation

Currently every project must create its own agents and pipelines, duplicating configuration. Agents and pipelines represent reusable templates (SpecWriter, Architect, Developer, Reviewer, QA) that should be defined once and available to all projects.

## Backend Changes

### Models

**Agent** (`backend/app/models/agent.py`):
- Remove `project_id` column (String(36), FK → projects.id)
- Remove `UniqueConstraint("project_id", "name")`
- Remove `project` relationship
- `pipeline_steps` relationship stays (PipelineStep references agents)

**Pipeline** (`backend/app/models/pipeline.py`):
- Remove `project_id` column (String(36), FK → projects.id)
- Remove `project` relationship
- `steps` and `runs` relationships stay

**Project** (`backend/app/models/project.py`):
- Remove `agents = relationship(...)` 
- Remove `pipelines = relationship(...)`

### Routers

- Move `agents.py` router prefix: `/api/projects/{project_id}/agents` → `/api/agents`
- Move `pipelines.py` router prefix: `/api/projects/{project_id}/pipelines` → `/api/pipelines`
- Register routers at app level in `main.py` (outside project prefix)

### Services

**AgentService**: Remove `project_id` parameter from `list_by_project(project_id)`, `create(project_id, ...)`, `seed_defaults(project_id)`. List returns all agents. Create no longer scopes to project.

**PipelineService**: Remove `project_id` parameter from `list_by_project(project_id)`, `create_pipeline(project_id, ...)`, `seed_defaults(project_id)`.

### Schemas

**AgentCreate**: Remove `project_id` field.
**AgentResponse**: Remove `project_id` field.
**PipelineCreate**: Remove `project_id` field.
**PipelineResponse**: Remove `project_id` field.

### MCP Tools (`backend/app/mcp/server.py`)

- `create_agent`: remove `project_id` parameter
- `list_agents`: remove `project_id` parameter
- `create_pipeline`: remove `project_id` parameter
- `list_pipelines`: remove `project_id` parameter
- `run_pipeline`: keep `project_id` (issue is project-scoped)
- `get_active_agent`, `send_agent_message`, `get_pipeline_messages`: no change needed

### Database Migration

Alembic migration to:
1. Drop `project_id` column from `agents` table
2. Drop `uq_agent_project_name` unique constraint from `agents`
3. Drop `project_id` column from `pipelines` table

## Frontend Changes

### Routes

Move from project-scoped to top-level:
- `routes/projects/$projectId/agents.tsx` → `routes/agents.tsx`
- `routes/projects/$projectId/pipelines.tsx` → `routes/pipelines.tsx`

### API Layer (`frontend/src/api/`)

Update all agent and pipeline API calls:
- `/api/projects/${projectId}/agents` → `/api/agents`
- `/api/projects/${projectId}/pipelines` → `/api/pipelines`

### Navigation

Add "Agents" and "Pipelines" to main navigation (currently they only appear inside a project).

### Agent Selection in Pipeline Steps

When creating/editing pipeline steps, agent dropdown shows all global agents instead of project-scoped list.

## What Stays the Same

- `PipelineRun` and `PipelineStepRun` keep their existing relationships (pipeline_id, issue_id)
- `PipelineMessage` unchanged
- `PipelineStep.agent_id` FK to agents stays
- Pipeline execution flow unchanged
- Issue workflow unchanged

## Test Plan

- Update existing tests to use new API paths
- Verify agents are visible across all projects
- Verify pipelines are visible across all projects
- Verify pipeline execution still works with global pipelines + project-scoped runs
