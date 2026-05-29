# Plan: Rename run_pipeline_step to get_step_context

Pure rename — no behavior change, no tests needed. Four files touched.

## Files

| File | Action |
|------|--------|
| `backend/app/mcp/server.py:1162-1182` | Rename function + `_desc` key |
| `backend/app/mcp/default_settings.json:73` | Rename key + description text |
| `claude_resources/commands/run-pipeline.md:30-32` | Update step 5 reference |
| `.claude/commands/run-pipeline.md:30-32` | Sync from claude_resources |

## Tasks

### Task 1: Rename function in server.py
- Rename `run_pipeline_step` → `get_step_context`
- Update `_desc` key from `tool.run_pipeline_step.description` → `tool.get_step_context.description`

### Task 2: Update default_settings.json
- Rename key `tool.run_pipeline_step.description` → `tool.get_step_context.description`
- Update description text: "Claim the current pipeline step for an issue..." → "Get the current pipeline step context for an issue. Returns agent identity, intent, run_id, step_run_id, step_index, and terminal_id for the active step. Pure read — no side effects. Parameters: issue_id (required). Returns: {run_id, step_run_id, agent_name, agent_intent, step_index, terminal_id}. Returns {active: null} if no pipeline is running for this issue."

### Task 3: Update run-pipeline.md references
- `claude_resources/commands/run-pipeline.md`: step 5 title "Claim your step" → keep title, change `run_pipeline_step` → `get_step_context` in body
- `.claude/commands/run-pipeline.md`: same sync change

### Task 4: Verify no remaining references
- Grep for `run_pipeline_step` in source files — should be 0 in server.py, default_settings.json, run-pipeline.md files
- Memories and issue files are historical records — not in scope