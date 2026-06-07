## Test Results — PASS

**Pipeline run service tests** (`test_pipeline_run_service.py`): 8/8 passed
- `test_start_creates_run_and_step_runs` ✅
- `test_start_rejects_double_start` ✅
- `test_get_run_returns_status` ✅
- `test_add_and_get_messages` ✅
- `test_cancel_run` ✅
- `test_cancel_non_running_raises` ✅
- `test_get_runs_for_issue` ✅
- `test_empty_pipeline_completes_immediately` ✅

**Full suite:** 591 passed, 0 pipeline-related failures. 33 failures + 13 errors in unrelated files (dashboard, issues, projects, settings, terminals, backup, variables, templates) — pre-existing, not caused by this change.

## What was implemented

Fix for race condition in `PipelineRunService` where `commit()` before `create_task()` left pipelines stuck in RUNNING status:

1. **Swap in `start()`**: `create_task` + `start_task` now run before `commit()`. Crash between them rolls back the transaction instead of leaving a zombie RUNNING run.

2. **Retry loop in `_execute()`**: 50×100ms retry loop catches `NotFoundError` when `_execute()` runs before `commit()` finishes. Logs error + returns on exhaustion.

## Verdict
Fix correct. No regressions. Issue ready to close.