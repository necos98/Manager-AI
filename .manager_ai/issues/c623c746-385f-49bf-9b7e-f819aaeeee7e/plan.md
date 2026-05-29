## Implementation Plan

### Files to modify

| File | Change |
|------|--------|
| `backend/app/services/agent_service.py` | Fix `create()` to accept and save `intent` |
| `backend/app/mcp/server.py` | Add `get_agent`, `update_agent`, `delete_agent` MCP tools; fix `create_agent` to accept `system_prompt` (maps to `intent`) |
| `backend/app/mcp/default_settings.json` | Restore descriptions for `get_agent`, `update_agent`, `delete_agent`; fix `create_agent` description |
| `backend/app/schemas/terminal.py` | Add `agent_id` field to `ManageAgentTerminalCreate` |
| `backend/app/routers/terminals.py` | Update `create_manage_agent_terminal` to inject agent-specific env vars when `agent_id` provided |
| `frontend/src/features/agents/components/AgentsTab.tsx` | Add "Start" (Play icon) button per agent row |
| `frontend/src/shared/types/index.ts` | Add `agent_id` to `ManageAgentTerminalCreate` type |

### Task 1: Fix AgentService.create() + create_agent MCP tool

**Files:** `backend/app/services/agent_service.py`, `backend/app/mcp/server.py`

- [ ] Add `intent` parameter to `AgentService.create(name, model, allowed_tools, intent="")`
- [ ] Save `intent` on the Agent model in `create()`
- [ ] Update `create_agent` MCP tool: rename/add `system_prompt` parameter, pass as `intent` to service
- [ ] Return `intent` in `create_agent` response
- [ ] Update `list_agents` response to include `intent`
- [ ] Update `default_settings.json`: fix `create_agent` description to list `system_prompt` parameter

### Task 2: Add get_agent, update_agent, delete_agent MCP tools

**Files:** `backend/app/mcp/server.py`, `backend/app/mcp/default_settings.json`

- [ ] Add `get_agent(agent_id)` tool — returns full agent detail including `intent`
- [ ] Add `update_agent(agent_id, name?, system_prompt?, model?, allowed_tools?)` — updates only provided fields. `system_prompt` maps to `intent` on model
- [ ] Add `delete_agent(agent_id)` tool — deletes agent, returns `{deleted: true}`
- [ ] Add descriptions for all 3 tools in `default_settings.json`

### Task 3: Enhance manage-agent terminal endpoint for per-agent start

**Files:** `backend/app/schemas/terminal.py`, `backend/app/routers/terminals.py`

- [ ] Add `agent_id: str | None = None` to `ManageAgentTerminalCreate`
- [ ] In `create_manage_agent_terminal`: if `agent_id` provided, fetch agent from DB
- [ ] Inject `MANAGER_AI_AGENT_ID` and `MANAGER_AI_AGENT_INTENT` env vars into terminal
- [ ] Append agent intent as inline instruction to the terminal command so claude sees it on startup

### Task 4: Add "Start" button to AgentsTab UI

**Files:** `frontend/src/features/agents/components/AgentsTab.tsx`, `frontend/src/shared/types/index.ts`

- [ ] Add `Play` icon import from lucide-react
- [ ] Add "Start" button in each agent row (next to Edit/Delete)
- [ ] On click: call `useCreateManageAgentTerminal` with `{ agent_id: agent.id }`
- [ ] On success: navigate to terminal view / open TerminalPanel with the returned terminal_id
- [ ] Add `agent_id?: string` to `ManageAgentTerminalCreate` type in shared types
- [ ] Add loading state while terminal is being created
