## Command Injection via shell_to_use in WSL Terminal Spawn

### Description

`Project.shell` (DB field, settable via API) and `MANAGER_AI_SHELL` env var flow directly into `pty.spawn()` command string with zero validation. An attacker who controls `Project.shell` can inject arbitrary commands via embedded quotes or shell metacharacters.

### Scope

- **In scope**: `terminal_service.py` — validate `shell_to_use` before spawn. `schemas/project.py` — add pydantic validator on `shell` field. `project_service.py` — add validation on `shell` during project update.
- **Out of scope**: Other env vars, other terminal service code paths, other DB fields.

### Constraints

- Existing terminal functionality must work for all valid shells (`cmd.exe`, `powershell.exe`, `wsl.exe`, `bash`, `pwsh`, etc.)
- WSL distro validation must remain intact
- Non-WSL code path (line 140) must also be protected
- No breaking changes to `Project` serialization or API responses

### Acceptance Criteria

1. `shell_to_use` containing quotes (`'`, `"`), backticks, `$()`, `;`, `|`, `&`, `\n` is rejected at API boundary (pydantic validator) AND at spawn site (defense-in-depth)
2. WSL path resolves `wsl.exe` via `shutil.which()` instead of trusting user-provided `shell` value
3. All existing terminal creation tests pass (WSL and non-WSL)
4. New test covering injection via `shell` parameter is added in `test_service_create_rejects_injection`
5. Non-WSL spawn path also validates `shell_to_use` before passing to `CreateProcess`/`pty.spawn`

### Non-Goals

- No redesign of terminal service architecture
- No changes to terminal WebSocket streaming, resize, or kill flows
- No changes to MCP server or agent pipeline code
- No changes to frontend terminal UI (xterm.js)
