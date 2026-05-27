# Implementation Plan: AgentService + PipelineService

## Files map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `backend/app/schemas/agent.py` | Pydantic models for Agent CRUD |
| Create | `backend/app/schemas/pipeline.py` | Pydantic models for Pipeline + Step CRUD |
| Modify | `backend/app/schemas/__init__.py` | Export new schema classes |
| Create | `backend/app/services/agent_service.py` | AgentService: CRUD + seed_defaults() |
| Create | `backend/app/services/pipeline_service.py` | PipelineService: CRUD pipeline/step + seed_defaults() |
| Create | `backend/app/routers/agents.py` | REST endpoints for agents |
| Create | `backend/app/routers/pipelines.py` | REST endpoints for pipelines |
| Modify | `backend/app/main.py` | Register agents and pipelines routers |
| Modify | `start.py` | Call seed_defaults() on startup |

---

## Task 1: Agent schemas

**Create:** `backend/app/schemas/agent.py`

```python
from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    system_prompt: str = Field(..., min_length=1)
    model: str | None = None
    allowed_tools: list[str] | None = None


class AgentUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    system_prompt: str | None = None
    model: str | None = None
    allowed_tools: list[str] | None = None


class AgentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    system_prompt: str
    model: str | None = None
    allowed_tools: list | None = None
    created_at: str | None = None
    updated_at: str | None = None
```

## Task 2: Pipeline schemas

**Create:** `backend/app/schemas/pipeline.py`

Note: `terminal_command` is NOT NULL in the model (defaults to empty string), so we treat it as `str` not `str | None`.

```python
from pydantic import BaseModel, Field


class PipelineStepCreate(BaseModel):
    agent_id: str = Field(..., min_length=1)
    order_index: int = Field(default=0, ge=0)
    terminal_command: str = ""


class PipelineStepResponse(BaseModel):
    id: str
    pipeline_id: str
    agent_id: str
    order_index: int
    terminal_command: str


class PipelineCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    steps: list[PipelineStepCreate] = []


class PipelineUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class PipelineResponse(BaseModel):
    id: str
    project_id: str
    name: str
    steps: list[PipelineStepResponse] = []
    created_at: str | None = None
    updated_at: str | None = None


class StepReorderRequest(BaseModel):
    step_ids: list[str] = Field(..., min_length=1)
```

## Task 3: Update schemas __init__.py

**Modify:** `backend/app/schemas/__init__.py`

Add new exports:
```python
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.schemas.pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineStepCreate,
    PipelineStepResponse,
    PipelineUpdate,
    StepReorderRequest,
)
```

Update `__all__` list.

## Task 4: AgentService

**Create:** `backend/app/services/agent_service.py`

Follows CredentialService pattern: `AsyncSession` per instance, SQLAlchemy ORM queries, `flush()` on mutations.

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.agent import Agent

DEFAULT_AGENTS = [
    {
        "name": "CodebaseExplorer",
        "system_prompt": (
            "Explore and analyze codebase structure, find patterns and conventions, "
            "trace execution paths, and document dependencies."
        ),
    },
    {
        "name": "BrainstormingAgent",
        "system_prompt": (
            "Brainstorm ideas and refine requirements through natural collaborative dialogue. "
            "Turn ideas into fully formed designs and specs."
        ),
    },
    {
        "name": "SpecWriter",
        "system_prompt": (
            "Write detailed specifications from requirements. Produce clear, structured "
            "specs covering architecture, components, data flow, error handling, and testing."
        ),
    },
    {
        "name": "PlanWriter",
        "system_prompt": (
            "Create implementation plans from specifications. Break down designs into "
            "atomic, ordered tasks with specific files to create or modify."
        ),
    },
    {
        "name": "Developer",
        "system_prompt": (
            "Implement code following plans and specifications. Write production-quality "
            "code that follows existing patterns and conventions."
        ),
    },
    {
        "name": "Reviewer",
        "system_prompt": (
            "Review code for bugs, logic errors, security vulnerabilities, code quality "
            "issues, and adherence to project conventions."
        ),
    },
]


class AgentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── seed ──────────────────────────────────────────────────────────

    async def seed_defaults(self, project_id: str) -> list[Agent]:
        """Idempotent. Creates 6 default agents only if project has 0 agents."""
        existing = await self.list_by_project(project_id)
        if existing:
            return existing
        agents = []
        for data in DEFAULT_AGENTS:
            agent = Agent(project_id=project_id, name=data["name"], system_prompt=data["system_prompt"])
            self.session.add(agent)
            agents.append(agent)
        await self.session.flush()
        return agents

    # ── CRUD ──────────────────────────────────────────────────────────

    async def create(
        self,
        project_id: str,
        name: str,
        system_prompt: str,
        model: str | None = None,
        allowed_tools: list[str] | None = None,
    ) -> Agent:
        agent = Agent(
            project_id=project_id,
            name=name,
            system_prompt=system_prompt,
            model=model,
            allowed_tools=allowed_tools,
        )
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def get_by_id(self, agent_id: str) -> Agent:
        result = await self.session.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if agent is None:
            raise NotFoundError(f"Agent not found: {agent_id}")
        return agent

    async def get_by_name(self, project_id: str, name: str) -> Agent | None:
        result = await self.session.execute(
            select(Agent).where(Agent.project_id == project_id, Agent.name == name)
        )
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: str) -> list[Agent]:
        result = await self.session.execute(
            select(Agent).where(Agent.project_id == project_id).order_by(Agent.name)
        )
        return list(result.scalars().all())

    async def update(self, agent_id: str, **kwargs) -> Agent:
        agent = await self.get_by_id(agent_id)
        for key, value in kwargs.items():
            if value is not None and hasattr(agent, key):
                setattr(agent, key, value)
        await self.session.flush()
        return agent

    async def delete(self, agent_id: str) -> bool:
        agent = await self.get_by_id(agent_id)
        await self.session.delete(agent)
        await self.session.flush()
        return True
