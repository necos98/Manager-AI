## Tester Recap: Pipeline shell config fix

**What was tested:**
- Pipeline run service tests: 8/8 PASSED
- Full backend suite: 590 passed, 33 failed (all pre-existing)
- No regressions from the fix

**Fix applied:**
- `backend/app/services/pipeline_run_service.py:_execute()` now passes `shell` and `wsl_distro` to `terminal_service.create()`. Pipeline terminals now respect project shell config (WSL/Ubuntu) instead of always defaulting to CMD.

**All pipeline agents: PASS** — BugHunter → Developer → CodeReviewer → QualityReviewer → Tester