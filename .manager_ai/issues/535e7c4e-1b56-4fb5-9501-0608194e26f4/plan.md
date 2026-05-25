# Implementation Plan: Replace PTY with direct subprocess for agent step execution

## Summary

Refactor `OrchestratorService._run_agent_step()` to use log terminal + `ClaudeCodeExecutor.run_streaming()` instead of PTY terminal + temp file + marker polling.

## Files

- **Modify:** `backend/app/services/orchestrator_service.py` — `_run_agent_step()` method (lines 331-473) and imports (lines 1-25)

## Task 1: Refactor `_run_agent_step()`

### Step 1: Update imports

**Remove** unused imports:
- `import shlex` (line 8)
- `import tempfile` (line 9)
- `import uuid` (line 10)
- `from pathlib import Path` (line 12)
- `from app.services.wsl_support import is_wsl_shell, win_to_wsl_path` (line 24)

**Modify** line 25 — keep `_ensure_reader`, drop `_inject_env_vars`:
```python
from app.routers.terminals import _ensure_reader
```

**Add** new import:
```python
from app.hooks.executor import ClaudeCodeExecutor
```

### Step 2: Replace PTY creation with log terminal (lines 356-374)

**Remove:**
```python
project_shell = project.shell if project else None
project_wsl_distro = project.wsl_distro if project else None
is_wsl = is_wsl_shell(project_shell)

# Create real PTY terminal (like Run Issue / ask terminal)
term = terminal_service.create(
    issue_id=pipeline_run.issue_id or "",
    project_id=resolved_project_id,
    project_path=project_path,
    shell=project_shell,
    wsl_distro=project_wsl_distro,
)
_ensure_reader(term["id"], terminal_service)
step.terminal_id = term["id"]
await self._commit()

await self._emit("agent_terminal_created", pipeline_run, step, project_id=resolved_project_id)

pty = terminal_service.get_pty(term["id"])

# Set up project context (cd for WSL, like ask terminal)
if is_wsl:
    cwd_wsl = win_to_wsl_path(project_path)
    pty.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

# Inject env vars (like ask terminal)
try:
    env_vars = {
        "MANAGER_AI_TERMINAL_ID": term["id"],
        "MANAGER_AI_ISSUE_ID": pipeline_run.issue_id or "",
        "MANAGER_AI_PROJECT_ID": resolved_project_id,
        "MANAGER_AI_AGENT_NAME": agent.name,
        "MANAGER_AI_AGENT_ROLE": agent.role_key,
    }
    if is_wsl:
        _inject_env_vars(pty, env_vars, is_wsl=True)
        pty.write(
            f'export MANAGER_AI_BASE_URL='
            f'"http://localhost:{os.environ.get("BACKEND_PORT", "8000")}"\r\n'
        )
    else:
        env_vars["MANAGER_AI_BASE_URL"] = (
            f'http://localhost:{os.environ.get("BACKEND_PORT", "8000")}'
        )
        _inject_env_vars(pty, env_vars, is_wsl=False)
except Exception:
    logger.warning("Failed to inject env vars for pipeline terminal %s", term["id"], exc_info=True)
```

**Replace with:**
```python
term = await terminal_service.create_log(
    project_id=resolved_project_id,
    issue_id=pipeline_run.issue_id or "",
    project_path=project_path,
    label=f"Agent: {agent.name}",
)
_ensure_reader(term["id"], terminal_service)
step.terminal_id = term["id"]
await self._commit()

await self._emit("agent_terminal_created", pipeline_run, step, project_id=resolved_project_id)

env_vars = {
    "MANAGER_AI_TERMINAL_ID": term["id"],
    "MANAGER_AI_ISSUE_ID": pipeline_run.issue_id or "",
    "MANAGER_AI_PROJECT_ID": resolved_project_id,
    "MANAGER_AI_AGENT_NAME": agent.name,
    "MANAGER_AI_AGENT_ROLE": agent.role_key,
    "MANAGER_AI_BASE_URL": f'http://localhost:{os.environ.get("BACKEND_PORT", "8000")}',
}
```

### Step 3: Replace prompt execution and polling (lines 406-473)

**Remove** the entire block from `# Build prompt, write to temp file...` through the `finally` block (lines 406-453) and the completion check (lines 455-473).

