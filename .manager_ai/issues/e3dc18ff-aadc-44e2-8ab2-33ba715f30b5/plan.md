# Rimozione env vars identita agente: single source of truth via get_active_agent

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all agent identity env vars from pipeline PTY injection. Single identity source becomes `get_active_agent(issue_id)` MCP tool only.

**Architecture:** `_run_step()` in `pipeline_run_service.py` currently injects 4 env vars into PTY before launching the agent command. We remove all 4, leaving only `claude --dangerously-skip-permissions "/run-pipeline {issue_id}"` + `exit`. The `/run-pipeline.md` command already tells agents to call `get_active_agent` — we rewrite step 1 in first-person to make it unmistakable.

**Tech Stack:** Python (FastAPI backend), Markdown (command files), JSON (MCP settings)

---

### Task 1: Remove agent identity env vars from _run_step

**Files:**
- Modify: `backend/app/services/pipeline_run_service.py:286-301`

- [ ] **Step 1: Remove the 8 env var injection lines in _run_step**

In `_run_step()`, replace lines 288-301 (the env var injection block) so the method only writes the command + exit:

```python
        if is_windows:
            pty.write(f"{command}\r\n")
            pty.write("exit\r\n")
        else:
            pty.write(f"{command}; exit\r\n")
```

The full `_run_step` method becomes (showing only the changed section after `command = ...`):

```python
        is_windows = _platform.system() == "Windows"
        command = f'claude --dangerously-skip-permissions "/run-pipeline {issue_id}"'

        if is_windows:
            pty.write(f"{command}\r\n")
            pty.write("exit\r\n")
        else:
            pty.write(f"{command}; exit\r\n")
```

- [ ] **Step 2: Verify no syntax errors**

Run: `python -c "import ast; ast.parse(open('backend/app/services/pipeline_run_service.py').read()); print('OK')"`

Expected: OK

- [ ] **Step 3: Run existing pipeline tests**

Run: `cd backend && python -m pytest tests/test_pipeline_run_service.py -v`

Expected: All tests pass (tests mock _run_step or don't assert on env vars)

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/pipeline_run_service.py
git commit -m "fix: remove agent identity env vars from pipeline _run_step

get_active_agent MCP tool is now the single source of truth for agent
identity. Removed MANAGER_AI_AGENT_NAME, MANAGER_AI_AGENT_ROLE,
MANAGER_AI_AGENT_INTENT, and MANAGER_AI_ISSUE_ID from PTY injection."
```

---

### Task 2: Rewrite /run-pipeline.md step 1 in first person

**Files:**
- Modify: `claude_resources/commands/run-pipeline.md:3-9`

- [ ] **Step 1: Rewrite step 1 of run-pipeline.md**

Replace lines 3-9:

```markdown
## 1. Discover your role

Call `get_active_agent` with the issue ID ($ARGUMENTS) to discover:
- Your **agent_name**, **agent_intent**, **run_id**, **step_run_id**, **step_index**, and **terminal_id**.
- The intent is your job description. Read it carefully — it is your primary instruction.

If `get_active_agent` returns null, no pipeline is running for this issue. Report this and stop.
```

With:

```markdown
## 1. Discover your identity

You ARE the active agent in this pipeline. `get_active_agent` tells you who you are.

Call `get_active_agent` with the issue ID ($ARGUMENTS). The response identifies YOU:
- **agent_name** — your name (e.g. "SpecWriter", "Developer")
- **agent_intent** — YOUR primary instruction. This is the most important field. Read it carefully and follow it.
- **run_id**, **step_run_id**, **step_index**, **terminal_id** — your execution context

`get_active_agent` is the ONLY source of your identity. There are no env vars, no secondary channels. Call it once, internalize the result, and act on it.

If `get_active_agent` returns null, no pipeline is running for this issue. Report this and stop.
```

- [ ] **Step 2: Commit**

```bash
git add claude_resources/commands/run-pipeline.md
git commit -m "fix: rewrite run-pipeline step 1 as first-person identity discovery

Clarifies that get_active_agent returns the agent's OWN identity, not an
external entity. Removes any ambiguity about identity sources."
```

---

### Task 3: Update get_active_agent tool description in default_settings.json

**Files:**
- Modify: `backend/app/mcp/default_settings.json:72`

- [ ] **Step 1: Update get_active_agent description**

Replace line 72:

```json
"tool.get_active_agent.description": "Get the currently active agent step in a running pipeline for an issue. Parameters: issue_id (required). Returns: run_id, step_run_id, agent_name, agent_intent, step_index, step_status, terminal_id. Returns null if no pipeline is running or no step is active. Use this to understand which role/agent you are currently acting as.",
```

With:

```json
"tool.get_active_agent.description": "Returns YOUR identity as the active pipeline agent. You ARE this agent — the returned agent_name and agent_intent describe YOU and what you must do. Parameters: issue_id (required). Returns: run_id, step_run_id, agent_name, agent_intent, step_index, step_status, terminal_id. Returns {active: null} if no pipeline is running or no step is active. This is the ONLY source of agent identity — there are no env vars.",
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/mcp/default_settings.json
git commit -m "fix: emphasize get_active_agent as self-discovery tool

Reworded description to use second-person ('YOU ARE this agent') so
agents understand the tool returns their own identity."
```

---

### Task 4: Remove terminal_command references from default_settings.json

**Files:**
- Modify: `backend/app/mcp/default_settings.json:63-66`

- [ ] **Step 1: Remove terminal_command from tool descriptions**

Update lines 63-66, removing `terminal_command` references:

Line 63 — `create_agent`:
```json
"tool.create_agent.description": "Create a new agent. Parameters: name (required), intent (optional string describing what the agent does), model (optional), allowed_tools (optional list of strings). Returns the created agent with id, name, intent, model, allowed_tools.",
```

Line 64 — `list_agents`:
```json
"tool.list_agents.description": "List all agents. Returns a list of agents with id, name, intent, model, allowed_tools.",
```

Line 65 — `create_pipeline`:
```json
"tool.create_pipeline.description": "Create a new pipeline with steps for a project. Parameters: project_id (required), name (required), steps (required list of {agent_id, order_index}). Returns the created pipeline with id, name, and steps.",
```

Line 66 — `list_pipelines`:
```json
"tool.list_pipelines.description": "List all pipelines for a project. Parameters: project_id (required). Returns a list of pipelines with id, name, and steps (each with agent_id, order_index).",
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/mcp/default_settings.json
git commit -m "fix: remove terminal_command from MCP tool descriptions

terminal_command column was already dropped and is unused by pipeline
execution. Tool descriptions now match actual parameter schemas."
```

---

### Task 5: Update related memories

- [ ] **Step 1: Update memory fc31b9e8 (pipeline agent env vars)**

Call `memory_update` to reflect that agent identity env vars are removed:
- Title: "Pipeline agent environment variables passed to subprocess (REMOVED)"
- Description: note that MANAGER_AI_AGENT_NAME, MANAGER_AI_AGENT_ROLE, MANAGER_AI_AGENT_INTENT, MANAGER_AI_ISSUE_ID are no longer injected. get_active_agent is the only identity channel.

- [ ] **Step 2: Update memory ee88c5a3 (agent intent flow)**

Call `memory_update` to remove the "Env var" channel mention — intent now flows ONLY through get_active_agent MCP tool.

- [ ] **Step 3: Update memory eb307327 (get_active_agent bridges env vars to MCP)**

Call `memory_update` to remove "bridges env-var identity" framing — it's now the sole source, not a bridge.
