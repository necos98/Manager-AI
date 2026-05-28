Work on issue $ARGUMENTS as part of a pipeline workflow.

## 1. Discover your role

Call `get_active_agent` with the issue ID ($ARGUMENTS) to discover:
- Your **agent name** and **intent** — the intent is your job description. Read it carefully and follow it.
- The **run_id**, **step_index**, and **terminal_id** for context.

If `get_active_agent` returns null, no pipeline is running for this issue. Report this and stop.

## 2. Get pipeline context

Call `get_active_pipeline_run` with the issue ID to see:
- Which steps have completed, which is running, which are pending.
- Who the other agents are and what they do.
- Where you fit in the overall workflow.

## 3. Get the issue

Call `get_issue_details` with the issue ID. The project_id is in `manager.json` at the repo root.

## 4. Read the agent chat (handoff from previous agents)

The pipeline has a **shared message log** that agents use to hand off context. Each agent writes a summary of what it did, decisions made, and guidance for downstream agents.

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

- **If your intent doesn't clearly map to any of the above**: read the intent again and use your best judgment. Use the available MCP tools (`create_issue_spec`, `create_issue_plan`, `create_plan_tasks`, `update_task_status`, `send_agent_message`) as appropriate.

## 6. Hand off to the next agent

When your step is complete, call `send_agent_message` with:
- `run_id`: your pipeline run ID
- `sender_agent_name`: your agent name
- `content`: a clear summary covering **what you did**, **key decisions and why**, **files changed / artifacts created**, **constraints or gotchas discovered**, and **specific guidance for the next agent** (e.g. "the plan tasks are ready, start with task 1", "the auth module needs special handling — see notes above").

This message becomes part of the shared pipeline log. The next agent will read it in step 4. Write it for them — be specific and actionable.

Also call `memory_create` (via the Manager AI MCP) for any durable, non-obvious facts learned — architectural decisions, constraints, gotchas, user preferences.

## 7. Complete

When done, simply exit. The pipeline engine will advance to the next agent automatically.
