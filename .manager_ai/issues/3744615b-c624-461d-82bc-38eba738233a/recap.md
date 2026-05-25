Removed `exc_info=True` from 3 `logger.warning` calls in `backend/app/main.py`:
- Line 148: "Skipping corrupted memory file"
- Line 198: "Skipping corrupted issue"
- Line 243: "Skipping corrupted files index"

Corrupted data files are recoverable edge cases — the warning message with the file path is sufficient. Stack traces added noise without actionable info. Line 363 ("Failed to install claude_resources") keeps `exc_info=True` as that's an operational failure where traceback aids debugging.
