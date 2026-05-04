## Problem

The filesystem watcher (`manager_ai_watcher.py`) emits `issue_updated` and `file_updated` events when it detects file changes and rebuilds index files. These events reach the frontend via WebSocket and produce toast notifications with the bare event type as title ("issue_updated", "file_updated"), plus a notification sound. This creates noise during normal operation, especially when external processes or Claude Code write files to `.manager_ai/`.

The `memory_updated` event from the same watcher is already correctly handled — it's silenced (no toast, no sound) but still triggers cache invalidation. The `issue_updated` and `file_updated` events should behave the same way.

## Root Cause

In `frontend/src/shared/context/event-context.tsx`, the `buildToastContent` function handles known event types explicitly. `memory_updated` and related memory events return `{ silent: true }`. But `issue_updated` and `file_updated` are not listed — they fall through to the `default` case, which creates a visible toast with title = `data.type` (the raw event type string).

## Fix

In `event-context.tsx`, add `"issue_updated"` and `"file_updated"` to the existing case block that silences memory and project events (line 178). These events must still:

1. Reach the frontend (WebSocket message delivery unchanged)
2. Trigger cache invalidation (the existing invalidation logic in `ws.onmessage` fires before toast/sound)
3. **Not** show a toast
4. **Not** play notification sound

## Impact

- One line change in the frontend
- No backend changes
- No new dependencies
- Other notification types (issue status changes, hook events, content updates, notifications) are unaffected