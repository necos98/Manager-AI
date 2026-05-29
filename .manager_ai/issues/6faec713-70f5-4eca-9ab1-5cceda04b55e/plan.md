## Files to change

1. **`backend/app/mcp/server.py:1105-1125,1162-1182`** — Add `step_run_id` to `get_active_agent` return dict. Delete `get_step_context` function entirely.
2. **`backend/app/mcp/default_settings.json:72-73`** — Update `tool.get_active_agent.description` to include `step_run_id` in documented fields. Delete `tool.get_step_context.description`.
3. **`claude_resources/commands/run-pipeline.md:5,30-32`** — Update step 1 to mention `step_run_id`. Remove step 5 "Claim your step" (calls deleted tool). Renumber 6→5, 7→6, 8→7.

## Implementation notes

- `get_active_agent` and `get_step_context` both already fetch step data from `steps[idx]` — `step_run_id` is `step["id"]`. No new DB queries needed.
- Memory rule: only edit `claude_resources/`, not `.claude/` mirror.
- No behavior change for `get_active_agent` consumers — purely additive field.
- Delete `get_step_context` with no backward compat shim — no other consumers exist (confirmed via grep).