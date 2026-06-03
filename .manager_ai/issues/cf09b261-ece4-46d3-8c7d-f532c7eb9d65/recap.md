## Code Review Complete — Terminal Leak Fix

### What Was Reviewed
3 fix locations for terminal session leaks + Question FK constraint:

**Fix 1 — pipeline_run_service.py:21,234-236** ✅
Added `_sessions` and `_stop_reader` to import; added `_stop_reader()` and `_sessions.pop()` to `_execute()` finally block before `kill()`. Cleanup order: `save_recording → stop_reader → pop → kill` — matches canonical `_teardown_terminal()`.

**Fix 2 — projects.py:20,357-358** ✅
Added `from app.services.terminal_session import _sessions, _stop_reader`; added same cleanup sequence before `kill()` in `delete_project` terminal loop.

**Fix 3 — question.py:4,16** ⚠️ **Bug Found & Fixed**
Developer removed `ForeignKey` from import (line 4) while removing `ForeignKey("issues.id")` from `issue_id` column (line 16). But `ForeignKey` is still used by `project_id` (line 15). This caused `NameError` on fresh import. Stale `.pyc` masked the bug in first test run. Fixed by adding `ForeignKey` back to the import.

### Tests
- `test_pipeline_run_service.py`: 8/8 pass ✅
- `test_models_pipeline.py`: 9/9 pass ✅
- Total: 17/17 pass after fix

### Memories Saved
1. Pipeline terminal cleanup order must match `_teardown_terminal()` pattern
2. Removing FK from column needs import usage check across entire file