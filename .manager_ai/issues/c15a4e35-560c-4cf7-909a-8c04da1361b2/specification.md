## Purpose

Reduce perceived latency on first project navigation by batch-loading all issue files into cache at once, instead of sequential scattered reads.

## Current behavior

`list_issues_full(project_path)` reads the index (`issues.yaml`), then calls `load_issue()` for each issue. Each `load_issue()` call hits disk: 1 YAML + up to 4 markdown files. On first access (cold cache), N issues = N * 5 file reads, all sequential.

## Proposed solution

Add `prewarm_project_cache(project_path)` in `backend/app/storage/issue_store.py`:

1. Check if index cache key (`{project_path}:__index__`) is warm — if so, skip (already prewarmed this TTL window).
2. Call `list_issues()` to get the index (one disk read or cache hit).
3. Glob all `issue.yaml` files under `.manager_ai/issues/*/issue.yaml`.
4. For each YAML: parse it, read associated `.md` files (description, specification, plan, recap), build an `IssueRecord`, set it in cache at key `{project_path}:{issue_id}`.
5. Return. `list_issues_full` then calls `load_issue()` per issue — all cache hits, zero disk I/O.

### Function signature
```python
def prewarm_project_cache(project_path: str) -> None:
```

### Integration point
```python
def list_issues_full(project_path: str) -> list[IssueRecord]:
    prewarm_project_cache(project_path)
    index = list_issues(project_path)
    out = []
    for light in index:
        full = load_issue(project_path, light.id)  # all cache hits
        if full is not None:
            out.append(full)
    return out
```

### Edge cases
- **Empty project**: no issues → glob empty → no-op.
- **Missing .md fields**: `_read_optional_md` returns `None`, same as `load_issue`.
- **TTL expiry**: after 30s, next `list_issues_full` triggers re-prewarm. Same cache semantics as today.

## Files changed
- `backend/app/storage/issue_store.py` — new function + 1-line call in `list_issues_full`

## Tests
- `backend/tests/storage/test_issue_store.py` — test that prewarm populates all cache keys and `list_issues_full` returns correct data