## Root Cause

Filesystem watcher (`manager_ai_watcher.py`) self-triggers on index files it writes, creating infinite event loop.

### Chain

1. Any change to `issues/<id>/issue.yaml` → `_Handler.on_any_event` → `_classify` returns `"issues"`
2. 500ms debounce → `_flush("issues")` → `rebuild_issues_index()` → writes `issues.yaml` via `atomic.write_yaml`
3. `issues.yaml` is inside watched `.manager_ai/` root → watcher fires again
4. `_classify` checks `parts[0]` — `"issues.yaml"` falls into `{"issues", "issues.yaml"}` → returns `"issues"`
5. Goto step 2 — infinite loop, each iteration emits `issue_updated` event via `event_service.emit`

Same bug for `memories.yaml` and `files.yaml`.

### Why flat-system introduced this

Before flat-system: no filesystem watcher existed. MCP tools wrote to DB and emitted events directly. Flat-system added `manager_ai_watcher.py` to detect external file changes (git pull, other users) and rebuild indices. The watcher correctly watches for individual issue/memory/file changes, but fails to exclude the index YAML files that `rebuild_*_index` writes.

## Fix

Modify `_classify` in `backend/app/services/manager_ai_watcher.py` to return `None` when the changed file is a root-level index file (`issues.yaml`, `memories.yaml`, `files.yaml`). These are outputs of the rebuild process, not inputs that should trigger another rebuild.

### Change

In `_classify`, differentiate between:
- `issues/` directory (contains individual issue files) → `"issues"` (legitimate trigger)
- `issues.yaml` file (the generated index) → `None` (skip, self-inflicted write)

Same for `memories/` vs `memories.yaml` and `files/` vs `files.yaml`.

### Edge cases
- Individual issue files inside `issues/<id>/` still trigger rebuild correctly
- The first MCP write triggering the watcher is correct (it catches external changes)
- If `issues.yaml` is deleted externally (e.g., git pull removing it), the watcher SHOULD rebuild it. But a deleted `issues.yaml` won't be picked up by current watcher anyway since it only watches existing files. The index is rebuilt on next app startup via startup scan.
- No debounce logic changes needed — the 500ms debounce still collapses rapid writes