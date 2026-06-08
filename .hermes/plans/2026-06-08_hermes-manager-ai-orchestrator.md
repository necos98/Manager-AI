# Hermes → Manager AI Orchestrator Integration Plan

> **For Hermes:** Execute this plan task-by-task. Each task is 5–15 min of focused work.
>
> **Goal:** Make Hermes the "brain" that orchestrates Manager AI projects via MCP — create issues, manage pipelines, and execute steps — without spawning subprocesses.
>
> **Architecture:** Hermes connects to Manager AI via MCP (`hermes mcp add manager-ai --url http://localhost:8000/mcp`) and uses MCP tools as first-class function calls. Backend changes are minimal: fix bugs in existing orchestrated pipeline code, add a `provider` field to agents, and create reusable Hermes skills that encode the orchestration workflow.
>
> **Tech Stack:** Python/FastAPI (backend), Hermes Agent (orchestrator), FastMCP (MCP server), SQLite + aiosqlite

---

## Overview of All Tasks

| # | Area | Task | Est. Time |
|---|---|---|---|
| 1 | Fix | `hermes -z` → `hermes chat -q` in HermesProvider | 2 min |
| 2 | Fix | `orchestrated` flag passthrough in `run_pipeline` MCP tool | 5 min |
| 3 | Fix | Provider-agnostic `start_step()` — replace hardcoded `claude` | 10 min |
| 4 | Feat | Add `provider` column to Agent model | 10 min |
| 5 | Feat | Accept `provider` in `create_agent` / `update_agent` MCP tools | 5 min |
| 6 | Feat | Skill: `manager-ai-orchestrator` for Hermes | 25 min |
| 7 | Feat | Skill: `manager-ai-issue-worker` for Hermes | 25 min |
| 8 | Feat | Install Hermes skills into projects + AGENTS.md | 15 min |
| 9 | Feat | Support Hermes in hooks (HookRegistry) | 10 min |
| 10 | Test | End-to-end: Hermes orchestrates a full pipeline via MCP | 15 min |

---

## Task 1: Fix `hermes -z` → `hermes chat -q` in HermesProvider

**Objective:** The `build_hook_command()` method uses the non-existent `-z` flag. Fix to use correct Hermes CLI syntax.

**Files:**
- Modify: `backend/app/providers/hermes_provider.py:50-59`

**Step 1: Edit the method**

Change:
```python
def build_hook_command(
    self, prompt: str, tool_guidance: str = ""
) -> list[str]:
    cmd = ["hermes", "-z", prompt]
    if tool_guidance:
        cmd += ["-s", "tool-guidance", "-q", prompt]
    cmd += ["--quiet"]
    return cmd
```

To:
```python
def build_hook_command(
    self, prompt: str, tool_guidance: str = ""
) -> list[str]:
    cmd = ["hermes", "chat", "-q", prompt, "--quiet"]
    if tool_guidance:
        cmd += ["-s", "tool-guidance"]
    return cmd
```

**Step 2: Verify**

```bash
cd backend
python -m pytest tests/ -k "test_hermes" -v --tb=short -n 0 2>/dev/null || true
# Also just import-check:
python -c "from app.providers.hermes_provider import HermesProvider; p = HermesProvider(); print(p.build_hook_command('hello'))"
# Expected: ['hermes', 'chat', '-q', 'hello', '--quiet']
```

---

## Task 2: Fix `orchestrated` passthrough in `run_pipeline` MCP tool

**Objective:** The MCP tool `run_pipeline` accepts `orchestrated: bool = False` but never passes it to `svc.start()`. It should create the run in `WAITING_FOR_STEP` mode when `orchestrated=True`.

**Files:**
- Modify: `backend/app/mcp/server.py:1187-1206`
- Modify: `backend/app/services/pipeline_run_service.py:47-113` (the `start()` method)

**Step 1: Update `PipelineRunService.start()` to accept and use `orchestrated`**

In `pipeline_run_service.py`, add `orchestrated: bool = False` parameter to `start()`:

