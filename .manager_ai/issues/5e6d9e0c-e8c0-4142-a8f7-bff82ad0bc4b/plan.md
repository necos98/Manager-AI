# Pipeline configurable command — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded `claude -p` in `_run_step()` with the step's `terminal_command` executed as a shell command, matching "Run Issue" variable substitution logic.

**Architecture:** `_run_step()` receives the already-substituted `terminal_command` from `_execute()`. Instead of wrapping it in a `claude -p` prompt, it executes it directly via `asyncio.create_subprocess_shell`. stdout+stderr are merged and streamed to a log terminal via `push_output()`. Agent system_prompt and issue context are passed as environment variables. `_safe_flush_session` gains error logging.

**Tech Stack:** Python asyncio, pywinpty (unchanged), log terminals (unchanged)

---

### Task 1: Fix `_safe_flush_session` silent error swallowing

**Files:**
- Modify: `backend/app/services/pipeline_run_service.py:252-257`

- [ ] **Step 1: Add warning log in except block**

```python
async def _safe_flush_session(self, session: AsyncSession) -> None:
    try:
        await session.flush()
    except Exception:
        logger.warning("_safe_flush_session: flush failed, rolling back", exc_info=True)
        await session.rollback()
        await session.flush()
```

- [ ] **Step 2: Verify import**

