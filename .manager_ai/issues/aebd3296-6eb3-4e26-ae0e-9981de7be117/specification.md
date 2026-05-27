# AgentService + PipelineService

## Overview

Create two DB-backed services: `AgentService` (CRUD + seed 6 default agents) and `PipelineService` (CRUD pipeline/step + seed default 6-step pipeline). Both follow the `CredentialService` pattern: `AsyncSession` per instance, SQLAlchemy ORM queries, flush on mutate, commit in router.

## Why DB-backed (not file-backed like IssueService)

IssueService is file-backed via `app.storage.issue_store`. Agent and Pipeline models are SQLAlchemy ORM models already wired into the `Project` model. They use SQLite — no file-backed storage exists for them. CredentialService is the correct pattern to replicate.

## Files to create

| File | Purpose |
|------|---------|
| `app/schemas/agent.py` | Pydantic request/response for Agent CRUD |
| `app/schemas/pipeline.py` | Pydantic request/response for Pipeline + Steps CRUD |
| `app/services/agent_service.py` | AgentService: CRUD + `seed_defaults()` |
| `app/services/pipeline_service.py` | PipelineService: CRUD pipeline/step + `seed_defaults()` |
| `app/routers/agents.py` | REST endpoints for agents |
| `app/routers/pipelines.py` | REST endpoints for pipelines |

## Files to update

| File | Change |
|------|--------|
| `app/schemas/__init__.py` | Export new schemas |
| `app/main.py` | Register new routers |

## AgentService

```python
class AgentService:
    def __init__(self, session: AsyncSession): ...
    
    # Seed
    async def seed_defaults(self, project_id: str) -> list[Agent]:
        """Idempotent. Creates 6 default agents only if project has 0 agents."""
    
    # CRUD
    async def create(self, project_id: str, name: str, system_prompt: str,
                     model: str | None = None, allowed_tools: list[str] | None = None) -> Agent: ...
    async def get_by_id(self, agent_id: str) -> Agent: ...
    async def get_by_name(self, project_id: str, name: str) -> Agent | None: ...
    async def list_by_project(self, project_id: str) -> list[Agent]: ...
    async def update(self, agent_id: str, **kwargs) -> Agent: ...
    async def delete(self, agent_id: str) -> bool: ...
```

### Default agents (seed)

Six agents with `model=None` and `allowed_tools=None`:

1. **CodebaseExplorer** — "Explore and analyze codebase structure, find patterns and conventions, trace execution paths, and document dependencies."
2. **BrainstormingAgent** — "Brainstorm ideas and refine requirements through natural collaborative dialogue. Turn ideas into fully formed designs and specs."
3. **SpecWriter** — "Write detailed specifications from requirements. Produce clear, structured specs covering architecture, components, data flow, error handling, and testing."
4. **PlanWriter** — "Create implementation plans from specifications. Break down designs into atomic, ordered tasks with specific files to create or modify."
5. **Developer** — "Implement code following plans and specifications. Write production-quality code that follows existing patterns and conventions."
6. **Reviewer** — "Review code for bugs, logic errors, security vulnerabilities, code quality issues, and adherence to project conventions."

## PipelineService

```python
class PipelineService:
    def __init__(self, session: AsyncSession): ...
    
    # Seed
    async def seed_defaults(self, project_id: str) -> Pipeline:
        """Idempotent. Creates 6-step pipeline only if project has 0 pipelines."""
    
    # Pipeline CRUD
    async def create_pipeline(self, project_id: str, name: str) -> Pipeline: ...
    async def get_pipeline(self, pipeline_id: str) -> Pipeline: ...
    async def list_by_project(self, project_id: str) -> list[Pipeline]: ...
    async def update_pipeline(self, pipeline_id: str, name: str) -> Pipeline: ...
    async def delete_pipeline(self, pipeline_id: str) -> bool: ...
    
    # Step CRUD
    async def add_step(self, pipeline_id: str, agent_id: str, order_index: int,
                       terminal_command: str | None = None) -> PipelineStep: ...
    async def remove_step(self, step_id: str) -> bool: ...
    async def reorder_steps(self, pipeline_id: str, step_ids: list[str]) -> list[PipelineStep]:
        """Reassign order_index based on list position."""
```

### Default pipeline (seed)

Name: "Default Pipeline". Six steps, one per default agent in order:

1. CodebaseExplorer
2. BrainstormingAgent  
3. SpecWriter
4. PlanWriter
5. Developer
6. Reviewer

Each step has `terminal_command=None`.

## Schemas

### agent.py
```python
class AgentCreate(BaseModel):
    name: str
    system_prompt: str
    model: str | None = None
    allowed_tools: list[str] | None = None

class AgentUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    allowed_tools: list[str] | None = None

class AgentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    system_prompt: str
    model: str | None
    allowed_tools: list | None
    created_at: datetime
    updated_at: datetime
```

### pipeline.py
```python
class PipelineStepCreate(BaseModel):
    agent_id: str
    order_index: int
    terminal_command: str | None = None

class PipelineStepResponse(BaseModel):
    id: str
    pipeline_id: str
    agent_id: str
    order_index: int
    terminal_command: str | None

class PipelineCreate(BaseModel):
    name: str
    steps: list[PipelineStepCreate] = []

class PipelineUpdate(BaseModel):
    name: str

class PipelineResponse(BaseModel):
    id: str
    project_id: str
    name: str
    steps: list[PipelineStepResponse]
    created_at: datetime
    updated_at: datetime

class StepReorderRequest(BaseModel):
    step_ids: list[str]
```

## REST endpoints

### Agents (`/api/projects/{project_id}/agents`)
- `GET /` — list agents for project
- `POST /` — create agent (body: AgentCreate)
- `GET /{agent_id}` — get agent by id
- `PUT /{agent_id}` — update agent (body: AgentUpdate)
- `DELETE /{agent_id}` — delete agent
- `POST /seed` — seed default agents

### Pipelines (`/api/projects/{project_id}/pipelines`)
- `GET /` — list pipelines for project
- `POST /` — create pipeline (body: PipelineCreate)
- `GET /{pipeline_id}` — get pipeline with steps
- `PUT /{pipeline_id}` — update pipeline name (body: PipelineUpdate)
- `DELETE /{pipeline_id}` — delete pipeline
- `POST /{pipeline_id}/steps` — add step (body: PipelineStepCreate)
- `DELETE /{pipeline_id}/steps/{step_id}` — remove step
- `PUT /{pipeline_id}/steps/reorder` — reorder steps (body: StepReorderRequest)
- `POST /seed` — seed default pipeline

## Seed trigger in start.py

After DB initialization, for each project found, call `AgentService.seed_defaults(project_id)` and `PipelineService.seed_defaults(project_id)`. Each wrapped in try/except — log warning and continue on failure. Seeds are non-fatal.

## Error handling

- `NotFoundError` when agent/pipeline/step not found
- `ValidationError` when name conflicts with existing (unique constraint on project_id + name)
- Router commits on success, rolls back on error