```python
async def start(
    self, pipeline_id: str, issue_id: str, project_id: str, project_path: str,
    orchestrated: bool = False,
) -> dict:
    # ... existing validation checks ...

    run = PipelineRun(
        pipeline_id=pipeline_id,
        issue_id=issue_id,
        status=PipelineRunStatus.WAITING_FOR_STEP if orchestrated else PipelineRunStatus.RUNNING,
        current_step_index=0,
        orchestrated=orchestrated,
        started_at=now(),
    )
    self.session.add(run)
    await self.session.flush()

    # Create step runs (PENDING) — same as before
    step_responses = []
    for step in sorted(pipeline.steps, key=lambda s: s.order_index):
        step_run = PipelineStepRun(
            pipeline_run_id=run.id,
            pipeline_step_id=step.id,
            status=PipelineStepRunStatus.PENDING,
        )
        self.session.add(step_run)
        await self.session.flush()
        step_responses.append({"id": step_run.id, ...})

    # CRITICAL: only spawn _execute for AUTO mode (non-orchestrated)
    if not orchestrated:
        task = asyncio.create_task(
            self._execute(run.id, project_id, project_path)
        )
        await pipeline_task_manager.start_task(run.id, task)

    await self.session.commit()

    return {run_data_with_status}
```

**Step 2: Update `run_pipeline` MCP tool to forward `orchestrated`**

In `mcp/server.py`:
```python
@mcp.tool(description=_desc["tool.run_pipeline.description"])
async def run_pipeline(project_id: str, pipeline_id: str, issue_id: str,
                       orchestrated: bool = False) -> dict:
    async with async_session() as session:
        # ... get project ...
        svc = PipelineRunService(session, session_factory=async_session)
        try:
            result = await svc.start(
                pipeline_id=pipeline_id,
                issue_id=issue_id,
                project_id=project_id,
                project_path=project.path,
                orchestrated=orchestrated,  # <-- ADD THIS
            )
            await session.commit()
            return result
        except AppError as e:
            return {"error": e.message}
```

**Step 3: Verify**

```bash
cd backend
python -c "
from app.models.pipeline_run import PipelineRunStatus
print('WAITING_FOR_STEP:', PipelineRunStatus.WAITING_FOR_STEP.value)
print('orchestrated logic will use WAITING_FOR_STEP when True')
"
```

---

## Task 3: Provider-agnostic `start_step()` — replace hardcoded `claude`

**Objective:** `PipelineRunService.start_step()` (line 891) hardcodes `claude --dangerously-skip-permissions`. It should use `AgentProviderRegistry` to build the command based on the step's agent configuration (which will soon have a `provider` field).

**Files:**
- Modify: `backend/app/services/pipeline_run_service.py:826-915`

**Step 1: Add provider resolution to `start_step()`**

The method currently has:
```python
command = f'claude --dangerously-skip-permissions "/run-pipeline {run.issue_id}"'
```

Replace with provider-based command generation:

```python
from app.providers.registry import AgentProviderRegistry

# Inside start_step(), after resolving step.agent:
agent = step.agent
agent_name = agent.name if agent else "unknown"
provider_name = getattr(agent, "provider", "claude") if agent else "claude"

try:
    provider = AgentProviderRegistry.get(provider_name)
    command = provider.build_run_pipeline_command(run.issue_id)
except KeyError:
    logger.warning("Unknown provider %r, falling back to claude", provider_name)
    provider = AgentProviderRegistry.get("claude")
    command = provider.build_run_pipeline_command(run.issue_id)
```

**Step 2: Verify import works**

```bash
cd backend
python -c "from app.providers.registry import AgentProviderRegistry; print(AgentProviderRegistry.available())"
# Expected: ['claude', 'hermes']
```

---

## Task 4: Add `provider` field to Agent model

**Objective:** The `Agent` model needs a `provider` column (str, default `"claude"`) so each agent can specify which CLI to use. This requires a DB migration.

**Files:**
- Modify: `backend/app/models/agent.py`
- Create: `backend/alembic/versions/xxxx_add_agent_provider.py`

**Step 1: Add `provider` field to Agent model**

In `agent.py`:
```python
class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, ...)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="claude")
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    allowed_tools: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    intent: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # ... timestamps unchanged ...
```

