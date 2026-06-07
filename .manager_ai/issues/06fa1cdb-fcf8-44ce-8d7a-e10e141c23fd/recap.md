## Test Results — PASS

**Bug**: Pipeline terminal for WSL+Ubuntu projects opens in Manager AI software folder instead of project folder. "Run Issue" works correctly.

**Fix**: Added `cd <posix_path>` emission into PTY after terminal creation in `pipeline_run_service.py:_execute()`, matching the router's WSL handling in `terminals.py:128-131`. Root cause: `terminal_service.create()` sets `spawn_cwd=None` for WSL (UNC paths rejected by Windows CreateProcess), assuming callers emit `cd` into the PTY — pipeline runner was missing this.

**Tests**: 54 passed (all WSL, pipeline, terminal tests). 2 pre-existing failures unrelated to fix.