## Changes made

### Backend — MCP tools restored
- **`agent_service.py`**: `create()` now accepts and saves `intent` parameter
- **`server.py`**: Added `get_agent`, `update_agent`, `delete_agent` MCP tools; fixed `create_agent` to accept `intent` param; `list_agents` now returns `intent` in response
- **`default_settings.json`**: Added descriptions for `get_agent`, `update_agent`, `delete_agent`; fixed `create_agent` and `list_agents` descriptions to reference `intent`
- **`schemas/agent.py`**: `AgentCreate` and `AgentUpdate` now include `intent` field; `AgentResponse` includes `intent`
- **`routers/agents.py`**: REST endpoints now pass `intent` through to service and include it in responses

### Backend — Agent terminal start
- **`schemas/terminal.py`**: `ManageAgentTerminalCreate` now has optional `agent_id` field
- **`routers/terminals.py`**: `create_manage_agent_terminal` fetches agent when `agent_id` provided, injects `MANAGER_AI_AGENT_ID` and `MANAGER_AI_AGENT_INTENT` env vars, appends agent intent to startup command

### Frontend — Agents page
- **`AgentsTab.tsx`**: Added `intent` field to create/edit form (Textarea); added Play button on each agent row to start a terminal with that agent; on click calls `useCreateManageAgentTerminal` mutation then navigates to `/terminals`
- **`types/index.ts`**: `ManageAgentTerminalCreate` now has `agent_id?: string`

### Result
- `/manage-agent` command now works: `get_agent`, `update_agent`, `delete_agent` MCP tools available
- `create_agent` accepts `intent` parameter
- Agents page has Start button (Play icon) per agent row → opens terminal with agent context
- All 19 agent/MCP/pipeline tests pass