**Step 2: Update `DEFAULT_AGENTS` in `agent_service.py` to include provider**

```python
DEFAULT_AGENTS = [
    {"name": "CodebaseExplorer", "provider": "claude", "intent": "..."},
    {"name": "BrainstormingAgent", "provider": "claude", ...},
    # ... all others default to "claude" for backward compat
]
```

**Step 3: Create Alembic migration**

```bash
cd backend
python -m alembic revision --autogenerate -m "add agent provider column"
python -m alembic upgrade head
```

**Step 4: Update `_serialize_agent` in `mcp/server.py`**

Add `"provider": agent.provider` to the serialized dict.

**Step 5: Run existing tests to confirm nothing broke**

```bash
cd backend
python -m pytest tests/test_agent_providers.py -v --tb=short -n 0
```

---

## Task 5: Accept `provider` in `create_agent` / `update_agent` MCP tools

**Objective:** The MCP tools `create_agent` and `update_agent` must accept the new `provider` parameter.

**Files:**
- Modify: `backend/app/mcp/server.py:973-1029`

**Step 1: Update `create_agent` tool**

Add `provider: str | None = None` parameter. Pass it through to `svc.create()`.

**Step 2: Update `update_agent` tool**

Add `provider: str | None = None` parameter. Pass it in kwargs when not None.

**Step 3: Update `default_settings.json` descriptions**

Add to the tool descriptions so Claude Code / Hermes know about the new field.

---

## Task 6: Create Hermes skill `manager-ai-orchestrator`

**Objective:** Create a reusable Hermes skill that teaches Hermes how to act as an orchestrator of Manager AI — creating issues, starting/managing pipeline runs, interpreting step results, and advancing through pipeline steps.

**Files:**
- Create: (in the Manager AI repo at a standard path, or in `~/.hermes/skills/`)
  Actually, these should be Hermes skills stored in the repo under `hermes_skills/` that get installed via `hermes skills install` or copied to `~/.hermes/skills/`.

Let's follow the same pattern as `claude_resources/skills/` → create `hermes_skills/` at the project root.

**Path:** `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\hermes_skills\manager-ai-orchestrator\SKILL.md`

**Content:**

```markdown
---
name: manager-ai-orchestrator
description: "Orchestrate Manager AI projects via MCP — create issues, run pipelines, advance steps, manage agents."
version: 1.0.0
author: Manager AI
platforms: [windows, linux, macos]
---

# Manager AI Orchestrator

You are connected to Manager AI via MCP (tool `manager-ai`). Use these patterns
to orchestrate project work.

## Prerequisites

Manager AI MCP server must be running at `http://localhost:8000/mcp` and connected
via `hermes mcp add manager-ai --url http://localhost:8000/mcp`.

## Issue Lifecycle

```
NEW → (create_issue_spec) → REASONING → (create_issue_plan) → PLANNED
  → (accept_issue) → ACCEPTED → (implement + complete_issue) → FINISHED
```

Cancel from any state with `cancel_issue`.

## Orchestrated Pipeline Workflow

1. **Create the pipeline** with agents (via `create_pipeline` or web UI)
2. **Create an issue** → write spec → write plan → accept
3. **Run the pipeline in orchestrated mode:**
   ```
   run_pipeline(project_id, pipeline_id, issue_id, orchestrated=True)
   ```
   This creates the run in `WAITING_FOR_STEP` — no subprocess is spawned.

4. **For each pipeline step, repeat:**
   - `start_pipeline_step(run_id, project_id)` — marks step RUNNING
   - Execute the step's intent (read issue, write code, review)
   - `finished_pipeline_step(issue_id, summary="...")` — signals completion
   - `advance_pipeline(run_id)` — moves to next step (or marks pipeline COMPLETED)

5. When pipeline finishes, write memories via `memory_create`.

## Agent Identity

Use `get_active_agent(issue_id)` to discover your role info in a running pipeline.
Use `get_active_pipeline_run(issue_id)` to see the full pipeline context.
Use `get_pipeline_messages(run_id)` to read handoffs from previous steps.

## Best Practices