```

## Task 5: PipelineService

**Create:** `backend/app/services/pipeline_service.py`

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.pipeline import Pipeline, PipelineStep
from app.services.agent_service import AgentService


class PipelineService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── seed ──────────────────────────────────────────────────────────

    async def seed_defaults(self, project_id: str) -> Pipeline:
        """Idempotent. Creates 6-step pipeline only if project has 0 pipelines."""
        existing = await self.list_by_project(project_id)
        if existing:
            return existing[0]
        agent_svc = AgentService(self.session)
        agents = await agent_svc.list_by_project(project_id)
        pipeline = Pipeline(project_id=project_id, name="Default Pipeline")
        self.session.add(pipeline)
        await self.session.flush()
        for i, agent in enumerate(agents):
            step = PipelineStep(
                pipeline_id=pipeline.id,
                agent_id=agent.id,
                order_index=i,
                terminal_command="",
            )
            self.session.add(step)
        await self.session.flush()
        return pipeline

    # ── Pipeline CRUD ─────────────────────────────────────────────────

    async def create_pipeline(self, project_id: str, name: str) -> Pipeline:
        pipeline = Pipeline(project_id=project_id, name=name)
        self.session.add(pipeline)
        await self.session.flush()
        return pipeline

    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        result = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.id == pipeline_id)
            .options(selectinload(Pipeline.steps))
        )
        pipeline = result.scalar_one_or_none()
        if pipeline is None:
            raise NotFoundError(f"Pipeline not found: {pipeline_id}")
        return pipeline

    async def list_by_project(self, project_id: str) -> list[Pipeline]:
        result = await self.session.execute(
            select(Pipeline)
            .where(Pipeline.project_id == project_id)
            .options(selectinload(Pipeline.steps))
            .order_by(Pipeline.name)
        )
        return list(result.unique().scalars().all())

    async def update_pipeline(self, pipeline_id: str, name: str) -> Pipeline:
        pipeline = await self.get_pipeline(pipeline_id)
        pipeline.name = name
        await self.session.flush()
        return pipeline

    async def delete_pipeline(self, pipeline_id: str) -> bool:
        pipeline = await self.get_pipeline(pipeline_id)
        await self.session.delete(pipeline)
        await self.session.flush()
        return True

    # ── Step CRUD ─────────────────────────────────────────────────────

    async def add_step(
        self,
        pipeline_id: str,
        agent_id: str,
        order_index: int,
        terminal_command: str = "",
    ) -> PipelineStep:
        step = PipelineStep(
            pipeline_id=pipeline_id,
            agent_id=agent_id,
            order_index=order_index,
            terminal_command=terminal_command,
        )
        self.session.add(step)
        await self.session.flush()
        return step

    async def remove_step(self, step_id: str) -> bool:
        result = await self.session.execute(
            select(PipelineStep).where(PipelineStep.id == step_id)
        )
        step = result.scalar_one_or_none()
        if step is None:
            raise NotFoundError(f"Pipeline step not found: {step_id}")
        await self.session.delete(step)
        await self.session.flush()
        return True

    async def reorder_steps(self, pipeline_id: str, step_ids: list[str]) -> list[PipelineStep]:
        steps = []
        for i, step_id in enumerate(step_ids):
            result = await self.session.execute(
                select(PipelineStep).where(PipelineStep.id == step_id, PipelineStep.pipeline_id == pipeline_id)
            )
            step = result.scalar_one_or_none()
            if step is None:
                raise NotFoundError(f"Pipeline step not found: {step_id}")
            step.order_index = i
            steps.append(step)
        await self.session.flush()
        return steps
```

## Task 6: Agents router

**Create:** `backend/app/routers/agents.py`

Follows credentials router pattern with per-endpoint service instantiation.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/projects/{project_id}/agents", tags=["agents"])