`logger` is already imported at line 23: `logger = logging.getLogger(__name__)`. No import change needed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/pipeline_run_service.py
git commit -m "fix: log warnings in _safe_flush_session instead of swallowing errors silently"
```

---

### Task 2: Update DEFAULT_AGENTS terminal_command to be executable

**Files:**
- Modify: `backend/app/services/agent_service.py:7-73`

- [ ] **Step 1: Change terminal_command values to executable shell commands**

Replace the task-description strings with proper `claude -p` commands that include the task. The `$issue_id` and `$project_id` variables are substituted in `_execute()`.

```python
DEFAULT_AGENTS = [
    {
        "name": "CodebaseExplorer",
        "system_prompt": (
            "Explore and analyze codebase structure, find patterns and conventions, "
            "trace execution paths, and document dependencies."
        ),
        "terminal_command": (
            'claude -p "Explore the codebase to understand the context of issue $issue_id '
            'in project $project_id. Report your findings."'
        ),
    },
    {
        "name": "BrainstormingAgent",
        "system_prompt": (
            "Brainstorm ideas and refine requirements through natural collaborative dialogue. "
            "Turn ideas into fully formed designs and specs."
        ),
        "terminal_command": (
            'claude -p "Brainstorm and refine requirements for issue $issue_id. '
            'Produce a clear design and specification."'
        ),
    },
    {
        "name": "SpecWriter",
        "system_prompt": (
            "Write detailed specifications from requirements. Produce clear, structured "
            "specs covering architecture, components, data flow, error handling, and testing."
        ),
        "terminal_command": (
            'claude -p "Write a detailed specification for issue $issue_id. '
            'Cover architecture, components, data flow, error handling, and testing."'
        ),
    },
    {
        "name": "PlanWriter",
        "system_prompt": (
            "Create implementation plans from specifications. Break down designs into "
            "atomic, ordered tasks with specific files to create or modify."
        ),
        "terminal_command": (
            'claude -p "Create an implementation plan for issue $issue_id. '
            'Break it down into atomic, ordered tasks with specific files to modify."'
        ),
    },
    {
        "name": "Developer",
        "system_prompt": (
            "Implement code following plans and specifications. Write production-quality "
            "code that follows existing patterns and conventions."
        ),
        "terminal_command": (
            'claude -p "Implement the code changes described in the plan for issue $issue_id. '
            'Follow existing codebase patterns and conventions."'
        ),
    },
    {
        "name": "Reviewer",
        "system_prompt": (
            "Review code for bugs, logic errors, security vulnerabilities, code quality "
            "issues, and adherence to project conventions."
        ),
        "terminal_command": (
            'claude -p "Review the code changes made for issue $issue_id. '
            'Check for bugs, logic errors, security vulnerabilities, and code quality issues."'
        ),
    },
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/agent_service.py
git commit -m "fix: make DEFAULT_AGENTS terminal_command executable shell commands"
```

---

### Task 3: Rewrite `_run_step()` to execute terminal_command directly

**Files:**
- Modify: `backend/app/services/pipeline_run_service.py:259-338`

- [ ] **Step 1: Replace `_run_step()` — remove prompt building, execute command via shell, merge stderr**

Replace the entire `_run_step()` method (lines 259-338) with:

```python
async def _run_step(
    self,
    term_id: str,
    agent_name: str,
    system_prompt: str,
    command: str,
    project_path: str,
    run_id: str,
    issue_id: str,
) -> bool:
    env = os.environ.copy()
    env["MANAGER_AI_AGENT_NAME"] = agent_name
    env["MANAGER_AI_AGENT_ROLE"] = agent_name
    env["MANAGER_AI_SYSTEM_PROMPT"] = system_prompt
    env["MANAGER_AI_ISSUE_ID"] = issue_id
    env["MANAGER_AI_RUN_ID"] = run_id

    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=project_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )

    async def stream_output():
        if proc.stdout is None:
            return
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                await terminal_service.push_output(term_id, text)
        except asyncio.CancelledError:
            pass

    stream_task = asyncio.create_task(stream_output())

    try:
        exit_code = await asyncio.wait_for(
            proc.wait(), timeout=DEFAULT_STEP_TIMEOUT
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        stream_task.cancel()
        return False
    except asyncio.CancelledError:
        proc.kill()
        await proc.wait()
        stream_task.cancel()
        raise

    await stream_task
    return exit_code == 0
```

- [ ] **Step 2: Verify `os` import is present**

Line 3: `import os` — already imported. No change needed.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/pipeline_run_service.py
git commit -m "feat: execute terminal_command directly via shell instead of hardcoding claude -p"
```

---

### Task 4: Reseed pipeline steps with updated terminal_command

**Files:**
- No file changes — manual operation

- [ ] **Step 1: Delete existing default pipeline to trigger reseed**

The `seed_defaults()` in `PipelineService` is idempotent — it only creates defaults if no pipelines exist. After updating `DEFAULT_AGENTS.terminal_command` values, existing pipeline steps still have the old task-description strings.

**Manual fix:** Delete the default pipeline via the UI or API, then restart the backend. The startup seed will recreate the pipeline with the new executable `terminal_command` values.

Alternative: Update each pipeline step's `terminal_command` via the API/UI.

```bash
# Restart backend to trigger reseed (only if pipeline was deleted)
python start.py
```

- [ ] **Step 2: Verify pipeline steps show executable commands**

Check the Pipelines tab in the UI — each step's `terminal_command` field should show a `claude -p "..."` command, not a bare task description.

---

### Task 5: Verify fix end-to-end

- [ ] **Step 1: Start the backend and frontend**

```bash
python start.py
```

- [ ] **Step 2: Create a test issue or use existing one**

Navigate to an issue, click "Start Pipeline" with the Default Pipeline.

- [ ] **Step 3: Verify terminal shows output**

Check that:
- Terminal connects and shows shell output (not just "Connected to agent output stream...")
- `claude -p` output streams in real-time
- Step transitions from RUNNING to COMPLETED on success
- Errors (if any) are visible in the terminal (merged stderr)

- [ ] **Step 4: Verify with custom terminal_command**

Edit a pipeline step's `terminal_command` to a simple command like `echo "hello from pipeline"`. Start a new pipeline run and verify the custom command output appears in the terminal.

- [ ] **Step 5: Commit any final adjustments**

```bash
git add -A
git commit -m "chore: final adjustments after end-to-end verification"
```
