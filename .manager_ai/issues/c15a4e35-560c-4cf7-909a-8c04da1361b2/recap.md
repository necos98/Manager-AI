Added `prewarm_project_cache(project_path)` in `backend/app/storage/issue_store.py`.

**What it does:** When `list_issues_full()` is called on a cold cache, `prewarm_project_cache` iterates the issues directory once, reads all `issue.yaml` + markdown files, builds `IssueRecord` objects, and populates the in-process `issue_cache` for every issue in a single batch. Subsequent `load_issue()` calls within the same loop are all cache hits — zero disk I/O.

**Skip mechanism:** Checks if the index cache key (`{project_path}:__index__`) is already warm. If so, returns immediately to avoid re-reading files within the same TTL window. After prewarming, calls `list_issues()` to seed the index cache.

**Edge cases handled:** Empty projects (no issues directory), missing individual YAML/MD files, partially cached state — all handled gracefully.

**Files changed:**
- `backend/app/storage/issue_store.py:124-185` — added `prewarm_project_cache()` function + 1-line call in `list_issues_full`
- `backend/tests/storage/test_issue_store.py` — added `TestPrewarmCache` class with 4 tests

**Test results:** 104/104 storage tests pass. Full suite: 122 pass, 1 pre-existing failure in `test_db_backup.py` (unrelated).