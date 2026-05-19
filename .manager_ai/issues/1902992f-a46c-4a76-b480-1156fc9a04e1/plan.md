# Agent Orchestration — Implementation Plan

> **Goal:** Multi-agent orchestration system with pipeline execution (Architect → Developer → Reviewer → QA) and structured inter-agent chat.

> **Architecture:** New DB models (Agent, Pipeline, PipelineRun, AgentStepRun, AgentMessage) + OrchestratorService that spawns Claude Code subprocesses per agent role. MCP tools exposed for agents to read/write chat and signal completion. Frontend with agent/pipeline editors, chat panel, and pipeline progress stepper.

> **Tech Stack:** Python FastAPI + SQLAlchemy async + FastMCP. React/Vite frontend. Claude Code CLI for agent execution. Alembic for migrations.

---

### Task 1: DB Models + Migration

**Files:**
- Create: `backend/app/models/agent.py`
- Create: `backend/app/models/pipeline.py`
- Create: `backend/app/models/agent_message.py`
- Modify: `backend/app/models/__init__.py`

**Models:**

`agent.py`:
```python
class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_key: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

`pipeline.py` (Pipeline, PipelineRun, AgentStepRun):
```python
class PipelineRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class AgentStepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Pipeline(Base):
    __tablename__ = "pipelines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    steps: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: [{"agent_id": "...", "order": 0}, ...]
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    trigger_type: Mapped[str] = mapped_column(String(50), default="issue_accepted")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipelines.id"), nullable=False)
    issue_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("issues.id"), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[PipelineRunStatus] = mapped_column(Enum(PipelineRunStatus), default=PipelineRunStatus.RUNNING)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class AgentStepRun(Base):
    __tablename__ = "agent_step_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_runs.id"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AgentStepStatus] = mapped_column(Enum(AgentStepStatus), default=AgentStepStatus.PENDING)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

`agent_message.py`:
```python
class AgentMessage(Base):
    __tablename__ = "agent_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_role: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, default="context")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

`__init__.py` — add imports for Agent, Pipeline, PipelineRun, AgentStepRun, AgentMessage.

Run: `cd backend && python -m alembic revision --autogenerate -m "add agents and pipelines" && python -m alembic upgrade head`

---

### Task 2: Schemas (Pydantic)

**Files:**
- Create: `backend/app/schemas/agent.py`
- Create: `backend/app/schemas/pipeline.py`
- Create: `backend/app/schemas/agent_message.py`

**Schemas:**

`agent.py` — AgentCreate, AgentUpdate, AgentResponse (matching model fields).
```python
from pydantic import BaseModel, Field

class AgentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    role_key: str = Field(..., max_length=100)
    system_prompt: str = ""

class AgentUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    enabled: bool | None = None

class AgentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    role_key: str
    system_prompt: str
    enabled: bool
    created_at: str | None = None
    updated_at: str | None = None
    model_config = {"from_attributes": True}
