# Implementation Plan: Pipeline Agent Execution Flow Fix

## File Map

| File | Responsibility |
|------|---------------|
| `backend/app/services/agent_service.py` | DEFAULT_AGENTS definitions + seeding |
| `backend/app/mcp/server.py` | MCP tool implementations |
| `backend/app/mcp/default_settings.json` | MCP tool descriptions |
| `backend/app/services/pipeline_run_service.py` | Orchestrator: step execution, event gating, timeout |
| `.claude/commands/run-pipeline.md` | Agent instructions in PTY session |
| `claude_resources/commands/run-pipeline.md` | Sync copy of run-pipeline.md |
| `backend/tests/test_pipeline_run_service.py` | Pipeline run service tests |

---

### Task 1: Populate agent intents in DEFAULT_AGENTS

**Files:** Modify `backend/app/services/agent_service.py`

Add `intent` field to each of the 6 DEFAULT_AGENTS. The `intent` is what the agent reads from `MANAGER_AI_AGENT_INTENT` and from `run_pipeline_step` response. Also pass `intent` to the Agent() constructor in `seed_defaults()`.

DEFAULT_AGENTS becomes:
```python
DEFAULT_AGENTS = [
    {
        "name": "CodebaseExplorer",
        "system_prompt": (
            "Explore and analyze codebase structure, find patterns and conventions, "
            "trace execution paths, and document dependencies."
        ),
        "intent": (
            "Explore the codebase to understand structure, patterns, and dependencies. "
            "Trace relevant code paths. Identify files that need changes. "
            "Document findings. Do NOT modify files — this is analysis only."
        ),
    },
    {
        "name": "BrainstormingAgent",
        "system_prompt": (
            "Brainstorm ideas and refine requirements through natural collaborative dialogue. "
            "Turn ideas into fully formed designs and specs."
        ),
        "intent": (
            "Analyze the issue description and brainstorm requirements. "
            "Ask clarifying questions if needed. Write a detailed specification "
            "via create_issue_spec. Set issue name via set_issue_name."
        ),
    },
    {
        "name": "SpecWriter",
        "system_prompt": (
            "Write detailed specifications from requirements. Produce clear, structured "
            "specs covering architecture, components, data flow, error handling, and testing."
        ),
        "intent": (
            "Analyze the issue description, ask clarifying questions if needed, "
            "write a detailed specification covering requirements, constraints, "
            "and success criteria. Save via create_issue_spec. "
            "Set issue name via set_issue_name."
        ),
    },
    {
        "name": "PlanWriter",
        "system_prompt": (
            "Create implementation plans from specifications. Break down designs into "
            "atomic, ordered tasks with specific files to create or modify."
        ),
        "intent": (
            "Review the specification. Design an implementation plan with concrete steps, "
            "identify files to create/modify, and define atomic tasks. "
            "Save via create_issue_plan and create_plan_tasks."
        ),
    },
    {
        "name": "Developer",
        "system_prompt": (
            "Implement code following plans and specifications. Write production-quality "
            "code that follows existing patterns and conventions."
        ),
        "intent": (
            "Read the plan tasks via get_plan_tasks. Implement each task sequentially — "
            "update status to In Progress when starting, Completed when done. "
            "Follow existing codebase patterns. Make autonomous decisions. "
            "Do NOT ask for confirmations."
        ),
    },
    {
        "name": "Reviewer",
        "system_prompt": (
            "Review code for bugs, logic errors, security vulnerabilities, code quality "
            "issues, and adherence to project conventions."
        ),
        "intent": (
            "Review all code changes for bugs, logic errors, security issues, "
            "and adherence to project conventions. Run the test suite. "
            "Report findings via send_agent_message with specific, "
            "actionable feedback for the QA agent."
        ),
    },
]
```

Update `seed_defaults()` to pass `intent`:
```python
async def seed_defaults(self) -> list[Agent]:
    existing = await self.list_all()
    if existing:
        return existing
    agents = []
    for data in DEFAULT_AGENTS:
        agent = Agent(
            name=data["name"],
            system_prompt=data["system_prompt"],
            intent=data.get("intent", ""),
        )
        self.session.add(agent)
        agents.append(agent)
    await self.session.flush()
    return agents
```

---

### Task 2: Add get_active_pipeline_run MCP tool

**Files:** Modify `backend/app/mcp/server.py`

Add after `get_active_agent` tool (around L1123). Description already exists in `default_settings.json` at L74.

```python
@mcp.tool(description=_desc["tool.get_active_pipeline_run.description"])
async def get_active_pipeline_run(issue_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "RUNNING"), None)
        if not active:
            return {"active": None}
        return active
```

