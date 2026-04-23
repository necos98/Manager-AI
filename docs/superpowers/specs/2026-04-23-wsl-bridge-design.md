# WSL Bridge Integration — Design

**Date:** 2026-04-23
**Status:** Proposed

## Problem

Users on Windows keep projects inside a WSL distro (typically Ubuntu). Manager AI runs on Windows and cannot reach Linux-side tooling. Forcing users to install Manager AI backend inside WSL doubles install burden and duplicates state (DB, settings, LanceDB). Claude Code CLI is Linux-native for these projects — it must run inside WSL, not on Windows.

Current state:
- `wsl.exe` already appears in the shell dropdown of project settings (`frontend/src/features/projects/components/project-settings-dialog.tsx:30`).
- Selecting it today is **broken**: env injection in `backend/app/routers/terminals.py:167-193` uses `set VAR=val` (cmd.exe syntax) when `platform.system() == "Windows"`, which fails inside the bash process spawned by `wsl.exe`.
- No Windows → WSL path translation. If `project.path` is `C:\foo\bar`, the bash shell starts there but user scripts relying on POSIX paths fail.
- No way for Claude Code inside WSL to discover the Manager AI MCP endpoint. WSL2 network is a separate subnet; `localhost` does not always reach the Windows host (depends on `networkingMode`).
- No UI hint that WSL is available, no per-project distro choice.

## Goal

Let Windows users keep Manager AI on Windows, keep project code in WSL, and run Claude Code in WSL — with Manager AI driving the loop via `wsl.exe` terminals and a reachable MCP endpoint. No backend inside Linux. No duplicate install.

## Non-goals

- Supporting WSL1 (no mirrored gateway, unusual). Detect and warn only.
- Treating `\\wsl.localhost\...` UNC paths as first-class project roots. They work by accident via drvfs; performance and file-watcher behavior are poor. Document as unsupported; recommend `wsl.exe` shell + native Linux paths instead.
- Automatic `claude` CLI install inside WSL. Detect presence, guide user to installer.
- Changing how non-WSL users configure shells. Existing cmd/powershell/bash flows untouched.

## Architecture

### Split of responsibilities

