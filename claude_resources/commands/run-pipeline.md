Work on issue $ARGUMENTS as part of a pipeline workflow.

## 1. Discover your identity

You ARE the active agent in this pipeline. `get_active_agent` tells you who you are.

Call `get_active_agent` with the issue ID ($ARGUMENTS). The response identifies YOU:
- **agent_name** — your name (e.g. "SpecWriter", "Developer")
- **agent_intent** — YOUR primary instruction. This is the most important field. Read it carefully and follow it.
- **run_id**, **step_run_id**, **step_index**, **terminal_id** — your execution context

`get_active_agent` is the ONLY source of your identity. There are no env vars, no secondary channels. Call it once, internalize the result, and act on it.

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

## 5. Execute your intent

Your agent's `intent` field tells you what to do. Use it as your primary instruction. Map your intent to the appropriate MCP tools:

- **Spec / Design intent** (analyzing requirements, writing specs, brainstorming): use `set_issue_name` if the issue lacks a good name, then invoke the `superpowers:brainstorming` skill, produce a spec, and save it via `create_issue_spec`.

- **Planning intent** (breaking down work, creating implementation plans): read the spec via `get_issue_details`, then create the implementation plan via `create_issue_plan` and atomic tasks via `create_plan_tasks`.

- **Implementation intent** (writing code, making changes): read the plan tasks via `get_plan_tasks`, work through them sequentially — set each to "In Progress" when starting, "Completed" when done. Follow existing codebase patterns. Make autonomous decisions — do not ask for confirmations. If blocked, use `ask_user_question`.

- **Exploration / Analysis intent** (understanding the codebase, tracing paths): explore the codebase, trace relevant code paths, identify files that need changes, document patterns and dependencies. Do NOT modify files — this is analysis only.

- **Review / QA intent** (verifying correctness, testing): review code changes for bugs, logic errors, security issues, and adherence to project conventions. Run tests, verify behavior, report findings.

- **If your intent doesn't clearly map to any of the above**: read the intent again and use your best judgment. Use the available MCP tools as appropriate.

## 6. Signal completion

When your step is complete, call `finished_pipeline_step` with:
- `issue_id`: $ARGUMENTS
- `summary`: a clear handoff summary covering **what you did**, **key decisions and why**, **files changed / artifacts created**, **constraints or gotchas discovered**, and **specific guidance for the next agent** (e.g. "the plan tasks are ready, start with task 1", "the auth module needs special handling — see notes above").

This saves your summary as a pipeline message for the next agent AND signals the orchestrator to advance to the next step.

Also call `memory_create` (via the Manager AI MCP) for any durable, non-obvious facts learned — architectural decisions, constraints, gotchas, user preferences.

## 7. Complete

After calling `finished_pipeline_step`, simply exit. The orchestrator will close your terminal and advance to the next agent automatically.
