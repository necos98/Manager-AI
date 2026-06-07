## Problem

URLs containing `host_ip` or `port` flow unquoted (or double-quote-wrapped only) into `pty.write()` calls in `terminals.py` and `projects.py`. A malicious or manipulated `host_ip` or `port` can inject shell metacharacters — backticks, `$()`, `;`, `&`, `|` — leading to arbitrary command execution.

## Scope

**In scope:**
- All `pty.write()` call sites in `terminals.py` where a constructed URL is passed as a shell command argument
- All `pty.write()` call sites in `projects.py` where `url` (containing `host_ip` + `port`) is passed as a shell command argument
- Both shell dialects that appear in the codebase: bash (WSL) and cmd.exe (Windows)

**Out of scope (explicitly excluded):**
- Non-URL shell arguments (already handled by `shlex.quote()` in existing `cd` commands)
- The `shell_to_use` path injection (already fixed by the 3-layer defense in memory `0c7ad026`)
- `_inject_env_vars()` in `terminals.py` (already handles quoting correctly)
- Any other `pty.write()` call sites not involving URL construction

## Affected code locations

Six sites across two files where constructed URLs flow into `pty.write()`:

| # | File | Lines | Command pattern | Shell | Risk |
|---|------|-------|-----------------|-------|------|
| 1 | `terminals.py` | 146-149 | `export MANAGER_AI_BASE_URL="http://{host_ip}:{port}"` | bash (WSL) | Double quotes still expand `$`, backticks, `\` |
| 2 | `terminals.py` | 151-154 | Same with `localhost` fallback | bash (WSL) | Same |
| 3 | `terminals.py` | 291-294 | Same in `create_ask_terminal` | bash (WSL) | Same |
| 4 | `terminals.py` | 296-299 | Same with `localhost` fallback | bash (WSL) | Same |
| 5 | `projects.py` | 477-480 | `claude mcp add ManagerAi --transport http "{url}"` | bash (WSL) | Double quotes |
| 6 | `projects.py` | 483-486 | `claude mcp add ManagerAi --transport http {url}` | cmd.exe | Zero quoting |

## Requirements

### R1: URL quotation helper

The codebase must provide a single function that quotes a URL for safe insertion into a shell command. The function must:
- Accept a URL string and a shell dialect indicator (bash vs cmd.exe)
- For bash/WSL: produce a single-quoted string via `shlex.quote()` — this is the existing project pattern (see `_inject_env_vars()` and `cd` commands)
- For cmd.exe: wrap the URL in double quotes — cmd.exe strips outer double quotes from argument parsing, preventing space/`&`/`|` splitting
- Be importable from both `terminals.py` and `projects.py`

### R2: Apply to all affected sites

Apply the helper from R1 to each of the 6 sites listed above. No URL must flow unquoted or double-quote-only into `pty.write()`.

### R3: No regression

Fixing URL quoting must not break existing terminal initialization or MCP installation behavior. The exact same URLs must be produced — only the quoting mechanism changes.

## Acceptance criteria

1. A `quote_url_for_shell(url, is_wsl)` function exists and is importable
2. All 6 sites in terminals.py and projects.py use it
3. `shlex.quote()` is used for bash/WSL sites — not raw f-strings with double quotes
4. Double-quote wrapping is used for cmd.exe sites — not raw unfquoted f-strings
5. Code compiles / imports without errors
6. Tests pass
7. Backend starts without errors

## Non-goals

- No changes to existing `shlex.quote()` usage for `cd` commands or `_inject_env_vars()`
- No changes to the 3-layer `shell_to_use` defense
- No new validation or sanitization of `host_ip` / `port` values themselves
- No changes outside `terminals.py` and `projects.py`
- No new dependencies

## Constraints

- The helper must handle the shell dialect split the same way `_inject_env_vars()` does: `is_wsl` boolean parameter determines bash vs cmd.exe quoting
- Must integrate with the existing `shlex` import pattern in `projects.py` (already imports `shlex` for `shlex.quote(cwd)`)
- `terminals.py` does not currently import `shlex` — the helper's location should either be in a shared module or the import should be added
