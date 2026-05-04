## Fix: Exclude root-level index YAML files from watcher classification

**Goal:** Stop filesystem watcher from self-triggering on index files it writes (`issues.yaml`, `memories.yaml`, `files.yaml`).

**Approach:** Modify `_classify` in `_Handler` to distinguish between directory changes (`issues/`, `memories/`, `files/`) and root-level index files (`issues.yaml`, `memories.yaml`, `files.yaml`). Only directory content changes should trigger index rebuild.

### Change

In `backend/app/services/manager_ai_watcher.py`, `_classify` method (lines 67-73):

```python
# Before (buggy):
if parts[0] in {"issues", "issues.yaml"}:
    return "issues"
if parts[0] in {"memories", "memories.yaml"}:
    return "memories"
if parts[0] in {"files", "files.yaml"}:
    return "files"

# After (fixed):
if parts[0] == "issues" and len(parts) > 1:
    return "issues"
if parts[0] == "memories" and len(parts) > 1:
    return "memories"
if parts[0] == "files" and len(parts) > 1:
    return "files"
```

**Logic:** When `parts[0]` is `"issues"` and `len(parts) > 1`, the changed file is inside `issues/<id>/` — a real data change. When `parts` is `["issues.yaml"]` (length 1), it's the index file the watcher just wrote — skip it.

### Edge cases verified
- Individual issue file changes inside `issues/<id>/` → `parts = ["issues", "<id>", "issue.yaml"]` → `len > 1` → triggers rebuild ✓
- Root `issues.yaml` change → `parts = ["issues.yaml"]` → `len == 1` → skipped ✓
- External tool touches `issues.yaml` directly → skipped (acceptable — index rebuilt on next real data change or app restart)