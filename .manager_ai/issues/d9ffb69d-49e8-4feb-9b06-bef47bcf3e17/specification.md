# Add visible "Start Conversation" button to Agents tab

## Problem
The Agents tab has a tiny Play icon button (32x32px, no text label) on each agent row that opens a terminal for `/manage-agent`. Users can't find it — it doesn't look like a "chat" or "conversation" button. The original design didn't include any conversation functionality; the Play button was added later as a compromise.

## User Request
- Remove the per-agent Play button entirely
- Add a general "Start Conversation" button at the top of the Agents tab (not per-agent)
- This button opens a terminal running `/manage-agent` (like Ask & Brainstorm does for `/ask-and-brainstorm`)
- The `/manage-agent` command handles agent CRUD interactively — no per-agent targeting needed

## Design

### AgentsTab.tsx Changes

**Remove:**
1. Play icon button from each agent row (the `handleStartAgent` function and its button)
2. `useNavigate` import (no longer needed)
3. `Play` icon import
4. `useCreateManageAgentTerminal` import from terminals hooks
5. Per-agent `startingAgentId` state

**Add:**
1. Import `TerminalPanel` component
2. Import `useCreateManageAgentTerminal`, `useManageAgentTerminals`, `useKillTerminal` hooks
3. General "Start Conversation" button in the header area (next to "Seed Defaults" and "Create Agent")
4. When clicked: creates a manage-agent terminal via `createManageAgentTerminal({})` (no agent_id)
5. Terminal state management: store terminalId, show TerminalPanel below the table when active
6. "End Conversation" button to close the terminal and return to table-only view

### Behavior
- **No terminal active**: Show agent table + "Start Conversation" button in header
- **Terminal active**: Show agent table + TerminalPanel below it, header button becomes "End Conversation"
- **Terminal ends**: Return to table-only view automatically (via TerminalPanel's `onSessionEnd` callback)

### Technical Details
- Reuses existing `POST /terminals/manage-agent` endpoint (already supports optional `agent_id`)
- Reuses `TerminalPanel` component with `projectId` prop
- Uses `useManageAgentTerminals()` to reattach to existing terminal on mount
- Follows same pattern as `AskPage` (`/projects/$projectId/ask.tsx`)
- No backend changes needed — all infrastructure exists