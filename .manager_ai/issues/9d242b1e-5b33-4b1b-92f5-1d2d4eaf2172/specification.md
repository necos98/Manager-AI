# Rename run_pipeline_step to get_step_context

## Problem
`run_pipeline_step` is misleading: it doesn't execute/start any step. The step is already RUNNING before the agent starts (set by orchestrator in `_execute()`). The tool is a **pure read** — fetches current step context: `{run_id, step_run_id, agent_name, agent_intent, step_index, terminal_id}`.

Name suggests side-effect (running a step), reality is data access (reading step context).

## Solution
Rename `run_pipeline_step` → `get_step_context` across all layers.

### Files to change

| File | Change |
|------|--------|
| `backend/app/mcp/server.py:1162-1182` | Rename function `run_pipeline_step` → `get_step_context`; update decorator `_desc` key |
| `backend/app/mcp/default_settings.json:73` | Rename key `tool.run_pipeline_step.description` → `tool.get_step_context.description`; update description text: "Claim the current pipeline step..." → "Get the current pipeline step context. Returns agent identity, intent, and step context for the running pipeline step. Pure read — no side effects." |
| `claude_resources/commands/run-pipeline.md:30-32` | Update step 5 title and body: `run_pipeline_step` → `get_step_context` |
| `.claude/commands/run-pipeline.md:30-32` | Sync copy of claude_resources (auto-generated) |

### Description update
**Old:** "Claim the current pipeline step for an issue. Call this when you start working as a pipeline agent. Returns your agent identity, intent, and step context."

**New:** "Get the current pipeline step context for an issue. Returns the agent identity, intent, run_id, step_run_id, step_index, and terminal_id for the active step. Pure read — no side effects. Parameters: issue_id (required). Returns: {run_id, step_run_id, agent_name, agent_intent, step_index, terminal_id}. Returns {active: null} if no pipeline is running for this issue."

### Not in scope
- Renaming other tools (`get_active_agent`, `finished_pipeline_step`)
- Changing behavior — only the name and description change
- Updating memories that reference old name (memories are historical records, not code)