def _response(agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        project_id=agent.project_id,
        name=agent.name,
        system_prompt=agent.system_prompt,
        model=agent.model,
        allowed_tools=agent.allowed_tools,
        created_at=str(agent.created_at) if agent.created_at else None,
        updated_at=str(agent.updated_at) if agent.updated_at else None,
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agents = await svc.list_by_project(project_id)
    return [_response(a) for a in agents]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(project_id: str, data: AgentCreate, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agent = await svc.create(
        project_id=project_id,
        name=data.name,
        system_prompt=data.system_prompt,
        model=data.model,
        allowed_tools=data.allowed_tools,
    )
    await db.commit()
    return _response(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(project_id: str, agent_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agent = await svc.get_by_id(agent_id)
    return _response(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(project_id: str, agent_id: str, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agent = await svc.update(
        agent_id,
        name=data.name,
        system_prompt=data.system_prompt,
        model=data.model,
        allowed_tools=data.allowed_tools,
    )
    await db.commit()
    return _response(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(project_id: str, agent_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    await svc.delete(agent_id)
    await db.commit()


@router.post("/seed", response_model=list[AgentResponse], status_code=201)
async def seed_agents(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = AgentService(db)
    agents = await svc.seed_defaults(project_id)
    await db.commit()
    return [_response(a) for a in agents]
```

## Task 7: Pipelines router

**Create:** `backend/app/routers/pipelines.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineStepCreate,
    PipelineStepResponse,
    PipelineUpdate,
    StepReorderRequest,
)
from app.services.pipeline_service import PipelineService

router = APIRouter(prefix="/api/projects/{project_id}/pipelines", tags=["pipelines"])


def _step_response(step) -> PipelineStepResponse:
    return PipelineStepResponse(
        id=step.id,
        pipeline_id=step.pipeline_id,
        agent_id=step.agent_id,
        order_index=step.order_index,
        terminal_command=step.terminal_command,
    )


def _response(pipeline) -> PipelineResponse:
    return PipelineResponse(
        id=pipeline.id,
        project_id=pipeline.project_id,
        name=pipeline.name,
        steps=[_step_response(s) for s in (pipeline.steps or [])],
        created_at=str(pipeline.created_at) if pipeline.created_at else None,
        updated_at=str(pipeline.updated_at) if pipeline.updated_at else None,
    )


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipelines = await svc.list_by_project(project_id)
    return [_response(p) for p in pipelines]


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(project_id: str, data: PipelineCreate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.create_pipeline(project_id, data.name)
    for step_data in data.steps:
        await svc.add_step(
            pipeline_id=pipeline.id,
            agent_id=step_data.agent_id,
            order_index=step_data.order_index,
            terminal_command=step_data.terminal_command,
        )
    await db.commit()
    return _response(await svc.get_pipeline(pipeline.id))


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(project_id: str, pipeline_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.get_pipeline(pipeline_id)
    return _response(pipeline)


@router.put("/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(project_id: str, pipeline_id: str, data: PipelineUpdate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.update_pipeline(pipeline_id, data.name)
    await db.commit()
    return _response(pipeline)


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(project_id: str, pipeline_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    await svc.delete_pipeline(pipeline_id)
    await db.commit()


@router.post("/{pipeline_id}/steps", response_model=PipelineStepResponse, status_code=201)
async def add_step(project_id: str, pipeline_id: str, data: PipelineStepCreate, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    step = await svc.add_step(
        pipeline_id=pipeline_id,
        agent_id=data.agent_id,
        order_index=data.order_index,
        terminal_command=data.terminal_command,
    )
    await db.commit()
    return _step_response(step)


@router.delete("/{pipeline_id}/steps/{step_id}", status_code=204)
async def remove_step(project_id: str, pipeline_id: str, step_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    await svc.remove_step(step_id)
    await db.commit()


@router.put("/{pipeline_id}/steps/reorder", response_model=list[PipelineStepResponse])
async def reorder_steps(project_id: str, pipeline_id: str, data: StepReorderRequest, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    steps = await svc.reorder_steps(pipeline_id, data.step_ids)
    await db.commit()
    return [_step_response(s) for s in steps]


@router.post("/seed", response_model=PipelineResponse, status_code=201)
async def seed_pipeline(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    pipeline = await svc.seed_defaults(project_id)
    await db.commit()
    return _response(await svc.get_pipeline(pipeline.id))
```

## Task 8: Register routers in main.py

**Modify:** `backend/app/main.py`

Add imports:
```python
from app.routers import agents, pipelines
```

Add router registration (after issue_relations):
```python
app.include_router(agents.router)
app.include_router(pipelines.router)
```

## Task 9: Seed trigger in start.py

**Modify:** `start.py`

Find section after DB init where projects are loaded. Add seed calls:

```python
# Seed default agents and pipelines for each project
try:
    from app.services.agent_service import AgentService
    from app.services.pipeline_service import PipelineService
    async with async_session() as session:
        from sqlalchemy import select
        from app.models.project import Project
        rows = (await session.execute(select(Project))).scalars().all()
        for p in rows:
            try:
                await AgentService(session).seed_defaults(p.id)
                await PipelineService(session).seed_defaults(p.id)
                await session.commit()
            except Exception:
                logger.warning("Failed to seed defaults for project %s", p.id, exc_info=True)
except Exception:
    logger.exception("Failed to seed default agents/pipelines; continuing startup")
```

Placement: inside the lifespan function, after `_load_project_into_memory` loop, before the `yield`. This ensures DB is ready and projects exist.