Also update `get_active_agent` to include `run_id` and `agent_intent` since run-pipeline.md step 1 expects them:
```python
@mcp.tool(description=_desc["tool.get_active_agent.description"])
async def get_active_agent(issue_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "RUNNING"), None)
        if not active:
            return {"active": None}
        steps = active["steps"]
        idx = active["current_step_index"]
        if idx >= len(steps):
            return {"active": None}
        step = steps[idx]
        return {
            "run_id": active["id"],
            "agent_name": step["agent_name"],
            "agent_intent": step.get("agent_intent", ""),
            "step_index": idx,
            "step_status": step["status"],
            "terminal_id": step.get("terminal_id"),
        }
```

This requires adding `agent_intent` to step dicts in `get_runs_for_issue()` and `get_run()` in `pipeline_run_service.py`. Add `"agent_intent": sr.pipeline_step.agent.intent if sr.pipeline_step and sr.pipeline_step.agent else ""` to each step dict.

---

### Task 3: Add run_pipeline_step MCP tool

**Files:** Modify `backend/app/mcp/server.py`, `backend/app/mcp/default_settings.json`

Add description to `default_settings.json`:
```json
"tool.run_pipeline_step.description": "Claim the current pipeline step for an issue. Call this when you start working as a pipeline agent. Returns your agent identity, intent, and step context. Parameters: issue_id (required). Returns: {run_id, step_run_id, agent_name, agent_intent, step_index, terminal_id}. Returns {active: null} if no pipeline is running for this issue."
```

Add tool in `server.py`:
```python
@mcp.tool(description=_desc["tool.run_pipeline_step.description"])
async def run_pipeline_step(issue_id: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "RUNNING"), None)
        if not active:
            return {"active": None}
        steps = active["steps"]
        idx = active["current_step_index"]
        if idx >= len(steps):
            return {"active": None}
        step = steps[idx]
        return {
            "run_id": active["id"],
            "step_run_id": step["id"],
            "agent_name": step["agent_name"],
            "agent_intent": step.get("agent_intent", ""),
            "step_index": idx,
            "terminal_id": step.get("terminal_id"),
        }
```

---

### Task 4: Add finished_pipeline_step MCP tool

**Files:** Modify `backend/app/mcp/server.py`, `backend/app/mcp/default_settings.json`, `backend/app/services/pipeline_run_service.py`

Add description to `default_settings.json`:
```json
"tool.finished_pipeline_step.description": "Signal completion of your pipeline step. Call this when you have finished all work for your step. Parameters: issue_id (required), summary (required, string — handoff summary for the next agent). Returns: {success, step_completed, pipeline_finished}. The pipeline automatically advances to the next step."
```

Add method to `PipelineRunService`:
```python
def set_step_completed(self, run_id: str, step_index: int) -> bool:
    key = (run_id, step_index)
    event = _step_completion_events.get(key)
    if event is None:
        return False
    event.set()
    return True
```

Add tool in `server.py`:
```python
@mcp.tool(description=_desc["tool.finished_pipeline_step.description"])
async def finished_pipeline_step(issue_id: str, summary: str) -> dict:
    async with async_session() as session:
        svc = PipelineRunService(session)
        runs = await svc.get_runs_for_issue(issue_id)
        active = next((r for r in runs if r["status"] == "RUNNING"), None)
        if not active:
            return {"error": "No active pipeline run for this issue"}
        
        run_id = active["id"]
        idx = active["current_step_index"]
        steps = active["steps"]
        if idx >= len(steps):
            return {"error": "No active step"}
        
        step = steps[idx]
        agent_name = step["agent_name"]
        
        # Save summary as agent message (handoff)
        await svc.add_message(
            run_id=run_id,
            sender_agent_name=agent_name,
            content=summary,
        )
        
        # Signal completion
        ok = svc.set_step_completed(run_id, idx)
        
        # Determine if this was the last step
        pipeline_finished = idx >= len(steps) - 1
        
        await session.commit()
        return {
            "success": ok,
            "step_completed": ok,
            "pipeline_finished": pipeline_finished,
        }
```

---

### Task 5: Implement event-based step gating in orchestrator

**Files:** Modify `backend/app/services/pipeline_run_service.py`

Add module-level dict near top of file (after imports, before class):
```python
# Maps (run_id, step_index) -> asyncio.Event for step completion signaling
_step_completion_events: dict[tuple[str, int], asyncio.Event] = {}
```