```

`pipeline.py` — PipelineCreate, PipelineUpdate, PipelineStep schema, PipelineResponse, PipelineRunResponse, AgentStepRunResponse.

`agent_message.py` — AgentMessageCreate, AgentMessageResponse.

---

### Task 3: Agent + Pipeline CRUD MCP Tools

**File:** Modify `backend/app/mcp/server.py`

Add to `default_settings.json` tool descriptions for: `list_agents`, `create_agent`, `update_agent`, `delete_agent`, `list_pipelines`, `create_pipeline`, `update_pipeline`, `delete_pipeline`.

Implement each tool matching existing patterns (async session, AppError handling, event emission).

`create_agent` emits event: `{"type": "agent_created", "project_id": ..., "agent_id": ..., "timestamp": ...}`
`update_agent` emits: `{"type": "agent_updated", ...}`
`delete_agent` emits: `{"type": "agent_deleted", ...}`

Same pattern for pipelines.

---

### Task 4: OrchestratorService

**File:** Create `backend/app/services/orchestrator_service.py`

Core service that manages pipeline execution:

```python
class OrchestratorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.executor = ClaudeCodeExecutor()

    async def start_pipeline(self, trigger_type: str, issue_id: str | None = None) -> PipelineRun:
        """Find default pipeline for project, create PipelineRun + AgentStepRuns, begin execution."""
        # 1. Find default pipeline for project from issue.project_id
        # 2. Create PipelineRun (status=running)
        # 3. Create AgentStepRun for each step in pipeline.steps JSON
        # 4. asyncio.create_task(_run_pipeline(pipeline_run))
        # 5. Return pipeline_run
        ...

    async def _run_pipeline(self, pipeline_run: PipelineRun) -> None:
        """Execute each step sequentially."""
        steps = await self._get_step_runs(pipeline_run.id)  # ordered by step_order
        for step in steps:
            success = await self._run_agent_step(pipeline_run, step)
            if not success:
                pipeline_run.status = PipelineRunStatus.PAUSED
                return
        pipeline_run.status = PipelineRunStatus.COMPLETED
        pipeline_run.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self._emit_event("pipeline_completed", ...)

    async def _run_agent_step(self, pipeline_run: PipelineRun, step: AgentStepRun) -> bool:
        """Execute single agent step via ClaudeCodeExecutor."""
        agent = await self.session.get(Agent, step.agent_id)
        issue = await self.session.get(Issue, pipeline_run.issue_id) if pipeline_run.issue_id else None

        prompt = self._build_prompt(agent, issue, pipeline_run.issue_id)
        env_vars = {"MANAGER_AI_PROJECT_ID": agent.project_id}
        result = await self.executor.run(prompt=prompt, project_path=..., env_vars=env_vars)

        # Agent signals completion via MCP tool (complete_agent_step)
        # This method is called by the MCP tool, not directly
        ...

    def _build_prompt(self, agent: Agent, issue: Issue | None, issue_id: str | None) -> str:
        """Build Claude Code prompt for agent."""
        parts = [agent.system_prompt]
        if issue:
            parts.append(f"## Issue: {issue.name or issue.description}")
            if issue.specification:
                parts.append(f"## Specification\n{issue.specification}")
            if issue.plan:
                parts.append(f"## Plan\n{issue.plan}")
        parts.append("## Agent Chat")
        parts.append("Use `send_agent_message` to communicate decisions and context.")
        parts.append("When finished, call `complete_agent_step` with a summary of your work.")
        return "\n\n".join(parts)

    async def complete_agent_step(self, pipeline_run_id: str, summary: str) -> bool:
        """Called via MCP tool when agent finishes. Transitions to next step."""
        # Find current running step, mark completed
        # Start next pending step or complete pipeline
        ...

    async def get_pipeline_status(self, pipeline_run_id: str) -> dict:
        """Return current pipeline state with all step statuses."""
        ...
```

Also create MCP tools that the OrchestratorService exposes to Claude Code agents:
- `complete_agent_step(pipeline_run_id, summary)` — agent calls this when done
- `send_agent_message(issue_id, content, message_type)` — write to chat
- `get_agent_messages(issue_id)` — read chat history
- `get_pipeline_status(pipeline_run_id)` — check pipeline state
- `start_pipeline(issue_id)` — manual trigger from UI

---

### Task 5: Integrate accept_issue → auto-start pipeline

**File:** Modify `backend/app/mcp/server.py` — the `accept_issue` tool

After `await session.commit()` in `accept_issue`, add:

```python
# Auto-start default pipeline if one exists
from app.services.orchestrator_service import OrchestratorService
orchestrator = OrchestratorService(session)
try:
    pipeline_run = await orchestrator.start_pipeline(
        trigger_type="issue_accepted",
        issue_id=issue_id
    )
    return {"id": issue_id, "status": issue_status, "pipeline_run_id": pipeline_run.id}
except Exception:
    # Pipeline start failure doesn't block issue acceptance
    logger.warning("Failed to auto-start pipeline for issue %s", issue_id, exc_info=True)
    return {"id": issue_id, "status": issue_status}
