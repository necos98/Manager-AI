# WSL Setup

Manager AI runs on Windows. This guide explains how to work on projects that live inside a WSL (Windows Subsystem for Linux) distro without installing the backend or Claude Code CLI on Windows.

## Architecture

```
Windows host                         WSL distro (e.g. Ubuntu)
  ├── Manager AI backend (:8000)       ├── bash PTY (spawned by wsl.exe)
  ├── Manager AI frontend              ├── cwd: /mnt/c/... or /home/...
  └── wsl.exe -d <distro>  ─────────►  └── claude CLI  ──► http MCP back to Windows
```

- **Only Claude Code** is installed inside WSL.
- Manager AI on Windows spawns terminals via `wsl.exe`. The same PTY that drives cmd.exe or PowerShell drives bash inside WSL — no extra transport.
- The terminal router translates the project's Windows path to a POSIX path (`C:\foo\bar` → `/mnt/c/foo/bar`), injects env vars with bash `export`, and computes `MANAGER_AI_BASE_URL` at runtime from `ip route show default` so each WSL session reaches the Windows host's current IP.

## One-time setup

### 1. Install Claude Code inside the distro

```bash
wsl -d Ubuntu
# inside WSL:
curl -fsSL https://claude.ai/install.sh | bash
command -v claude   # sanity check — must print a path
```

### 2. MCP server registration (automatic)

Every WSL terminal Manager AI spawns now re-registers the MCP server `ManagerAi` against the current `$MANAGER_AI_BASE_URL` automatically. Nothing to do. The registration is idempotent (remove + add, silenced), so a changed WSL2 gateway IP still lands on a working entry.

If you want to check it:

```bash
claude mcp list
# ManagerAi: http://172.x.x.1:8000/mcp/ (HTTP) - ✓ Connected
```

If `claude` is not yet installed in the distro, the auto-registration is a silent no-op — finish step 1 and open a new terminal.

## Per-project configuration

In the Manager AI UI, open **Project Settings** and set:

- **Terminal Shell**: `WSL`
- **WSL Distro** (shown only when WSL is detected): e.g. `Ubuntu-22.04`. Leave on *Default distro* to use Windows' default.

The project path can be either a Windows path (`C:\dev\myproj`) or a WSL path pasted as a UNC path (`\\wsl.localhost\Ubuntu\home\you\myproj`). The router translates both.

## What you will see in a spawned terminal

```
$ cd /mnt/c/dev/myproj
$ export MANAGER_AI_TERMINAL_ID=… && export MANAGER_AI_ISSUE_ID=… && export MANAGER_AI_PROJECT_ID=…
$ export MANAGER_AI_BASE_URL="http://$(ip route show default | awk '{print $3}'):8000"
$ echo "$MANAGER_AI_BASE_URL"
http://172.x.x.1:8000
$ curl "$MANAGER_AI_BASE_URL/api/system/info"
{"platform":"Windows","wsl_available":true, …}
```

From here `claude` can reach the Manager AI MCP over HTTP.

## Troubleshooting

- **`curl` to `$MANAGER_AI_BASE_URL` times out.** The Windows firewall may be blocking inbound connections from the WSL interface. Allow TCP 8000 on the profile named something like *vEthernet (WSL)*. Alternatively, enable mirrored networking in `%USERPROFILE%\.wslconfig`:
  ```ini
  [wsl2]
  networkingMode=mirrored
  ```
  and restart WSL with `wsl --shutdown`. With mirrored networking `localhost:8000` works directly.
- **`command not found: claude`.** The CLI is not installed inside the distro you selected. Re-run the install command from step 1 *inside that distro*.
- **WSL1 distros:** `ip route show default` prints the Windows gateway, so the runtime resolution works. WSL2 is still recommended for performance.
- **`docker-desktop` distros appear nowhere in the picker.** Intentional — they are filtered out by `wsl_support.list_wsl_distros` because they are not user-runnable.
- **I changed my distro's IP / restarted WSL.** No action needed. The IP is resolved fresh for every new terminal via `ip route show default`.

## Non-goals

- No support for running the Manager AI **backend** itself inside WSL. Keep it on Windows.
- No automatic install of the `claude` CLI. See step 1.
- UNC paths (`\\wsl.localhost\...`) work via drvfs but are slow for large repos and have quirky file-watcher behaviour. Prefer keeping project sources on the Linux filesystem (`/home/...`) and letting the translator map them.
