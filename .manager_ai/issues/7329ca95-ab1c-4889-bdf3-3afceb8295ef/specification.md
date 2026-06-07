## Problem

`start.py` `_bootstrap_venv_and_reexec()` on Windows (lines 106-108) spawns a child process via `subprocess.run()` and exits with `sys.exit()`. When the user kills the terminal, the child process survives as an orphan — no process tree binding ties it to the parent.

```python
if IS_WINDOWS:
    ret = subprocess.run([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]).returncode
    sys.exit(ret)
```

Linux uses `os.execv` which replaces the process (same PID, clean), so it's unaffected.

## Scope

Modify only the Windows branch of `_bootstrap_venv_and_reexec()` in `start.py` (lines 105-108). The re-executed Python process must die when the terminal/launcher that spawned it is killed.

## Out of Scope

- The `main()` function's process management (backend/frontend subprocesses) — those are handled via `Popen` + `terminate()` and work correctly.
- The Linux `os.execv` path — unchanged.
- Adding new pip dependencies — not allowed.

## Constraints

1. **No new dependencies** — use `ctypes` (stdlib), matching the existing `desktop_icon.py` pattern.
2. **CREATE_BREAKAWAY_FROM_JOB** (0x02000000) required — Windows Terminal and other launchers put processes in a job by default. Without this flag, `AssignProcessToJobObject` fails with `ERROR_ACCESS_DENIED`.
3. **Parent must hold the job handle** — call `Popen.wait()` (blocking, matching the current `subprocess.run()` behavior) so the handle stays alive until the child exits. When the parent is killed or exits, the handle closes and `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` triggers child termination.
4. **Silent fallback** — if any Job API call fails (unusual security policies or ancient Windows), fall back to the current behavior without crashing or logging errors.

## Approach

Replace the current two-line Windows block with:
1. Create a Win32 Job Object via `ctypes.windll.kernel32.CreateJobObjectW`.
2. Set `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` via `SetInformationJobObject` with a `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` struct.
3. Spawn the child with `subprocess.Popen(creationflags=CREATE_BREAKAWAY_FROM_JOB)` (instead of `subprocess.run()`).
4. Assign the child process to the job via `AssignProcessToJobObject` using `Popen.handle`.
5. Call `Popen.wait()` to block until the child exits (preserving existing behavior).
6. On failure at any step (ctypes load error, API call failure, handle error), silently skip Job Object setup and fall back to bare `Popen.wait()`.

## Acceptance Criteria

1. Killing the terminal (Ctrl+C, window close, taskkill) terminates the re-executed Python process.
2. Normal operation unchanged — re-exec still spawns correctly and waits for completion.
3. No new pip dependencies.
4. Non-Windows platforms completely unaffected.
5. If Job Object API is unavailable, behavior degrades gracefully to current behavior (orphan possible but no crash).
