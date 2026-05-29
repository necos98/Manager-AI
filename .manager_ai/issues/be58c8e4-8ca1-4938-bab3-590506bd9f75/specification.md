## Summary

"Start Conversation" in Agents section creates terminal but TerminalPanel doesn't render properly — terminal only visible in global Terminals page. Three issues found.

## Root Cause 1: CSS height chain broken (primary)

**AgentsTab.tsx** terminal wrapper div:
```html
<div class="border rounded-lg overflow-hidden min-h-[400px]">
  <TerminalPanel />  <!-- has h-full (height: 100%) -->
</div>
```

In normal block flow, `height: 100%` on child resolves to **0** when parent has only `min-height` (no explicit `height`). TerminalPanel's ResizeObserver sees `clientHeight === 0` and never opens xterm.

**Fix:** Match TerminalGrid pattern — add `flex flex-col` to wrapper + inner `flex-1 min-h-0` div:
```html
<div class="border rounded-lg overflow-hidden min-h-[400px] flex flex-col">
  <div class="flex-1 min-h-0">
    <TerminalPanel />
  </div>
</div>
```

This gives TerminalPanel a definite flex-basis for `h-full` to resolve.

## Root Cause 2: Missing query invalidation (secondary)

`useCreateManageAgentTerminal` mutation `onSuccess` doesn't invalidate `terminalKeys.manageAgent`. After creating terminal, the reconnection `useEffect` (lines 159-167) uses stale `manageAgentTerminals` data. On component remount (route navigation), the effect fails to reattach.

**Fix:** Add `queryClient.invalidateQueries({ queryKey: terminalKeys.manageAgent })` to `onSuccess`.

## Root Cause 3: `list_active` empty-string filter bug (secondary)

`TerminalService.list_active(project_id="", issue_id="")` in `terminals.py:create_manage_agent_terminal`:

```python
if project_id and term["project_id"] != project_id:  # "" is falsy → no filter!
```

Empty string `""` is falsy in Python, so `project_id=""` means **no filtering**. This kills ALL active terminals (not just manage-agent) when creating a new one.

**Fix:** Use `is not None` instead of truthiness for both filters.

## Files Changed

1. `frontend/src/features/agents/components/AgentsTab.tsx` — fix wrapper layout
2. `frontend/src/features/terminals/hooks.ts` — add manageAgent invalidation
3. `backend/app/services/terminal_service.py` — fix list_active filter
