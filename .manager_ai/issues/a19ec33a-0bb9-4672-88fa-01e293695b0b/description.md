MCP server tools that agents call during pipeline execution.

**New MCP tools to register in `app/mcp/server.py` + update `default_settings.json`:**

1. **send_pipeline_message**
   - Parameters: `pipeline_run_id` (string), `content` (string, markdown)
   - Creates a `pipeline_message` record in DB
   - Emits WebSocket event `pipeline_message_sent` with the message data
   - Returns: `{ id, pipeline_run_id, sender_agent_name, content, created_at }`

2. **get_pipeline_messages**
   - Parameters: `pipeline_run_id` (string), `limit` (int, optional, default 50)
   - Returns all messages for the pipeline run, ordered chronologically
   - Returns: `[{ id, sender_agent_name, content, created_at }, ...]`

3. **complete_pipeline_step**
   - Parameters: `pipeline_step_run_id` (string)
   - Marks the current step as COMPLETED
   - Returns: `{ pipeline_step_run_id, status, next_step_name }`
   - Only works if the step is currently RUNNING
   - The backend orchestrator (Issue #4) listens for this and spawns the next terminal

**Important:**
- All descriptions must be added to `app/mcp/default_settings.json` with key pattern "tool.{function_name}.description"
- Follow existing MCP tool patterns in server.py