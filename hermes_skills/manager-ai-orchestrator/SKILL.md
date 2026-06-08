---
name: manager-ai-orchestrator
description: "Orchestrate Manager AI projects via MCP — create issues, manage pipelines, advance steps, write memories."
version: 1.0.0
author: Manager AI
platforms: [windows, linux, macos]
---

# Manager AI Orchestrator

You are connected to **Manager AI** via its MCP server (toolset `manager-ai`).
Your role is to act as the **orchestrator**: create issues, configure and run
pipelines, advance work, and manage project memory — all through MCP tool calls.

## Prerequisites

Manager AI must be running (`python start.py` from the Manager-AI repo) and
Hermes MCP must be connected:

```bash
hermes mcp add manager-ai --url http://localhost:8000/mcp
```

Verify with: `hermes mcp list` — the `manager-ai` server should appear with
all its tools listed.

## Key Concepts

### Issue Lifecycle

```
NEW ──[create_issue_spec]──> REASONING ──[create_issue_plan]──> PLANNED
  ──[accept_issue]──> ACCEPTED ──[implement + complete_issue]──> FINISHED
```

Cancel from any state with `cancel_issue`. Force-finish edge cases with
`force_finish_issue`.

### Pipeline System

A **pipeline** is a sequence of **agents** (steps). Each agent has a `name`,
`intent` (what it should do), and a `provider` (`"claude"` or `"hermes"`).
Pipelines run against an **issue** in a **project**.

### Orchestrated vs Auto Mode

| Mode | `orchestrated` | Who executes steps |
|------|---------------|-------------------|
| **Auto** (default) | `false` | Manager AI spawns Claude Code in a PTY subprocess for each step |
| **Orchestrated** | `true` | **You** (Hermes) control each step via MCP tools |

In **orchestrated mode**, the flow is:

```
run_pipeline(..., orchestrated=True)  → status: WAITING_FOR_STEP
                    │
start_pipeline_step(run_id, project_id)  → step RUNNING
    │
    ├── You do the work (MCP tools + filesystem)
    │
finished_pipeline_step(issue_id, summary="...")  → step COMPLETED
    │
advance_pipeline(run_id)  → next step or pipeline COMPLETED
    │
    └── Repeat until pipeline_finished=True
```

## Orchestration Workflow

### 1. Discover Project Context

Always start by understanding the project:

```python
# Find project_id
# Read manager.json from the project repo root
# Or call the project API if you know the project exists

# Get project details
get_project_context(project_id=...)

# Read project memories
memory_search(project_id=..., query="<keywords>")
memory_list(project_id=..., parent_id="")
```

### 2. Create an Issue

```python
# Create the issue
create_issue(project_id=..., description="...", priority=3)

# Write a specification (moves to REASONING)
create_issue_spec(project_id=..., issue_id=..., spec="...")

# Write a plan (moves to PLANNED)
create_issue_plan(project_id=..., issue_id=..., plan="...")

# Create atomic tasks
create_plan_tasks(issue_id=..., tasks=[{"name": "..."}, ...])

# Accept the plan (moves to ACCEPTED)
accept_issue(project_id=..., issue_id=...)
```

### 3. Run an Orchestrated Pipeline

```python
# Create agents first if they don't exist
create_agent(name="SpecWriter", provider="hermes",
    intent="Analyze the issue and write a specification")
create_agent(name="Developer", provider="hermes",
    intent="Implement the issue according to the plan")

# Create a pipeline with those agents
pipeline = create_pipeline(name="My Pipeline", steps=[
    {"agent_id": "<specwriter-id>", "order_index": 0},
    {"agent_id": "<developer-id>", "order_index": 1},
])

# Run in orchestrated mode
run = run_pipeline(project_id=..., pipeline_id=..., issue_id=...,
                   orchestrated=True)
# run.status = "WAITING_FOR_STEP"
```

### 4. Execute Steps

For each step of the pipeline:

```python
# 1. Start the step
step_info = start_pipeline_step(run_id=run["id"], project_id=...)
# Returns: {term_id, agent_name, agent_intent, step_index, step_run_id}

# 2. Read pipeline context
messages = get_pipeline_messages(run_id=run["id"])
active_run = get_active_pipeline_run(issue_id=...)
agent_info = get_active_agent(issue_id=...)

# 3. Follow the agent's intent
# The agent_name and agent_intent tell you what to do
# If you ARE the SpecWriter → read issue → write spec
# If you ARE the Developer → implement the code

# 4. Signal completion
finished_pipeline_step(issue_id=..., summary="<handoff text>")

# 5. Advance to next step
advance_pipeline(run_id=run["id"])
```

### 5. Manage Multiple Projects

Use project links to keep track of related projects:

```python
get_project_links(project_id=...)
```

### Memory Protocol

**ALWAYS write memories** after completing an issue:

```python
memory_create(project_id=..., title="...", description="...")
```

Search existing memories before creating duplicates:

```python
memory_search(project_id=..., query="<keywords>")
```

## Best Practices

1. **Read before acting** — always check issue state, project context, and
   memories before starting work
2. **Write memories** — every completed issue should produce at least one
   memory with key decisions and constraints
3. **Use `send_notification`** for milestones — lets the user track progress
4. **Use `ask_user_question`** only when genuinely blocked — otherwise make
   autonomous decisions
5. **Check pipeline status** with `get_active_pipeline_run` before advancing
6. **Handoff summaries matter** — write clear, actionable summaries in
   `finished_pipeline_step` so the next agent (or the human) knows what was done
