Changed `get_dashboard_data()` in `project_service.py:77` from `list_issues_full()` to `list_issues()`. 

**Why:** `list_issues_full()` loads all markdown bodies (description, specification, plan, recap) for every active issue — 4N file reads. The dashboard only needs name, status, priority, which `list_issues()` returns from the `issues.yaml` index without touching any markdown files.

**Impact:** For 50 active issues, saves ~200 disk reads per dashboard request. Cache layer (30s TTL) partially mitigated this but the call was still wasteful.

**Verification:** Dashboard tests show same results before and after — 1 pass, 3 pre-existing failures (KeyError on project creation, unrelated infrastructure issue). No regression.