**Replace with:**
```python
prompt = self._build_prompt(agent, issue, pipeline_run)

executor = ClaudeCodeExecutor()

async def on_output(text: str) -> None:
    await terminal_service.push_output(term["id"], text)

result = await executor.run_streaming(
    prompt=prompt,
    project_path=project_path,
    env_vars=env_vars,
    on_output=on_output,
)

await terminal_service.destroy_log(term["id"])

await self.session.refresh(step)

if step.status == AgentStepStatus.COMPLETED:
    await self._emit("agent_step_completed", pipeline_run, step, project_id=resolved_project_id)
    return True

step.completed_at = datetime.now(timezone.utc)
if result.success:
    step.status = AgentStepStatus.COMPLETED
    step.summary = f"Agent {agent.name} completed successfully."
    await self._commit()
    await self._emit("agent_step_completed", pipeline_run, step, project_id=resolved_project_id)
    return True
else:
    step.status = AgentStepStatus.FAILED
    step.error = result.error or "Claude process failed"
    await self._commit()
    await self._emit("agent_step_failed", pipeline_run, step, project_id=resolved_project_id)
    return False
```

### Step 4: Run existing tests

```bash
cd backend && python -m pytest tests/test_orchestrator.py -v
```

Verify all existing orchestrator tests still pass.

### Step 5: Manual verification

Start the app and run a pipeline to verify:
1. Log terminal appears in frontend with live agent output
2. Agent step completes successfully
3. WebSocket events fire correctly

## Complete new `_run_agent_step()` method

```python
async def _run_agent_step(
    self, pipeline_run: PipelineRun, step: AgentStepRun, *, project_id: str = ""
) -> bool:
    agent = await self.session.get(Agent, step.agent_id)
    if agent is None or not agent.enabled:
        step.status = AgentStepStatus.FAILED
        step.error = "Agent not found or disabled"
        await self._commit()
        return False

    resolved_project_id = project_id or agent.project_id

    project = await ProjectService(self.session).get_by_id(agent.project_id)
    issue = (
        await self.session.get(Issue, pipeline_run.issue_id)
        if pipeline_run.issue_id
        else None
    )

    step.status = AgentStepStatus.RUNNING
    step.started_at = datetime.now(timezone.utc)
    await self._commit()

    await self._emit("agent_step_started", pipeline_run, step, project_id=resolved_project_id)

    project_path = project.path if project else ""

    term = await terminal_service.create_log(
        project_id=resolved_project_id,
        issue_id=pipeline_run.issue_id or "",
        project_path=project_path,
        label=f"Agent: {agent.name}",
    )
    _ensure_reader(term["id"], terminal_service)
    step.terminal_id = term["id"]
    await self._commit()

    await self._emit("agent_terminal_created", pipeline_run, step, project_id=resolved_project_id)

    env_vars = {
        "MANAGER_AI_TERMINAL_ID": term["id"],
        "MANAGER_AI_ISSUE_ID": pipeline_run.issue_id or "",
        "MANAGER_AI_PROJECT_ID": resolved_project_id,
        "MANAGER_AI_AGENT_NAME": agent.name,
        "MANAGER_AI_AGENT_ROLE": agent.role_key,
        "MANAGER_AI_BASE_URL": f'http://localhost:{os.environ.get("BACKEND_PORT", "8000")}',
    }

    prompt = self._build_prompt(agent, issue, pipeline_run)

    executor = ClaudeCodeExecutor()

    async def on_output(text: str) -> None:
        await terminal_service.push_output(term["id"], text)

    result = await executor.run_streaming(
        prompt=prompt,
        project_path=project_path,
        env_vars=env_vars,
        on_output=on_output,
    )

    await terminal_service.destroy_log(term["id"])

    await self.session.refresh(step)

    if step.status == AgentStepStatus.COMPLETED:
        await self._emit("agent_step_completed", pipeline_run, step, project_id=resolved_project_id)
        return True

    step.completed_at = datetime.now(timezone.utc)
    if result.success:
        step.status = AgentStepStatus.COMPLETED
        step.summary = f"Agent {agent.name} completed successfully."
        await self._commit()
        await self._emit("agent_step_completed", pipeline_run, step, project_id=resolved_project_id)
        return True
    else:
        step.status = AgentStepStatus.FAILED
        step.error = result.error or "Claude process failed"
        await self._commit()
        await self._emit("agent_step_failed", pipeline_run, step, project_id=resolved_project_id)
        return False
```

## Risk assessment

- **Low risk.** Single method refactor. No API changes. No frontend changes. Log terminal pattern already proven in hook system.
- **Rollback:** Revert the commit — old code is entirely self-contained in `_run_agent_step()`.
