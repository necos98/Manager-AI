# Implementation Plan: Add visible "Start Conversation" button to Agents tab

## Files to modify
- `frontend/src/features/agents/components/AgentsTab.tsx` — the only file that needs changes

## Changes

### 1. Update imports
- **Remove**: `Play` from lucide-react import
- **Remove**: `useNavigate` from @tanstack/react-router
- **Add**: `MessageSquare` from lucide-react
- **Add**: `TerminalPanel` from @/features/terminals/components/terminal-panel
- **Add**: `useCreateManageAgentTerminal`, `useManageAgentTerminals`, `useKillTerminal` from @/features/terminals/hooks
- **Remove**: `import type { Agent, AgentCreate, AgentUpdate }` — keep Agent, AgentCreate, AgentUpdate types

### 2. Update component state
- **Remove**: `const navigate = useNavigate();`
- **Remove**: `const startAgentTerminal = useCreateManageAgentTerminal();`
- **Add**: `const createManageAgentTerminal = useCreateManageAgentTerminal();`
- **Add**: `const { data: manageAgentTerminals } = useManageAgentTerminals();`
- **Add**: `const killTerminal = useKillTerminal();`
- **Add**: `const [chatTerminalId, setChatTerminalId] = useState<string | null>(null);`
- **Remove**: `const [startingAgentId, setStartingAgentId] = useState<string | null>(null);`

### 3. Remove handleStartAgent function
Delete the entire `handleStartAgent` function.

### 4. Add handleStartChat and handleEndChat functions
```typescript
const handleStartChat = async () => {
  try {
    const terminal = await createManageAgentTerminal.mutateAsync({});
    setChatTerminalId(terminal.id);
  } catch (err) {
    // toast error handled by hook
  }
};

const handleEndChat = async () => {
  if (chatTerminalId) {
    try { await killTerminal.mutateAsync(chatTerminalId); } catch {}
    setChatTerminalId(null);
  }
};
```

### 5. Update header buttons
Replace the existing header with a "Start Conversation" button (using MessageSquare icon) next to Seed Defaults and Create Agent buttons. When terminal is active, show "End Conversation" button instead.

### 6. Remove Play button from each agent row
Remove the Play button block (the entire `<Button variant="ghost" size="icon" ...>` for Play) from the actions column.

### 7. Add TerminalPanel below the table
When `chatTerminalId` is set, render `<TerminalPanel terminalId={chatTerminalId} projectId={_projectId} onSessionEnd={handleEndChat} />` below the table.

### 8. Reattach to existing terminal on mount
Use useEffect to check `manageAgentTerminals` and reattach to the latest active terminal for this project (same pattern as AskPage lines 29-37).

## Verification
1. `npm run dev` — verify Agents tab loads
2. Click "Start Conversation" — verify terminal opens with /manage-agent command
3. Verify table still shows with terminal below
4. Click "End Conversation" — verify terminal closes
5. Verify no Play buttons on agent rows
6. Verify Edit and Delete buttons still work