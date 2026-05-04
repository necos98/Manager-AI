## Root cause

Filesystem watcher (`manager_ai_watcher.py`) self-triggered on index files it wrote, creating infinite event loop.

### Chain
1. Any write to `issues/<id>/issue.yaml` → watcher detects → `_classify` returns `"issues"`
2. 500ms debounce → `_flush("issues")` → `rebuild_issues_index()` → writes `issues.yaml`
3. Writing `issues.yaml` → watcher detects it in watched root → `_classify` matched `"issues.yaml"` in `{"issues", "issues.yaml"}` → returned `"issues"`
4. Infinite loop, each iteration emitted `issue_updated` event to frontend

Same bug existed for `memories.yaml` and `files.yaml`.

## Fix

Modified `_classify` in `_Handler` (line 67-73) to distinguish directory content changes from root-level index files:

```python
# Before: if parts[0] in {"issues", "issues.yaml"}: return "issues"
# After:  if parts[0] == "issues" and len(parts) > 1: return "issues"
```

When `parts[0]` is `"issues"` and `len(parts) > 1`, the file is inside `issues/<id>/` — real data change. When `parts` is `["issues.yaml"]` (length 1), it's the index the watcher just wrote — skipped.

## Files changed
- `backend/app/services/manager_ai_watcher.py` — 3 lines in `_classify` method
- `backend/tests/test_manager_ai_watcher.py` — added `test_watcher_skips_root_index_files_but_reacts_to_content`