```

---

### Task 6: WebSocket Events

**File:** Modify `backend/app/services/event_service.py`

New event types emitted by OrchestratorService:
- `agent_step_started` — `{issue_id, pipeline_run_id, step_index, agent_name, agent_role}`
- `agent_step_completed` — `{issue_id, pipeline_run_id, step_index, agent_name, summary}`
- `agent_step_failed` — `{issue_id, pipeline_run_id, step_index, agent_name, error}`
- `agent_message_added` — `{issue_id, message: full AgentMessage dict}`
- `pipeline_completed` — `{issue_id, pipeline_run_id, total_steps, duration}`

Frontend `EventProvider` already handles `type`-based routing — new event types are automatically dispatched. Frontend components just subscribe to them.

---

### Task 7: Frontend — Agent Definitions + Pipeline Editor

**Files:**
- Create: `frontend/src/pages/ProjectSettings/AgentsTab.jsx`
- Create: `frontend/src/pages/ProjectSettings/PipelinesTab.jsx`
- Modify: `frontend/src/pages/ProjectSettings.jsx` (add tabs)

**AgentsTab:**
- Fetch agents via `GET /api/agents?project_id=...`
- Table: name, role_key, enabled toggle (switch), edit button
- Edit modal: textarea for system_prompt, save calls `PUT /api/agents/{id}`
- Add button: form with name, role_key, system_prompt → `POST /api/agents`
- Delete button with confirm

**PipelinesTab:**
- Fetch pipelines via `GET /api/pipelines?project_id=...`
- List of pipelines, one starred as default
- Click to edit: shows ordered list of agents (drag handle reorder)
- Add step: dropdown of available agents → append to list
- Remove step button
- Save: `PUT /api/pipelines/{id}` with steps JSON
- Create new: name + select agents → `POST /api/pipelines`
- Set default: radio/star toggle

---

### Task 8: Frontend — Agent Chat Panel + Pipeline Progress

**Files:**
- Create: `frontend/src/components/AgentChat.jsx`
- Create: `frontend/src/components/PipelineProgress.jsx`
- Modify: `frontend/src/pages/IssueDetail.jsx`

**PipelineProgress:**
- Horizontal stepper (CSS flexbox with connectors)
- Each step = circle with agent initial + label
- Status colors: gray (#9ca3af) pending, blue (#3b82f6) running with spinner, green (#22c55e) completed, red (#ef4444) failed
- Current step has animated pulse border
- Props: `pipelineRunId` → fetches `GET /api/pipelines/runs/{id}`

**AgentChat:**
- Scrollable message list (max-height, overflow-y: auto)
- Each message card: rounded, left-aligned, with colored left border
- Header: agent name (bold) + role badge + timestamp (relative)
- Body: message content (monospace, pre-wrap for code)
- Footer: message_type chip (small colored tag)
- New messages arrive via WebSocket (`agent_message_added` event)
- Auto-scroll to bottom on new message

**IssueDetail integration:**
- Right sidebar: Tabs "Agent Chat" | "Pipeline"
- Pipeline tab visible when pipeline is running/completed
- Chat tab always visible, shows "No agent activity yet" when empty

---

### Task 9: Default Agents Seeding

**File:** Create migration or seed script

On project creation (or first agent list request for a project), auto-create 4 default agents:

```python
DEFAULT_AGENTS = [
    {"name": "Architect", "role_key": "architect",
     "system_prompt": "You are a Software Architect. Analyze requirements, design system architecture, write technical specifications. Output concise, actionable specs. When done, call complete_agent_step with your architectural decisions."},
    {"name": "Developer", "role_key": "developer",
     "system_prompt": "You are a Senior Developer. Implement code following the specification. Write tests. Keep code clean and follow existing patterns. When done, call complete_agent_step with implementation summary."},
    {"name": "Reviewer", "role_key": "reviewer",
     "system_prompt": "You are a Code Reviewer. Review the implementation for bugs, security issues, code quality. Check adherence to spec. When done, call complete_agent_step with review findings."},
    {"name": "QA", "role_key": "qa",
     "system_prompt": "You are a QA Engineer. Verify the implementation meets requirements. Run tests, check edge cases, validate acceptance criteria. When done, call complete_agent_step with test results."},
]

DEFAULT_PIPELINE = {
    "name": "Default",
    "steps": [
        {"agent_role": "architect", "order": 0},
        {"agent_role": "developer", "order": 1},
        {"agent_role": "reviewer", "order": 2},
        {"agent_role": "qa", "order": 3},
    ],
    "is_default": True,
    "trigger_type": "issue_accepted",
}
```

Seed logic in `OrchestratorService.ensure_default_agents(project_id)` — called on first agent list request. Idempotent (checks if agents already exist).

---

### Task 10: Testing

**File:** Create `backend/tests/test_orchestrator.py`

Test cases:
1. `test_create_agent` — create agent via MCP tool, verify response
2. `test_list_agents` — list agents for project
3. `test_create_pipeline` — create pipeline with steps
4. `test_start_pipeline_manual` — trigger pipeline manually, verify PipelineRun created
5. `test_send_agent_message` — write chat message, read back
6. `test_get_agent_messages` — returns messages ordered by created_at
7. `test_complete_agent_step` — complete step, verify next step transitions
8. `test_pipeline_completion` — complete all steps, verify pipeline marked completed
9. `test_accept_issue_triggers_pipeline` — accept issue, verify PipelineRun created
10. `test_default_agents_seeded` — first list request seeds defaults

Uses async in-memory SQLite with `asyncio_mode = "auto"` (existing test config).

Run: `cd backend && python -m pytest tests/test_orchestrator.py -v`
