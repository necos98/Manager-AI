## Implementation Plan

**Goal:** Remove `exc_info=True` from 3 `logger.warning` calls that handle corrupted data files.

**File:** `backend/app/main.py`

**Changes:**
1. Line 148: Remove `exc_info=True` from "Skipping corrupted memory file"
2. Line 198: Remove `exc_info=True` from "Skipping corrupted issue"
3. Line 243: Remove `exc_info=True` from "Skipping corrupted files index"

Line 363 ("Failed to install claude_resources") stays unchanged — operational failure, traceback useful.
