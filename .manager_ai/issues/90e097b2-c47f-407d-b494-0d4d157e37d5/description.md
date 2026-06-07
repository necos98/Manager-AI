## Pipeline Windows PTY: `exit` command race condition  

### Summary  
In `pipeline_run_service.py:_run_step()` (line 568-570), on Windows, the `exit` command is written to the PTY as a **separate write** immediately after the `claude` command. This creates a race condition where `cmd.exe` can process `exit` before `claude.exe` finishes its work, causing the PTY to die prematurely and the pipeline to fail or hang.

### Location  
`backend/app/services/pipeline_run_service.py` — `_run_step()` method, lines 565-572  

```python
is_windows = _platform.system() == "Windows"  
command = f'claude --dangerously-skip-permissions "/run-pipeline {issue_id}"'  

if is_windows:  
    pty.write(f"{command}\r\n")       # Write claude command  
    pty.write("exit\r\n")             # Write exit IMMEDIATELY after  
else:  
    pty.write(f"{command}; exit\r\n") # Linux: single write, shell waits  
```

### Root Cause  
On **Linux** (`command; exit\r\n`): the `exit` is part of the same shell command string. The shell (`bash`) waits for `claude` to finish before processing `; exit`. This is safe.  

On **Windows**: two **separate** `pty.write()` calls. pywinpty writes both lines into the PTY's input buffer nearly simultaneously. The shell (`cmd.exe`) reads and processes them sequentially:
1. `claude ...` → starts `claude.exe` (which may be a `.cmd` batch wrapper that spawns Node.js and returns immediately)
2. `exit` → processed as soon as claude.exe returns

The problem: if `claude.exe` is a batch wrapper (`.cmd`) that spawns `node.exe` and exits, cmd.exe does NOT wait for Node.js. It immediately reads `exit` from the buffer, the shell terminates, the PTY detects EOF, and `_run_step`'s `pty_task` completes before the agent can call `finished_pipeline_step`.

### Consequences  
- `_run_step()` returns `success = False` (line 595-599)  
- Pipeline transitions to **FAILED**  
- Agent's work is lost, pipeline must be restarted  
- In worst case, agent is mid-execution when PTY dies → corrupted state  

### Impact  
All pipeline runs on **Windows**. Platform-specific. Not reproducible on Linux/WSL.

### Steps to reproduce  
1. Start a pipeline run on Windows  
2. Observe PTY behavior: `exit` is queued before Claude finishes  
3. Claude process (batch wrapper) exits before actual Node.js work completes  
4. Pipeline fails with log: `"Step X failed: PTY died before finished_pipeline_step called"`

### Fix  
Merge the `exit` into the same write as the claude command using shell chaining (`&` on Windows):

```python
if is_windows:  
    pty.write(f"{command} & exit\r\n")  # cmd.exe: run claude, then exit when done  
else:  
    pty.write(f"{command}; exit\r\n")
```

`&` in cmd.exe means "run the first command, then run the second after it completes" — same semantics as `;` in bash.

### Related  
Issue #2: pipeline agents don't explicitly call `finished_pipeline_step` — combined, these two bugs mean agents both forget to signal AND the PTY dies before they can.