# Rich Notifications Design

**Date:** 2026-03-27
**Status:** Approved

## Overview

Improve the WebSocket notification system so every toast shows the project name and issue name (where applicable), instead of generic "Event" / "New event" labels.

Toast format (using sonner):
- **Title:** issue name (or file/item title for embedding events)
- **Description:** `"ProjectName • human-readable event description"`
- **Action button:** "View" — only when `project_id` + `issue_id` are present

All event types continue to show a toast (approach A — no filtering).

---

## Backend Changes

### 1. `backend/app/services/issue_service.py`

`accept_issue` and `cancel_issue` already fire hooks but do not pass names in `HookContext.metadata`. Add a project fetch and populate metadata, matching the pattern already used by `complete_issue`:

```python
project = await ProjectService(self.session).get_by_id(project_id)
HookContext(
    project_id=project_id,
    issue_id=issue_id,
    event=HookEvent.ISSUE_ACCEPTED,  # or ISSUE_CANCELLED
    metadata={
        "issue_name": issue.name or (issue.description or "")[:50] or "Untitled",
        "project_name": project.name if project else "",
    },
)
```

### 2. `backend/app/hooks/registry.py`

All three hook events (`hook_started`, `hook_completed`, `hook_failed`) gain two new fields sourced from `HookContext.metadata`:

```python
"issue_name": context.metadata.get("issue_name", ""),
"project_name": context.metadata.get("project_name", ""),
```

### 3. `backend/app/mcp/server.py` — `send_notification`

Already fetches the issue. Add a project fetch and include `project_name` in the emitted event:

```python
project_service = ProjectService(session)
project = await project_service.get_by_id(project_id)
await event_service.emit({
    ...existing fields...,
    "project_name": project.name if project else "",
})
```

### 4. `backend/app/services/rag_service.py`

Add `project_name: str` parameter to both `embed_file` and `embed_issue`. Include `project_id` and `project_name` in all emitted embedding events:

```python
await self.event_service.emit({
    "type": "embedding_completed",
    "source_type": "...",
    "source_id": source_id,
    "title": title,
    "project_id": project_id,
    "project_name": project_name,
    "timestamp": ...,
})
```

### 5. Call sites for `RagService`

- **`server.py` (`complete_issue`):** already fetches the project for hook metadata → pass `project.name` to `rag.embed_issue()`
- **Files router (`embed_file`):** fetch the project before launching the background task → pass `project.name` to `rag.embed_file()`

---

## Frontend Changes

### `frontend/src/shared/context/event-context.tsx`

Replace the current flat toast call with type-aware logic:

```typescript
function buildToast(data: Record<string, unknown>): { title: string; description: string } {
  const type = data.type as string;
  const issueName = (data.issue_name as string) || "";
  const projectName = (data.project_name as string) || "";
  const title = (data.title as string) || "";
  const message = (data.message as string) || "";
  const hookName = (data.hook_name as string) || "";
  const error = (data.error as string) || "";

  const prefix = projectName ? `${projectName} • ` : "";

  switch (type) {
    case "notification":
      return {
        title: issueName || "Notifica",
        description: `${prefix}${message}`,
      };
    case "hook_started":
      return {
        title: issueName || "Hook avviato",
        description: `${prefix}${hookName} in esecuzione…`,
      };
    case "hook_completed":
      return {
        title: issueName || "Hook completato",
        description: `${prefix}${hookName} completato`,
      };
    case "hook_failed":
      return {
        title: issueName || "Hook fallito",
        description: `${prefix}${error || "Errore sconosciuto"}`,
      };
    case "embedding_completed":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding completato`,
      };
    case "embedding_failed":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding fallito: ${error}`,
      };
    case "embedding_skipped":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding saltato`,
      };
    default:
      return {
        title: issueName || title || "Evento",
        description: `${prefix}${message || "New event"}`,
      };
  }
}
```

The existing `toast()` call is replaced with:

```typescript
const { title, description } = buildToast(data);
toast(title, {
  description,
  action: projectId && issueId ? { label: "View", onClick: ... } : undefined,
});
```

---

## Event Payload Reference (after changes)

| Event type | Fields always present | New fields |
|---|---|---|
| `notification` | type, title, message, project_id, issue_id, issue_name, timestamp | `project_name` |
| `hook_started` | type, hook_name, hook_description, issue_id, project_id, timestamp | `issue_name`, `project_name` |
| `hook_completed` | type, hook_name, issue_id, project_id, output, timestamp | `issue_name`, `project_name` |
| `hook_failed` | type, hook_name, issue_id, project_id, error, timestamp | `issue_name`, `project_name` |
| `embedding_completed` | type, source_type, source_id, title, timestamp | `project_id`, `project_name` |
| `embedding_failed` | type, source_type, source_id, title, error, timestamp | `project_id`, `project_name` |
| `embedding_skipped` | type, source_type, source_id, title, reason, timestamp | `project_id`, `project_name` |

---

## Files to Change

**Backend:**
- `backend/app/services/issue_service.py`
- `backend/app/hooks/registry.py`
- `backend/app/mcp/server.py`
- `backend/app/services/rag_service.py`
- Files router (to be identified — calls `embed_file`)

**Frontend:**
- `frontend/src/shared/context/event-context.tsx`

---

## Out of Scope

- Notification history / inbox panel
- Per-event-type toast styling (colors, icons)
- Filtering which events produce a toast
- `update_task_status` emitting its own events