- Always read project memories first via `memory_search`/`memory_list`
- Always check existing issue state before acting
- Use `send_notification` to alert the user of milestones
- Use `ask_user_question` when you genuinely need input
- After completing an issue, write a memory with key decisions
```

---

## Task 7: Create Hermes skill `manager-ai-issue-worker`

**Objective:** A Hermes skill that tells Hermes how to execute a single issue step — reading context, implementing changes, updating tasks, and signaling completion. This is the "worker" side of the pipeline.

**Path:** `C:\Users\j.magarelli\Desktop\manager-ai\Manager-AI\hermes_skills\manager-ai-issue-worker\SKILL.md`

**Content:**

```markdown
---
name: manager-ai-issue-worker
description: "Execute a single step in a Manager AI pipeline — read issue, implement, update tasks, signal completion."
version: 1.0.0
author: Manager AI
platforms: [windows, linux, macos]
---

# Manager AI Issue Worker

You ARE the active agent in a Manager AI pipeline. Use the MCP tools to
discover your identity, read context, execute your intent, and signal done.

## 1. Discover Your Identity

Call `get_active_agent(issue_id)` with the issue ID. The response tells you:
- **agent_name** — who you are
- **agent_intent** — YOUR primary instruction (read carefully!)
- **run_id**, **step_index** — where you fit in the pipeline

Keep this context for the duration of the step.

## 2. Read Pipeline Context

Call `get_active_pipeline_run(issue_id)` to see completed/pending/running steps.
Call `get_pipeline_messages(run_id)` to read handoffs from previous agents.

## 3. Read the Issue

Call `get_issue_details(project_id, issue_id)` to get spec, plan, tasks, status.
Read `.manager_ai/memories/` files for project context.

## 4. Execute Your Intent

Map your intent to MCP tools:

| Intent | Action |
|--------|--------|
| Spec / Design | `set_issue_name` → `create_issue_spec` |
| Planning | `create_issue_plan` → `create_plan_tasks` |
| Implementation | Read plan tasks → implement → update task statuses |
| Exploration | Trace code, document findings (read-only) |
| Review / QA | Run tests, review code, report via `send_agent_message` |

## 5. Signal Completion

When done, call:
```
finished_pipeline_step(issue_id, summary="<handoff text>")
```

The summary should include: what you did, key decisions, files changed,
constraints discovered, and guidance for the next agent.

Then simply exit. The orchestrator advances the pipeline.

## 6. Memory Write (MUST)

After completing work, extract durable facts from your summary and write them:
- `memory_create(project_id, title, description)` for new facts
- `memory_search` first to avoid duplicates
```

---

## Task 8: Install Hermes skills into projects + AGENTS.md

**Objective:** When setting up a project in Manager AI, the user should be able to install Hermes skills (analogous to "Install Claude Resources"). Add a REST endpoint + UI flow.

**Files:**
- Modify: `backend/app/routers/system.py` (add endpoint)
- Modify: `backend/app/routers/projects.py` (maybe add function)
- Create: `hermes_skills/` directory root (skills from tasks 6-7)
- Create: `hermes_skills/AGENTS.md` — the Hermes-equivalent of CLAUDE.md

**`AGENTS.md` content:**

```markdown
# AGENTS.md — Hermes Agent Guidance for Manager AI Projects

This file is loaded by Hermes when operating in this project directory.

## MCP Connection

Manager AI MCP server is at `http://localhost:8000/mcp`.
Connect Hermes with: `hermes mcp add manager-ai --url http://localhost:8000/mcp`

## Project ID

The project_id is in `manager.json` at the repo root.
Load it before calling any MCP tool that needs `project_id`.

## Memory Protocol

- READ: `grep -ri "<keywords>" .manager_ai/memories/` on the filesystem
- WRITE: `memory_create` / `memory_update` via MCP (not direct file edit)

## Key Skills

