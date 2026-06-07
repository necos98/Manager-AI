Fixed Windows orphan process in start.py re-exec by replacing subprocess.run()+sys.exit() with Win32 Job Object kill-on-close pattern.

Changes in start.py:
- Added `import ctypes` (stdlib, no new deps — matches desktop_icon.py pattern)
- Defined `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` ctypes struct (x64 layout, 152 bytes) and Win32 constants under `if IS_WINDOWS:` guard
- Added `_run_windows_reexec(cmd)` helper: creates unnamed Job Object, sets JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, spawns child with CREATE_BREAKAWAY_FROM_JOB (escapes Windows Terminal job), assigns child to job, waits via Popen.wait(). Falls back silently to bare Popen.wait() on any API failure
- Windows branch in `_bootstrap_venv_and_reexec()` now calls `_run_windows_reexec()` instead of subprocess.run()

Result: when terminal/launcher is killed, the parent process dies, the Job Object handle closes, and Windows terminates the child process automatically. No orphan processes.