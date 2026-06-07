## Windows PTY Exit Race Condition Fix

### Problem
In `pipeline_run_service.py:_run_step()`, the `exit` command is written as a **separate** `pty.write()` call immediately after the `claude` command on Windows. This creates a race condition: `cmd.exe` can process `exit` before `claude.exe` finishes, killing the PTY and causing the pipeline step to FAIL.

Relevant memory: PTY death without `finished_pipeline_step` = strict FAILURE ([[cb0b9511]]). So this race doesn't just end the step early — it causes pipeline failure.

### Root Cause
Two separate `pty.write()` calls on Windows:
```python
pty.write(f"{command}\r\n")   # write 1: claude command
pty.write("exit\r\n")         # write 2: exit immediately after
```

Linux uses `command; exit\r\n` as a single write where bash waits for claude to finish before `; exit`. Windows `cmd.exe` processes queued input line-by-line — if `claude.exe` is a batch wrapper (`.cmd`) that spawns `node.exe` and returns, `cmd.exe` immediately reads `exit` from the buffer.

### Fix
Merge `exit` into the same write using `&` (cmd.exe chaining, same semantics as bash `;`):

```python
if is_windows:
    pty.write(f"{command} & exit\r\n")  # cmd.exe waits for claude, then exits
else:
    pty.write(f"{command}; exit\r\n")   # unchanged
```

`&` in cmd.exe = "run first command, then run second after it completes" — identical semantics to `;` in bash.

### Scope
1 file changed: `backend/app/services/pipeline_run_service.py` — `_run_step()` method, ~3 lines.

### Testing
- Manual: start pipeline run on Windows, verify step completes without premature PTY death
- Existing pipeline tests should pass unchanged (Linux path unaffected, Windows `&` is a no-op diff in PTY test context since tests use mock PTY)