## Summary
Added a visible "Start Conversation" button to the Agents tab header, replacing the hidden per-agent Play icon button. Users can now click a clearly labeled button to open a terminal running `/manage-agent` for interactive agent management.

## Changes Made
- **Removed**: Per-agent Play button (hidden 32x32 icon, no label)
- **Added**: General "Start Conversation" button in header with MessageSquare icon, next to Seed Defaults and Create Agent
- **Added**: TerminalPanel component rendered below agent table when conversation is active
- **Added**: "End Conversation" button to close the terminal
- **Added**: Reattach-on-mount logic to reconnect to existing manage-agent terminals
- **Removed**: Unused imports (Play icon, useNavigate, the duplicate useCreateManageAgentTerminal hook)

## Files Modified
- `frontend/src/features/agents/components/AgentsTab.tsx` — +35/-30 lines, zero TypeScript errors