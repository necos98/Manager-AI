## Implementation Plan: Command Injection Fix (3-Layer Defense)

### Files Changed
- `backend/app/schemas/project.py` — add pydantic validator on `shell`
- `backend/app/services/terminal_service.py` — spawn-site guard + WSL resolution
- `backend/tests/test_terminals_wsl.py` — new shell injection test

### Step 1: Pydantic validator on `shell` (API boundary)
**File**: `backend/app/schemas/project.py`

Add `@field_validator("shell")` to both `ProjectCreate` and `ProjectUpdate`. Skip if None (optional field). Reject if value contains any of: `'`, `"`, `` ` ``, `$`, `;`, `|`, `&`, `\n`, `\r`. Use simple char-class regex or set membership. Raise `ValueError` with descriptive message.

Existing `shell: str | None = None` field at lines 21/36 stays unchanged — validator runs for any non-None value.

### Step 2: Spawn-site validation guard
**File**: `backend/app/services/terminal_service.py`, after line 118

Add char-class check after `shell_to_use = shell or DEFAULT_SHELL`:
```python
_shell_bad_chars = re.compile(r"[\'\"`$;|&\n\r]")
if _shell_bad_chars.search(shell_to_use):
    raise ValueError(f"shell contains unsafe characters: {shell_to_use!r}")
```

Covers all call paths — API, `MANAGER_AI_SHELL` env var, programmatic callers (pipeline_run_service.py, routers/terminals.py). Defense-in-depth behind Layer 1.

### Step 3: Resolve `wsl.exe` via `shutil.which()` in WSL path
**File**: `backend/app/services/terminal_service.py`, line 138

Replace `shell_to_use` with `shutil.which("wsl.exe")` for WSL spawn:
```python
if use_wsl_distro:
    wsl_exe = shutil.which("wsl.exe")
    if wsl_exe is None:
        raise ValueError("wsl.exe not found on PATH, cannot start WSL terminal")
    pty.spawn(f'"{wsl_exe}" -d {wsl_distro}', cwd=spawn_cwd)
```

This removes attacker-controlled `shell` value from the WSL command string entirely. Import `shutil` at top of terminal_service.py (not yet imported there).

Non-WSL path (line 140) is already protected by Layer 2 validation.

### Step 4: Add shell injection test
**File**: `backend/tests/test_terminals_wsl.py`, after `test_service_create_rejects_injection`

New test `test_service_create_rejects_shell_injection` — same pattern as existing wsl_distro test at line 113:
- monkeypatch PTY with fake
- Call `svc.create()` with `shell` containing `"` (e.g. `cmd" /c "rm -rf /`)
- Assert `ValueError` raised
- Test at least one WSL shell value and one non-WSL shell value with bad chars

### Edge Cases
- `shell_to_use = DEFAULT_SHELL` from env var: Layer 2 catches at spawn site
- `shutil.which()` returns None: hard fail with ValueError (WSL unavailable)
- `shell=None` in pydantic validator: skip validation (optional field)
- Non-WSL path doesn't need special handling — Layer 2 validation already guards it

### Build Order
Steps 1-3 are independent, any order works. Step 4 after 1-3 (tests validate new behavior).