## Specification: Suppress stack trace on corrupted file load

**Problem:** When loading data files (memories, issues, files index) from `.manager_ai/`, a corrupted file triggers a `logger.warning` with `exc_info=True`, dumping the full stack trace to the output. The stack trace is noise — the warning message with the file path is sufficient.

**Files affected:** `backend/app/main.py`

**Changes:**
1. Remove `exc_info=True` from `logger.warning` for "Skipping corrupted memory file" (line 148)
2. Remove `exc_info=True` from `logger.warning` for "Skipping corrupted issue" (line 198)  
3. Remove `exc_info=True` from `logger.warning` for "Skipping corrupted files index" (line 243)

All three follow the same pattern: a corrupted data file is a recoverable edge case, not a crash. The warning log with the file path tells the user what was skipped. The traceback adds no actionable information.

**Not changed:** `logger.warning` for "Failed to install claude_resources" (line 363) keeps `exc_info=True` — that's an operational failure where traceback could help debugging.

**Risk:** None. Pure logging change. No behavior or flow change.
