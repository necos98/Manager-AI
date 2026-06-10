# Snackbar Undo Issue Delete Implementation Plan

**Goal:** Replace permanent issue deletion with soft-delete + 5s undo snackbar via sonner.

**Architecture:** Add `deleted_at` timestamp to `IssueRecord`. `DELETE` marks `deleted_at` instead of removing files. List endpoints filter out soft-deleted issues. `POST /restore` clears `deleted_at`. Frontend shows sonner toast with Undo action on delete, navigates away only after toast expires. Background purge cleans up old soft-deletes after 30s TTL.

**Tech Stack:** Python/FastAPI backend (issue_store + issue_service), React/Vite frontend (sonner), YAML-file-backed IssueRecord dataclass.

---

### Task 1: Backend — Add `deleted_at` to IssueRecord + filter from listings
- Add `deleted_at: str | None = None` field to `IssueRecord` dataclass in `backend/app/storage/issue_store.py`
- Add `deleted_at` to `_to_index_entry()` and `_index_to_light_record()` so the field propagates through the index
- Filter out records with `deleted_at` set in `list_issues()` and `list_issues_full()`
- Add `list_deleted_issues()` helper for admin/debug

### Task 2: Backend — Soft-delete + Restore + Permanent Delete in IssueService + Router
- Modify `issue_service.delete()` to soft-delete: set `deleted_at` timestamp on record, don't remove files
- Add `issue_service.restore()`: clear `deleted_at`, issue reappears in listings
- Add `issue_service.permanently_delete()`: the old behavior (RAM + disk removal)
- Add POST `/{issue_id}/restore` and DELETE `/{issue_id}/permanent` endpoints to `routers/issues.py`
- Update MCP `shared_tools.py` `delete_issue` to soft-delete + add `restore_issue` MCP tool
- Wire new MCP tools in `orchestrator_server.py`

### Task 3: Backend — Background purge for expired soft-deletes
- Add `purge_expired_deleted(project_id, ttl_seconds=30)` to IssueService
- Add `list_issues_full_raw()` to issue_store (includes deleted records)
- Schedule periodic purge every 60s in `main.py` lifespan

### Task 4: Frontend — Snackbar undo on issue delete
- Add `restoreIssue()` and `permanentlyDeleteIssue()` API functions in `api.ts`
- Add `useRestoreIssue` mutation hook in `hooks.ts`
- Modify `handleDelete` in `issue-detail.tsx`: soft-delete → show sonner toast with "Undo" button (5s duration) instead of navigating immediately
- On Undo click: call restore API, show success toast
- On toast dismiss/auto-close: navigate to issues list