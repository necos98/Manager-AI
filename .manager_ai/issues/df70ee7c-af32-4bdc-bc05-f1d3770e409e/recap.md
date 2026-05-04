## Summary
Added `_check_resource_consistency()` to the project health endpoint `GET /api/projects/{project_id}/health`. The new check reads `manager.json` as the authoritative source for `project_id`, then scans all YAML resources in `.manager_ai/` for mismatches and auto-fixes them.

### Resources checked
1. `issues.yaml` index — each entry's `project_id`
2. `.manager_ai/issues/<id>/issue.yaml` — individual issue files
3. `memories.yaml` index — each entry's `project_id`
4. `.manager_ai/memories/<id>.md` — YAML frontmatter `project_id`

### Behavior
- **Auto-fix always**: no flag needed, mismatches are corrected immediately
- **Skip gracefully**: if `manager.json` missing/unreadable, returns `ok: null` with a note
- **Atomic writes**: uses `tmp + os.replace()` pattern
- **Report**: returns `{ ok, scanned, fixed, details[] }` with per-resource mismatch info

### Files changed
- `backend/app/routers/projects.py` — new function + wired into `project_health()`
- `backend/tests/test_routers_projects.py` — 9 unit tests + 1 integration test

### Decisions
- All file types scanned in a single pass through the health endpoint (no separate endpoint)
- Markdown frontmatter for memories handled via `split("---", 2)` — preserves body content exactly
- Missing optional directories/files are silently skipped (not errors)
- All A options chosen: everything scanned, auto-fix always, lives in projects.py alongside existing checks