## What was done
Renamed MCP tool `run_pipeline_step` → `get_step_context` across all source files. Pure rename — no behavior change.

## Files changed
- `backend/app/mcp/server.py:1162-1163` — renamed function + `_desc` key to `tool.get_step_context.description`
- `backend/app/mcp/default_settings.json:73` — renamed key + new description: "Get the current pipeline step context for an issue. Returns agent identity, intent, run_id, step_run_id, step_index, and terminal_id for the active step. Pure read — no side effects."
- `claude_resources/commands/run-pipeline.md:32` — updated step 5 reference
- `.claude/commands/run-pipeline.md:32` — sync copy updated

## Key decision
Chose `get_step_context` over alternatives (`claim_pipeline_step`, `get_current_step`) because:
- `claim_pipeline_step` still implies side-effect (claiming), but the tool is pure read
- `get_step_context` honestly describes what it does: fetches step context
- The step is already RUNNING when the agent starts (set by orchestrator)

## Verification
Grep confirmed zero remaining `run_pipeline_step` references in backend/, claude_resources/, .claude/.