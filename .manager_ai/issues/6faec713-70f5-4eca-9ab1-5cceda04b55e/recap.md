## Summary

Consolidated `get_step_context` into `get_active_agent` — single source of truth for agent context.

## Changes

1. **`backend/app/mcp/server.py`**: Added `step_run_id` to `get_active_agent` return dict. Deleted `get_step_context` function.
2. **`backend/app/mcp/default_settings.json`**: Updated `tool.get_active_agent.description` to include `step_run_id`. Deleted `tool.get_step_context.description`.
3. **`claude_resources/commands/run-pipeline.md`**: Updated step 1 to mention `step_run_id`. Removed step 5 "Claim your step". Renumbered 6→5, 7→6, 8→7.

## Result
- One tool where there were two
- `agent_intent` no longer read twice
- Zero remaining references to `get_step_context` in backend or claude_resources