Add `set_step_completed` static/module-level function:
```python
def set_step_completed(run_id: str, step_index: int) -> bool:
    key = (run_id, step_index)
    event = _step_completion_events.get(key)
    if event is None:
        return False
    event.set()
    return True
```

Modify `_run_step()` method — replace the `await session.pty_dead.wait()` pattern with event-based gating. Changes to `_run_step()`:
```python
async def _run_step(
    self,
    term_id: str,
    agent_name: str,
    intent: str,
    issue_id: str,
    run_id: str,
    step_index: int,
) -> bool:
    import platform as _platform
    import os as _os
    from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

    pty = terminal_service.get_pty(term_id)

    session = TerminalSession()
    _sessions[term_id] = session
    _ensure_reader(term_id, terminal_service)

    is_windows = _platform.system() == "Windows"
    command = f'claude --dangerously-skip-permissions "/run-pipeline {issue_id}"'

    if is_windows:
        pty.write(f"set MANAGER_AI_AGENT_NAME={agent_name}\r\n")
        pty.write(f"set MANAGER_AI_AGENT_ROLE={agent_name}\r\n")
        pty.write(f"set MANAGER_AI_AGENT_INTENT={intent}\r\n")
        pty.write(f"set MANAGER_AI_ISSUE_ID={issue_id}\r\n")
        pty.write(f"{command}\r\n")
        pty.write("exit\r\n")
    else:
        import shlex as _shlex
        pty.write(f"export MANAGER_AI_AGENT_NAME={_shlex.quote(agent_name)}\r\n")
        pty.write(f"export MANAGER_AI_AGENT_ROLE={_shlex.quote(agent_name)}\r\n")
        pty.write(f"export MANAGER_AI_AGENT_INTENT={_shlex.quote(intent)}\r\n")
        pty.write(f"export MANAGER_AI_ISSUE_ID={_shlex.quote(issue_id)}\r\n")
        pty.write(f"{command}; exit\r\n")

    # Wait for step completion event or PTY death
    event = asyncio.Event()
    _step_completion_events[(run_id, step_index)] = event
    
    timeout = int(_os.environ.get("MANAGER_AI_PIPELINE_STEP_TIMEOUT", "1800"))
    
    async def wait_pty_death():
        await session.pty_dead.wait()
    
    pty_task = asyncio.create_task(wait_pty_death())
    event_task = asyncio.create_task(event.wait())
    
    try:
        done, pending = await asyncio.wait(
            [pty_task, event_task],
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        if event_task in done:
            # Agent explicitly called finished_pipeline_step
            success = True
        elif pty_task in done:
            # PTY died — agent exited without calling finished_pipeline_step
            logger.warning(
                "Step %s PTY died before finished_pipeline_step called", agent_name
            )
            success = session.pty_died_naturally
        else:
            # Timeout
            logger.error("Step %s timed out after %ds", agent_name, timeout)
            terminal_service.kill(term_id)
            success = False
        
        # Cancel any unfinished tasks
        for t in pending:
            t.cancel()
    finally:
        _step_completion_events.pop((run_id, step_index), None)
    
    return success
```

Update the call site in `_execute()` to pass `run_id` and `step_index`:
```python
success = await self._run_step(
    term_id=term_id,
    agent_name=agent_name,
    intent=agent_prompt,
    issue_id=run.issue_id,
    run_id=run_id,
    step_index=i,
)
```

Also add `agent_intent` to step dicts in `get_runs_for_issue()` and `get_run()`. In both methods, add this field to each step dict:
```python
"agent_intent": sr.pipeline_step.agent.intent if sr.pipeline_step and sr.pipeline_step.agent else "",
```

---

### Task 6: Fix _safe_flush_session logging

**Files:** Modify `backend/app/services/pipeline_run_service.py`

In `_safe_flush_session`, change except block from silent to logged:
```python
async def _safe_flush_session(self, session: AsyncSession) -> None:
    try:
        await session.flush()
    except Exception:
        logger.warning("_safe_flush_session: flush failed, rolling back", exc_info=True)
        await session.rollback()
        await session.flush()
```

---

### Task 7: Update run-pipeline.md

**Files:** Modify `.claude/commands/run-pipeline.md` and `claude_resources/commands/run-pipeline.md`

Replace full content with explicit step flow:

