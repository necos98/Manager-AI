# Consolidate `get_active_agent` and `get_step_context`

## Problem

`get_active_agent` and `get_step_context` return nearly identical data:

| Field | `get_active_agent` | `get_step_context` |
|-------|--------------------|--------------------|
| run_id | yes | yes |
| agent_name | yes | yes |
| agent_intent | yes | yes |
| step_index | yes | yes |
| terminal_id | yes | yes |
| step_status | yes | no |
| step_run_id | no | yes |

Only one field differs each way. `run-pipeline.md` reads `agent_intent` twice — step 1 from `get_active_agent`, step 5 from `get_step_context` — creating ambiguity about the canonical source.

## Solution

**Merge `get_step_context` into `get_active_agent`.** `get_active_agent` gains `step_run_id` and becomes the single source of truth for agent context. `get_step_context` is deleted.

### Files to change

1. **`backend/app/mcp/server.py`:**
   - Add `step_run_id` to `get_active_agent` return dict
   - Delete `get_step_context` function entirely

2. **`backend/app/mcp/default_settings.json`:**
   - Update `tool.get_active_agent.description` — document `step_run_id` in return fields
   - Delete `tool.get_step_context.description`

3. **`claude_resources/commands/run-pipeline.md`:**
   - Step 1: note `get_active_agent` now returns `step_run_id`
   - Step 5 "Claim your step": remove (calls deleted `get_step_context`)
   - Renumber remaining steps: 6→5, 7→6, 8→7

### New `get_active_agent` return signature

```json
{
  "run_id": "...",
  "step_run_id": "...",
  "agent_name": "...",
  "agent_intent": "...",
  "step_index": 0,
  "step_status": "running",
  "terminal_id": "..."
}
```

### Acceptance criteria
- `get_step_context` removed from MCP server
- `get_active_agent` returns `step_run_id`
- `run-pipeline.md` calls `get_active_agent` once, not twice
- `default_settings.json` descriptions updated
- No references to `get_step_context` remain in codebase