- `manager-ai-orchestrator` — orchestrate pipeline runs
- `manager-ai-issue-worker` — execute individual pipeline steps
```

**REST endpoint** (`POST /api/system/install-hermes-skills`):
- Takes a `project_path` parameter
- Copies `hermes_skills/` to `<project_path>/.hermes/skills/`
- Copies `hermes_skills/AGENTS.md` to `<project_path>/AGENTS.md`
- Returns list of copied items

---

## Task 9: Support Hermes in hooks (HookRegistry)

**Objective:** The hook system uses `ClaudeCodeExecutor` which spawns `claude -p ...` directly. Add support for Hermes-based hooks via `HermesProvider.build_hook_command()`.

**Files:**
- Read: `backend/app/hooks/handlers/` (find the executor code)

**Step 1: Find and review the hook executor**

Check how hooks currently invoke Claude Code. The hook handler likely has something like:

```python
proc = await asyncio.create_subprocess_exec(
    "claude", "-p", prompt, ...
)
```

**Step 2: Make provider configurable per-hook or globally**

Add a setting `hook_provider` (default `"claude"`) via `SettingsService`. The executor reads it and uses `AgentProviderRegistry.get(hook_provider)` to build the command.

If `hook_provider = "hermes"`, the executor uses:
```python
provider = AgentProviderRegistry.get("hermes")
cmd = provider.build_hook_command(prompt, tool_guidance)
proc = await asyncio.create_subprocess_exec(*cmd, ...)
```

**Step 3: Add endpoint to change hook provider**

`POST /api/settings` with `{"key": "hook_provider", "value": "hermes"}`

---

## Task 10: End-to-End Test

**Objective:** Verify the full integration works by creating an issue and running an orchestrated pipeline via MCP, all from Hermes.

**Test script** (`backend/tests/test_hermes_orchestration.py`):

```python
"""Test Hermes end-to-end orchestration of Manager AI via MCP tools."""

async def test_orchestrated_pipeline_flow(db_session):
    """Hermes → MCP → Manager AI: full orchestrator flow."""

    # 1. Create project
    # 2. Create agents (a SpecWriter and a Developer)
    # 3. Create a pipeline with both agents
    # 4. Create an issue
    # 5. Write spec via create_issue_spec
    # 6. Accept the issue
    # 7. Run pipeline with orchestrated=True
    #    → assert status=WAITING_FOR_STEP
    # 8. start_pipeline_step → assert status=RUNNING
    # 9. finished_pipeline_step → assert step_completed
    # 10. advance_pipeline → assert next_step or COMPLETED
    # 11. Verify terminal_id is saved, messages are created
```

**Manual verification steps (for human testing):**

1. Start Manager AI: `python start.py`
2. Create a project
3. Connect Hermes MCP: `hermes mcp add manager-ai --url http://localhost:8000/mcp`
4. Load orchestrator skill: `hermes chat --skills manager-ai-orchestrator`
5. Ask Hermes: "Create a new issue in project X, run the default pipeline in orchestrated mode"
6. Verify: issue is created, pipeline starts in WAITING_FOR_STEP, steps progress correctly

---

## Open Questions

1. **Where to store Hermes skills permanently?** In the repo under `hermes_skills/` (shippable) and installable via `hermes skills install <url>` or copied to project's `.hermes/skills/`.
2. **Should the hook system use a per-project or global provider setting?** Global setting with per-hook override is simplest for v1.
3. **Migration for existing Agents?** All existing agents get `provider="claude"` via the default column value — backward compatible.

---

## Summary of Files Changed

| File | Action | Task |
|------|--------|------|
| `backend/app/providers/hermes_provider.py` | MODIFY | 1 |
| `backend/app/mcp/server.py` | MODIFY | 2, 5 |
| `backend/app/services/pipeline_run_service.py` | MODIFY | 2, 3 |
| `backend/app/models/agent.py` | MODIFY | 4 |
| `backend/app/services/agent_service.py` | MODIFY | 4 |
| `backend/alembic/versions/*_add_agent_provider.py` | CREATE | 4 |
| `hermes_skills/manager-ai-orchestrator/SKILL.md` | CREATE | 6 |
| `hermes_skills/manager-ai-issue-worker/SKILL.md` | CREATE | 7 |
| `hermes_skills/AGENTS.md` | CREATE | 8 |
| `backend/app/routers/system.py` | MODIFY | 8 |
| `backend/app/hooks/handlers/*.py` | MODIFY | 9 |
| `backend/tests/test_hermes_orchestration.py` | CREATE | 10 |
