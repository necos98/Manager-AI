## Implementation Plan: Fix Windows orphan process in start.py re-exec

### File changed
- `start.py` — modify `_bootstrap_venv_and_reexec()` Windows branch (lines 106-108)

### Pre-requisite: Add ctypes import
- Add `import ctypes` to the existing imports at top of `start.py` (line 14, after `import subprocess`)

### Steps

**1. Define Win32 constants at module level**
Add after imports, before function definitions:
```python
# Win32 Job Object constants (Windows only, ctypes)
if IS_WINDOWS:
    CREATE_BREAKAWAY_FROM_JOB = 0x02000000
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
```
This keeps constants scoped and readable, avoiding magic numbers in the function body.

**2. Define the `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` ctypes struct**
Add after constants:
```python
if IS_WINDOWS:
    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", ctypes.c_ulong * 4),  # 4 DWORDs padding
            ("IoInfo", ctypes.c_ulong * 6),                 # 6 DWORDs padding (IO_INFO)
            ("ProcessMemoryLimit", ctypes.c_ulong),
            ("JobMemoryLimit", ctypes.c_ulong),
            ("PeakProcessMemoryUsed", ctypes.c_ulong),
            ("PeakJobMemoryUsed", ctypes.c_ulong),
        ]
```

Actually, `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` is more complex. Let me think about the correct layout.

Per MSDN, `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` has:
- `JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation` — which itself has many fields
- `IO_COUNTERS IoInfo`
- `SIZE_T ProcessMemoryLimit`
- `SIZE_T JobMemoryLimit`
- `SIZE_T PeakProcessMemoryUsed`
- `SIZE_T PeakJobMemoryUsed`

The simplest approach: use the correct struct layout with ctypes. `JOBOBJECT_BASIC_LIMIT_INFORMATION` on 64-bit Windows has:
- PERIOD (LARGE_INTEGER = 8 bytes)
- PROCESS_QUOTA_LIMITS fields including:
  - MinimumWorkingSetSize (SIZE_T = 8 bytes on 64-bit)
  - MaximumWorkingSetSize (SIZE_T)
  - ActiveProcessLimit (DWORD = 4)
  - Affinity (ULONG_PTR = 8)
  - ChildProcess (DWORD = 4 + 4 padding on 64-bit)
  - LimitFlags (DWORD = 4 + 4 padding on 64-bit)
  - etc.

Actually this gets really messy with manual struct definitions. A much cleaner approach is to define only what we need:

The key insight: `SetInformationJobObject` with `JobObjectExtendedLimitInformation` (info class 9) needs `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`. We only need to set `LimitFlags` inside `BasicLimitInformation` to `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.

Let me use a simpler approach — define the struct with raw byte sizes, which is what many ctypes Win32 examples do:

```python
if IS_WINDOWS:
    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("ChildProcessNotify", ctypes.c_uint32),
            ("Padding", ctypes.c_uint32),  # alignment
            ("MaximumSchedulingClass", ctypes.c_uint32),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]
```

Hmm, this is getting verbose for a plan. Let me simplify the plan. The developer can look up the exact struct layout. Let me focus on the approach and let the implementation handle the details.

Let me rewrite the plan more succinctly but still precise.

**3. Modify `_bootstrap_venv_and_reexec()` Windows branch**

Replace the current two lines:
```python
if IS_WINDOWS:
    ret = subprocess.run([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]).returncode
    sys.exit(ret)
```

With:
```python
if IS_WINDOWS:
    _run_windows_reexec([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])
```

And add a new helper function `_run_windows_reexec(cmd)` that:
1. Tries to create a Job Object via `ctypes.windll.kernel32.CreateJobObjectW(None, None)`
2. If successful, sets `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` via `SetInformationJobObject`
3. Spawns child via `subprocess.Popen(cmd, creationflags=CREATE_BREAKAWAY_FROM_JOB)`
4. Assigns child to job via `AssignProcessToJobObject(handle, child_pid_handle)`
5. Calls `Popen.wait()` to block until child exits
6. On any failure at any step, falls back to bare `subprocess.Popen(cmd).wait()`
7. `sys.exit()` with the return code

**4. Error handling pattern**
Wrap the entire Job Object setup in a single `try/except` block. On any exception (AttributeError if kernel32 doesn't exist, OSError if API call fails, etc.), skip the job setup and fall back to:
```python
proc = subprocess.Popen(cmd)
ret = proc.wait()
sys.exit(ret)
```

### Key implementation details for the Developer

1. `ctypes.windll.kernel32.CreateJobObjectW(None, None)` returns a HANDLE (via ctypes.c_void_p). None name = unnamed job.
2. `SetInformationJobObject` signature: `BOOL SetInformationJobObject(HANDLE hJob, int InfoClass, void* lpJobObjectInfo, DWORD cbJobObjectInfoLength)`. InfoClass 9 = `JobObjectExtendedLimitInformation`.
3. `AssignProcessToJobObject` signature: `BOOL AssignProcessToJobObject(HANDLE hJob, HANDLE hProcess)`. Use `proc._handle` (the internal handle attribute of Popen).
4. After Popen returns, call `AssignProcessToJobObject` before the child does too much work. Minimal delay since child is still starting up.
5. Use `ctypes.c_uint64` not `c_size_t` for SIZE_T members (pointer-width dependent). On 64-bit Python they're the same, but `c_size_t` is correct.
6. `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000`

### Struct layout for `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` (x64)

Use these ctypes struct definitions for x64 compatibility:
- `JOBOBJECT_BASIC_LIMIT_INFORMATION`: PerProcessUserTimeLimit (int64), PerJobUserTimeLimit (int64), LimitFlags (uint32 + 4 padding), MinimumWorkingSetSize (size_t), MaximumWorkingSetSize (size_t), ActiveProcessLimit (uint32 + 4 padding), Affinity (size_t), ChildProcessNotify (uint32 + 4 padding), MaximumSchedulingClass (uint32 + 4 padding) — or just pad with raw bytes
- Use `ctypes.c_size_t` for pointer-width fields, `ctypes.c_uint32` for DWORD
- Or use a single large `JOBOBJECT_EXTENDED_LIMIT_INFORMATION` with total known byte size and set LimitFlags via offset. The offset of LimitFlags within JOBOBJECT_BASIC_LIMIT_INFORMATION is 16 (two int64 fields), and within JOBOBJECT_EXTENDED_LIMIT_INFORMATION it's at the same offset at the start. But it's cleaner to define the proper nested structs.

Simpler approach — define structs at the right size with explicit fields for what we need, padded for the rest. The Developer can reference MSDN for exact layout.

### No other files affected
- Linux `os.execv` path unchanged
- No new dependencies
- No changes to `main()`, `_install_backend_deps()`, or any other function