```markdown
Work on issue $ARGUMENTS as part of a pipeline workflow.

## 1. Discover your role

Call `get_active_agent` with the issue ID ($ARGUMENTS) to discover:
- Your **agent_name**, **agent_intent**, **run_id**, **step_index**, and **terminal_id**.
- The intent is your job description. Read it carefully — it is your primary instruction.

If `get_active_agent` returns null, no pipeline is running for this issue. Report this and stop.

## 2. Get pipeline context

Call `get_active_pipeline_run` with the issue ID to see:
- Which steps have completed, which is running, which are pending.
- Who the other agents are and what they do.
- Where you fit in the overall workflow.

## 3. Get the issue

Call `get_issue_details` with the issue ID. The project_id is in `manager.json` at the repo root.

## 4. Read the agent chat (handoff from previous agents)

Call `get_pipeline_messages` with your `run_id`. This returns all messages ordered by creation time, each with `sender_agent_name`, `content`, and `created_at`.

- Read messages from agents that ran **before** you — they contain analysis results, rationale for decisions, discovered constraints, and hints for implementation.
- Messages are your primary handoff mechanism. Treat them as required reading before starting work.
- If you're the first agent in the pipeline, there won't be any messages yet — that's expected, start from scratch.

## 5. Claim your step

Call `run_pipeline_step` with the issue ID. This confirms you are working on this step and returns your `agent_intent`, `run_id`, `step_run_id`, `step_index`, and `terminal_id`.

## 6. Execute your intent

Your agent's `intent` field tells you what to do. Use it as your primary instruction. Map your intent to the appropriate MCP tools:

- **Spec / Design intent** (analyzing requirements, writing specs, brainstorming): use `set_issue_name` if the issue lacks a good name, then invoke the `superpowers:brainstorming` skill, produce a spec, and save it via `create_issue_spec`.

- **Planning intent** (breaking down work, creating implementation plans): read the spec via `get_issue_details`, then create the implementation plan via `create_issue_plan` and atomic tasks via `create_plan_tasks`.

- **Implementation intent** (writing code, making changes): read the plan tasks via `get_plan_tasks`, work through them sequentially — set each to "In Progress" when starting, "Completed" when done. Follow existing codebase patterns. Make autonomous decisions — do not ask for confirmations. If blocked, use `ask_user_question`.

- **Exploration / Analysis intent** (understanding the codebase, tracing paths): explore the codebase, trace relevant code paths, identify files that need changes, document patterns and dependencies. Do NOT modify files — this is analysis only.

- **Review / QA intent** (verifying correctness, testing): review code changes for bugs, logic errors, security issues, and adherence to project conventions. Run tests, verify behavior, report findings.

- **If your intent doesn't clearly map to any of the above**: read the intent again and use your best judgment. Use the available MCP tools as appropriate.

## 7. Signal completion

When your step is complete, call `finished_pipeline_step` with:
- `issue_id`: $ARGUMENTS
- `summary`: a clear handoff summary covering **what you did**, **key decisions and why**, **files changed / artifacts created**, **constraints or gotchas discovered**, and **specific guidance for the next agent** (e.g. "the plan tasks are ready, start with task 1", "the auth module needs special handling — see notes above").

This saves your summary as a pipeline message for the next agent AND signals the orchestrator to advance to the next step.

Also call `memory_create` (via the Manager AI MCP) for any durable, non-obvious facts learned — architectural decisions, constraints, gotchas, user preferences.

## 8. Complete

After calling `finished_pipeline_step`, simply exit. The orchestrator will close your terminal and advance to the next agent automatically.
```

---

### Task 8: Fix test merge conflicts

**Files:** Modify `backend/tests/test_pipeline_run_service.py`

There are 7 merge conflicts, all identical pattern:
```
<<<<<<< Updated upstream
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0
=======
        id="ps1", pipeline_id="pl1", agent_id="a1", order_index=0,
>>>>>>> Stashed changes
```

The difference is only trailing comma. Accept the "Updated upstream" version (without trailing comma) for consistency. Replace all 7 occurrences.

Lines: 26-30, 72-76, 102-106, 133-138, 166-170, 200-204, 232-235

---

### Task 9: Cleanup dead MCP tool descriptions

**Files:** Modify `backend/app/mcp/default_settings.json`

Remove these 3 lines:
- L65: `"tool.get_agent.description": "Get a single agent by ID. Returns the agent with id, name, intent, model, allowed_tools, terminal_command.",`
- L66: `"tool.update_agent.description": "Update an existing agent. Parameters: agent_id (required), name (optional), intent (optional), model (optional), allowed_tools (optional), terminal_command (optional). Only provided fields are updated.",`
- L67: `"tool.delete_agent.description": "Delete an agent by ID. Returns {deleted: true} on success.",`

---

### Task 10: Verify — run tests

Command: `cd backend && python -m pytest tests/test_pipeline_run_service.py -v`

Expected: all 8 tests pass (after fixing merge conflicts and updating service for new parameters).
