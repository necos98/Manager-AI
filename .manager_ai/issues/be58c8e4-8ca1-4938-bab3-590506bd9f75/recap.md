## Recap

3 root causes fixed:

1. **CSS height chain broken (AgentsTab.tsx)**: Terminal wrapper div had `min-h-[400px]` but no flex context. TerminalPanel's `h-full` (height:100%) resolved to 0 in normal block flow, causing xterm `openIfReady()` to never fire (clientHeight === 0). Fix: changed wrapper to `flex flex-col` with inner `flex-1 min-h-0` div — matching TerminalGrid pattern used by the global Terminals page.

2. **Missing query invalidation (hooks.ts)**: `useCreateManageAgentTerminal` mutation `onSuccess` didn't invalidate `terminalKeys.manageAgent`. After terminal creation, the reconnection `useEffect` in AgentsTab couldn't reattach on component remount because it used stale query data. Fix: added `queryClient.invalidateQueries({ queryKey: terminalKeys.manageAgent })`.

3. **Empty-string filter bug (terminal_service.py)**: `list_active(project_id="")` treated empty string as falsy, returning ALL active terminals instead of only those with `project_id=""`. This could kill unrelated terminals (ask, issue-scoped) when creating manage-agent terminals. Fix: changed `if project_id` (truthiness check) to `if project_id is not None` (explicit None check).