```
┌───────────────────────── Windows ──────────────────────────┐
│                                                            │
│  Manager AI backend (FastAPI)                              │
│    ├─ REST + MCP server  http://<host>:8000                │
│    ├─ TerminalService (winpty)                             │
│    └─ spawns:  wsl.exe -d <distro>                         │
│                                                            │
│  Manager AI frontend (Vite)                                │
│                                                            │
└────────────────────────────────────────────────────────────┘
                          │  PTY stdio
                          ▼
┌────────────────────── WSL distro ──────────────────────────┐
│                                                            │
│  bash (spawned by wsl.exe)                                 │
│    ├─ cwd = /mnt/c/...  or  /home/user/...                 │
│    ├─ env: MANAGER_AI_* (exported via bash syntax)         │
│    ├─ MANAGER_AI_BASE_URL = http://<host_ip>:8000          │
│    └─ claude CLI → http MCP → Manager AI on Windows        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Key decisions

**1. Detect WSL shell by basename, not by path.**
`is_wsl_shell(shell) = basename(shell).lower() == "wsl.exe"`. Works for the default `C:\Windows\System32\wsl.exe`, Store-installed wsl, and user overrides.

**2. Path translation is a pure function.**
`win_to_wsl_path("C:\\foo\\bar") == "/mnt/c/foo/bar"`. UNC `\\wsl.localhost\Ubuntu\home\u\p` → `/home/u/p` (drop first 4 backslash-delimited segments: empty, empty, `wsl.localhost`, distro). Non-Windows paths pass through.

**3. Env injection uses the shell's dialect, not the host platform's.**
Today: branch on `platform.system() == "Windows"` → `set` vs `export`. New rule: if `is_wsl_shell(shell)` → always `export` regardless of host. Keep existing Windows branch for cmd/powershell (they accept `set`). Git Bash on Windows is the existing quiet bug (also needs `export`) but out of scope — call it out in code comment.

**4. MCP endpoint discovery uses a runtime bash expression.**
Static IP resolution at terminal-create time is fragile (WSL2 gateway changes on restart). Export:
```bash
export MANAGER_AI_BASE_URL="http://$(ip route show default | awk '{print $3}'):8000"
```
This resolves on each new terminal. If `networkingMode=mirrored` is set in `.wslconfig`, `localhost:8000` works directly — optional optimization later. For mirrored mode detection we'd have to shell into WSL to read `.wslconfig` parsing; skip for v1.

**5. Distro selection is per-project, optional, nullable.**
New column `Project.wsl_distro: str | None`. If null, `wsl.exe` uses the system default distro. If set, spawn as `wsl.exe -d <distro>`. No global default — each project picks.

**6. System capabilities exposed via `GET /api/system/info`.**
Single endpoint, cached client-side via React Query. Lists distros, WSL availability, platform. Frontend conditionally shows UI. Missing endpoint = old backend = UI hides WSL features (forward-compatible).

**7. MCP registration is a one-shot terminal startup command.**
When user first spawns a WSL terminal in a project, inject:
```bash
claude mcp add manager-ai --transport http "$MANAGER_AI_BASE_URL/mcp" 2>/dev/null || true
```
Idempotent on claude's side (`add` errors if exists, we swallow). Runs only when `is_wsl && has_claude` (soft-detected via `command -v claude`).

### Spawn mechanics

`winpty.PTY.spawn(command_line, cwd=...)` accepts a single command line string. For distro-specific spawn:
- Shell field in DB stays as-is (`C:\Windows\System32\wsl.exe`).
- New `wsl_distro` field, if set, gets appended: the effective command line is `wsl.exe -d <distro>`.
- `terminal_service.create` becomes distro-aware via a new optional parameter.

Verify during Task 4: if winpty signature requires separate `appname`+`cmdline`, adjust. Based on current code (`backend/app/services/terminal_service.py:116`), it passes a single string. Assume that holds.

### Non-breaking guarantees

| Scenario | Change |
|----------|--------|
| cmd / powershell / pwsh / Git Bash on Windows | None. Branch `is_wsl_shell` is false. |
| Native Linux / macOS user | None. `IS_WINDOWS` path unchanged. `wsl.exe` not on PATH, `wsl_available=false`. |
| Existing user with `shell=wsl.exe` already set | **Fixes currently-broken injection.** Strict improvement, no regression. |
| DB migration | ADD COLUMN `wsl_distro VARCHAR(100) NULL`. No default, no backfill, no index. |
| `/api/system/info` missing from old clients | Additive endpoint; old frontend ignores. |

## Risk

- **WSL1 distros:** `ip route show default` prints the Windows gateway directly; host is reachable at the gateway. Actually works. No special handling needed, just document.
- **Corporate WSL disabled:** `wsl.exe` may exist but fail. `list_wsl_distros` wraps `subprocess.run` with 5 s timeout; on failure → `wsl_available=false`. UI hides.
- **`docker-desktop*` distros:** listed by `wsl.exe -l -q` but not user-usable. Filter them out in `list_wsl_distros`.
- **UTF-16 LE output of wsl.exe:** `wsl.exe -l -q` writes UTF-16 LE with BOM on Windows. Decode explicitly, don't rely on default locale.
- **Claude not installed in WSL:** soft sentinel detection (`__MANAGER_AI_NO_CLAUDE__`) via PTY read-back. Non-blocking. Toast in UI linking to install docs. Deferred to Task 12 — nice-to-have.

## Memory to record on completion

- Decision: "WSL support = Claude Code in WSL + Manager AI on Windows; no backend in Linux." Reason: avoids dual install and state duplication.
- Pattern: "Env injection must follow shell dialect (`is_wsl_shell` → bash `export`), not host platform." Reason: prior bug where `set` ran against bash silently failed.
- Gotcha: "`wsl.exe -l -q` outputs UTF-16 LE; always decode explicitly." Reason: default-locale decode garbles distro names on non-English Windows.
