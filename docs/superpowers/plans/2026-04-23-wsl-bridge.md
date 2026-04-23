# WSL Bridge Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Windows users keep their projects inside a WSL distro and drive Claude Code from Manager AI without installing the backend in Linux. Manager AI on Windows spawns terminals via `wsl.exe`, translates paths, injects bash-compatible env, and auto-discovers the Windows host IP for MCP reachability.

**Architecture:** New pure-function module `wsl_support.py` centralises detection, path translation, distro listing, and host IP probing. A new `/api/system/info` endpoint exposes capabilities to the frontend. `terminals.py` branches on `is_wsl_shell(shell)` and injects `export` + POSIX paths. A new nullable `Project.wsl_distro` column picks the distro. Frontend shows a conditional distro dropdown and an install hint. Every change is additive — users on cmd/powershell/bash/native-Linux are untouched.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, winpty, React 18, Vite, TanStack Query, shadcn/ui.

Reference spec: `docs/superpowers/specs/2026-04-23-wsl-bridge-design.md`.

---

## File Structure

### Backend
- **Create** `backend/app/services/wsl_support.py` — `is_wsl_shell`, `win_to_wsl_path`, `list_wsl_distros`, `get_host_ip_for_wsl`, `wsl_available`.
- **Create** `backend/tests/test_wsl_support.py` — unit tests for path translation and detection.
- **Create** `backend/app/routers/system.py` — `GET /api/system/info`.
- **Create** `backend/app/schemas/system.py` — Pydantic `SystemInfoResponse`.
- **Modify** `backend/app/main.py` — register system router.
- **Modify** `backend/app/routers/terminals.py` — extract `_inject_env_vars` helper, add `is_wsl` branch in `create_terminal` and `create_ask_terminal`.
- **Create** `backend/tests/test_terminals_wsl.py` — verify WSL-shell injection emits `export` + POSIX paths.
- **Modify** `backend/app/models/project.py` — add `wsl_distro` column.
- **Modify** `backend/app/schemas/project.py` — expose `wsl_distro` on read/update.
- **Create** `backend/alembic/versions/xxxx_add_wsl_distro_to_project.py` — migration.
- **Modify** `backend/app/services/terminal_service.py` — accept optional `wsl_distro`, build command line with `-d <distro>`.

### Frontend
- **Create** `frontend/src/api/system.ts` — `getSystemInfo` + `useSystemInfo` hook.
- **Modify** `frontend/src/shared/types/index.ts` — add `wsl_distro?: string | null` to `Project`, `SystemInfo` type.
- **Modify** `frontend/src/features/projects/components/project-settings-dialog.tsx` — conditional WSL distro dropdown, install hint banner.
- **Modify** `frontend/src/features/projects/hooks.ts` (or local client) — pass `wsl_distro` on update.

### Docs
- **Modify** `CLAUDE.md` — add WSL bullet under Architecture → Terminal Service.
- **Create** `docs/wsl-setup.md` — short user guide (how to install Claude in WSL, config).

---

## Task 1: Create `wsl_support.py` utility module

**Files:**
- Create: `backend/app/services/wsl_support.py`
- Create: `backend/tests/test_wsl_support.py`

- [ ] **Step 1: Write failing tests first**

Create `backend/tests/test_wsl_support.py`:

```python
import pytest
from app.services.wsl_support import (
    is_wsl_shell,
    win_to_wsl_path,
)


class TestIsWslShell:
    def test_none(self):
        assert is_wsl_shell(None) is False

    def test_empty(self):
        assert is_wsl_shell("") is False

    def test_default_path(self):
        assert is_wsl_shell(r"C:\Windows\System32\wsl.exe") is True

    def test_lowercase(self):
        assert is_wsl_shell(r"c:\windows\system32\wsl.exe") is True

    def test_store_path(self):
        assert is_wsl_shell(r"C:\Program Files\WindowsApps\...\wsl.exe") is True

    def test_cmd_not_wsl(self):
        assert is_wsl_shell(r"C:\Windows\System32\cmd.exe") is False

    def test_bash_not_wsl(self):
        assert is_wsl_shell("/bin/bash") is False


class TestWinToWslPath:
    def test_drive_letter(self):
        assert win_to_wsl_path(r"C:\foo\bar") == "/mnt/c/foo/bar"

    def test_drive_letter_lowercase(self):
        assert win_to_wsl_path(r"d:\x\y") == "/mnt/d/x/y"

    def test_drive_root(self):
        assert win_to_wsl_path("C:\\") == "/mnt/c/"

    def test_unc_wsl_localhost(self):
        assert (
            win_to_wsl_path(r"\\wsl.localhost\Ubuntu\home\u\proj")
            == "/home/u/proj"
        )

    def test_unc_wsl_dollar(self):
        assert (
            win_to_wsl_path(r"\\wsl$\Ubuntu-22.04\home\u\proj")
            == "/home/u/proj"
        )

    def test_posix_passthrough(self):
        assert win_to_wsl_path("/home/user/proj") == "/home/user/proj"

    def test_empty(self):
        assert win_to_wsl_path("") == ""
```

Run: `cd backend && python -m pytest tests/test_wsl_support.py -v` — should fail with ImportError.

- [ ] **Step 2: Implement the module**

Create `backend/app/services/wsl_support.py`:

```python
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from functools import lru_cache


def is_wsl_shell(shell: str | None) -> bool:
    """True iff the shell path points at wsl.exe (any install location)."""
    if not shell:
        return False
    return os.path.basename(shell).lower() == "wsl.exe"


def win_to_wsl_path(path: str) -> str:
    """Translate a Windows path to its WSL equivalent.

    - ``C:\\foo\\bar``                       -> ``/mnt/c/foo/bar``
    - ``\\\\wsl.localhost\\Ubuntu\\home\\u`` -> ``/home/u``
    - ``\\\\wsl$\\Ubuntu\\home\\u``          -> ``/home/u``
    - POSIX or empty paths pass through unchanged.
    """
    if not path:
        return path
    if path.startswith("\\\\wsl.localhost\\") or path.startswith("\\\\wsl$\\"):
        # \\wsl.localhost\<distro>\<rest...>
        parts = path.split("\\")
        # parts = ['', '', 'wsl.localhost', '<distro>', '<rest...>']
        tail = parts[4:]
        return "/" + "/".join(tail)
    if len(path) >= 2 and path[1] == ":":
        drive = path[0].lower()
        rest = path[2:].replace("\\", "/").lstrip("/")
        return f"/mnt/{drive}/{rest}" if rest else f"/mnt/{drive}/"
    return path


@lru_cache(maxsize=1)
def wsl_available() -> bool:
    """True iff we're on Windows and wsl.exe is on PATH."""
    if platform.system() != "Windows":
        return False
    return shutil.which("wsl.exe") is not None


def list_wsl_distros() -> list[str]:
    """Return user-usable WSL distro names. Empty list if WSL unavailable or errors.

    ``wsl.exe -l -q`` outputs UTF-16 LE with BOM on Windows; decode explicitly.
    Filters out docker-desktop* distros which are not end-user runnable.
    """
    if not wsl_available():
        return []
    try:
        result = subprocess.run(
            ["wsl.exe", "-l", "-q"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if result.returncode != 0:
        return []
    # Try utf-16 first (Windows native), fall back to utf-8.
    try:
        text = result.stdout.decode("utf-16-le").lstrip("﻿")
    except UnicodeDecodeError:
        text = result.stdout.decode("utf-8", errors="replace")
    distros = [
        line.strip().replace("\x00", "")
        for line in text.splitlines()
        if line.strip()
    ]
    return [d for d in distros if not d.startswith("docker-desktop")]


def get_default_distro() -> str | None:
    """Return the default WSL distro name or None."""
    distros = list_wsl_distros()
    return distros[0] if distros else None


def get_host_ip_for_wsl() -> str | None:
    """Best-effort Windows host IP reachable from a WSL2 guest.

    Returning None signals the frontend/injector to fall back to a runtime
    bash expression (``ip route show default | awk '{print $3}'``) inside
    the terminal. That fallback always works.
    """
    # v1: always return None and rely on runtime resolution inside bash.
    # A future iteration can probe vEthernet (WSL) via `ipconfig` parsing.
    return None
```

- [ ] **Step 3: Run tests, confirm green**

```bash
cd backend && python -m pytest tests/test_wsl_support.py -v
```

All test cases pass.

---

## Task 2: System info endpoint

**Files:**
- Create: `backend/app/schemas/system.py`
- Create: `backend/app/routers/system.py`
- Modify: `backend/app/main.py`
- Create test in `backend/tests/test_routers_system.py`

- [ ] **Step 1: Schema**

`backend/app/schemas/system.py`:

```python
from pydantic import BaseModel


class SystemInfoResponse(BaseModel):
    platform: str
    wsl_available: bool
    distros: list[str]
    default_distro: str | None
    host_ip_for_wsl: str | None
```

- [ ] **Step 2: Router**

`backend/app/routers/system.py`:

```python
from __future__ import annotations

import platform

from fastapi import APIRouter

from app.schemas.system import SystemInfoResponse
from app.services.wsl_support import (
    get_default_distro,
    get_host_ip_for_wsl,
    list_wsl_distros,
    wsl_available,
)

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
async def system_info() -> SystemInfoResponse:
    return SystemInfoResponse(
        platform=platform.system(),
        wsl_available=wsl_available(),
        distros=list_wsl_distros(),
        default_distro=get_default_distro(),
        host_ip_for_wsl=get_host_ip_for_wsl(),
    )
```

- [ ] **Step 3: Mount router**

`backend/app/main.py` — add `from app.routers import system` and `app.include_router(system.router)` alongside the other router registrations.

- [ ] **Step 4: Test**

`backend/tests/test_routers_system.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_system_info_shape(monkeypatch):
    from app.routers import system as sysrouter

    monkeypatch.setattr(sysrouter, "wsl_available", lambda: True)
    monkeypatch.setattr(sysrouter, "list_wsl_distros", lambda: ["Ubuntu-22.04"])
    monkeypatch.setattr(sysrouter, "get_default_distro", lambda: "Ubuntu-22.04")
    monkeypatch.setattr(sysrouter, "get_host_ip_for_wsl", lambda: None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/system/info")
    assert r.status_code == 200
    body = r.json()
    assert body["wsl_available"] is True
    assert body["distros"] == ["Ubuntu-22.04"]
    assert body["default_distro"] == "Ubuntu-22.04"
    assert body["host_ip_for_wsl"] is None
    assert "platform" in body
```

Run: `cd backend && python -m pytest tests/test_routers_system.py -v`. Green.

---

## Task 3: Extract `_inject_env_vars` helper in `terminals.py`

Pure refactor, no behaviour change. Sets up Task 4.

**File:** `backend/app/routers/terminals.py`

- [ ] **Step 1: Introduce helper above `create_terminal` (near line 130)**

```python
def _inject_env_vars(
    pty,
    env: dict[str, str],
    *,
    is_wsl: bool,
) -> None:
    """Write env exports to the PTY using the shell dialect.

    - is_wsl=True  -> bash ``export`` (runs inside WSL).
    - is_wsl=False -> Windows ``set`` on Windows host, ``export`` on Linux/macOS host.
    """
    if is_wsl:
        set_cmd = "export"
    else:
        set_cmd = "set" if platform.system() == "Windows" else "export"
    line = " && ".join(f"{set_cmd} {k}={v}" for k, v in env.items())
    pty.write(line + "\r\n")
```

- [ ] **Step 2: Replace inline env-injection blocks**

In `create_terminal` (around `backend/app/routers/terminals.py:167-193`) and `create_ask_terminal` (around `:275-300`), replace the two copies of the set/export logic with calls to `_inject_env_vars(pty, env_vars, is_wsl=False)`. Keep `is_wsl=False` for now; Task 4 flips it.

- [ ] **Step 3: Run existing tests**

```bash
cd backend && python -m pytest tests/test_routers_terminals.py -v
```

No regressions — this task must not change observable behaviour.

---

## Task 4: Add `is_wsl` branch in terminal creation

**File:** `backend/app/routers/terminals.py`

- [ ] **Step 1: Import helpers**

```python
import shlex
from app.services.wsl_support import is_wsl_shell, win_to_wsl_path
```

- [ ] **Step 2: Compute `is_wsl` after spawning**

In `create_terminal`, after `service.create(...)` returns, before env injection:

```python
is_wsl = is_wsl_shell(project_shell)
if is_wsl:
    cwd_wsl = win_to_wsl_path(project_path)
    pty = service.get_pty(terminal["id"])
    pty.write(f"cd {shlex.quote(cwd_wsl)}\r\n")
```

- [ ] **Step 3: Route env through helper with `is_wsl`**

Change the env block:

```python
env_vars = {
    "MANAGER_AI_TERMINAL_ID": terminal["id"],
    "MANAGER_AI_ISSUE_ID": data.issue_id,
    "MANAGER_AI_PROJECT_ID": data.project_id,
}
# MANAGER_AI_BASE_URL: resolved inside bash for WSL, static for others.
if is_wsl:
    _inject_env_vars(pty, env_vars, is_wsl=True)
    pty.write(
        'export MANAGER_AI_BASE_URL='
        f'"http://$(ip route show default | awk \'{{print $3}}\'):'
        f'{os.environ.get("BACKEND_PORT", "8000")}"\r\n'
    )
else:
    env_vars["MANAGER_AI_BASE_URL"] = (
        f'http://localhost:{os.environ.get("BACKEND_PORT", "8000")}'
    )
    _inject_env_vars(pty, env_vars, is_wsl=False)
```

- [ ] **Step 4: Custom project variables — same pattern**

Pass `is_wsl` into the `_inject_env_vars` call for custom project variables. If the service returns variable values that include spaces or special chars, the current code is also unsafe on cmd — scope note only, do not fix here.

- [ ] **Step 5: `$project_path` replacement uses WSL path when WSL**

In the run-commands loop inside `create_terminal`:

```python
replacements = {
    "$issue_id": data.issue_id,
    "$project_id": data.project_id,
    "$project_path": win_to_wsl_path(project_path) if is_wsl else project_path,
}
```

- [ ] **Step 6: Apply identical changes to `create_ask_terminal`**

Same pattern: compute `is_wsl`, inject `cd`, route env via helper, translate `$project_path` in the ask brainstorm command.

- [ ] **Step 7: Test**

Create `backend/tests/test_terminals_wsl.py`:

```python
import pytest
from unittest.mock import MagicMock, patch

from app.routers.terminals import _inject_env_vars


def test_inject_env_vars_wsl_uses_export():
    pty = MagicMock()
    _inject_env_vars(pty, {"A": "1", "B": "2"}, is_wsl=True)
    pty.write.assert_called_once()
    written = pty.write.call_args.args[0]
    assert "export A=1" in written
    assert "export B=2" in written
    assert "set " not in written


def test_inject_env_vars_windows_non_wsl_uses_set():
    pty = MagicMock()
    with patch("app.routers.terminals.platform.system", return_value="Windows"):
        _inject_env_vars(pty, {"A": "1"}, is_wsl=False)
    written = pty.write.call_args.args[0]
    assert "set A=1" in written


def test_inject_env_vars_linux_host_uses_export():
    pty = MagicMock()
    with patch("app.routers.terminals.platform.system", return_value="Linux"):
        _inject_env_vars(pty, {"A": "1"}, is_wsl=False)
    written = pty.write.call_args.args[0]
    assert "export A=1" in written
```

For end-to-end verification add an integration test that mocks `service.create` + `get_pty`, sets `project.shell = "C:\\Windows\\System32\\wsl.exe"`, posts to `/api/terminals`, and asserts the sequence of `pty.write` calls contains `cd /mnt/c/...`, `export MANAGER_AI_...`, `export MANAGER_AI_BASE_URL="http://$(ip route...`.

Run: `cd backend && python -m pytest tests/test_terminals_wsl.py tests/test_routers_terminals.py -v`. Green.

---

## Task 5: Add `wsl_distro` column to `Project`

**Files:**
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/schemas/project.py`
- Create: `backend/alembic/versions/xxxx_add_wsl_distro_to_project.py`

- [ ] **Step 1: Model**

Add alongside existing `shell` column (`backend/app/models/project.py:18`):

```python
wsl_distro: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

- [ ] **Step 2: Schema**

In `backend/app/schemas/project.py`, add `wsl_distro: str | None = None` to the read and update/create schemas. Keep it optional.

- [ ] **Step 3: Generate migration**

```bash
cd backend && python -m alembic revision --autogenerate -m "add_wsl_distro_to_project"
```

- [ ] **Step 4: Verify migration content**

Open the generated file. Expected body:

```python
def upgrade() -> None:
    op.add_column("projects", sa.Column("wsl_distro", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "wsl_distro")
```

No unexpected ops. If autogenerate produced anything else (unrelated diffs from drift), prune them manually.

- [ ] **Step 5: Apply and test**

```bash
cd backend && python -m alembic upgrade head
python -m pytest tests/test_routers_projects.py -v
```

Existing tests still pass. Projects without `wsl_distro` set behave identically.

---

## Task 6: Distro-aware spawn in `TerminalService`

**File:** `backend/app/services/terminal_service.py`

- [ ] **Step 1: Accept `wsl_distro` parameter**

Add `wsl_distro: str | None = None` to `TerminalService.create` signature.

- [ ] **Step 2: Compose command line when WSL + distro set**

```python
from app.services.wsl_support import is_wsl_shell

shell_to_use = shell or DEFAULT_SHELL
if wsl_distro and is_wsl_shell(shell_to_use):
    # winpty.PTY.spawn takes a single command-line string on Windows.
    command_line = f'"{shell_to_use}" -d {wsl_distro}'
else:
    command_line = shell_to_use

pty = PTY(cols, rows)
pty.spawn(command_line, cwd=project_path)
```

Note: inspect the local `winpty.PTY.spawn` signature before committing. If it expects separate `appname` and `cmdline`, switch to that form. Verify with `python -c "from winpty import PTY; help(PTY.spawn)"` in the backend venv.

- [ ] **Step 3: Propagate from routers**

In both `create_terminal` and `create_ask_terminal`:

```python
project_obj = await db.get(Project, data.project_id)
project_shell = project_obj.shell if project_obj else None
project_wsl_distro = project_obj.wsl_distro if project_obj else None

terminal = service.create(
    issue_id=data.issue_id,
    project_id=data.project_id,
    project_path=project_path,
    shell=project_shell,
    wsl_distro=project_wsl_distro,
)
```

- [ ] **Step 4: Test**

Extend `backend/tests/test_terminals_wsl.py`:

```python
def test_service_create_appends_distro(monkeypatch):
    from app.services import terminal_service as ts
    spawns = []

    class FakePTY:
        def __init__(self, *a, **k): pass
        def spawn(self, cmd, cwd=None): spawns.append((cmd, cwd))
        def write(self, *a, **k): pass
        def close(self): pass
        def read(self, blocking=True): return ""
        def set_size(self, *a, **k): pass

    monkeypatch.setattr(ts, "PTY", FakePTY)
    svc = ts.TerminalService()
    svc.create(
        issue_id="i", project_id="p", project_path="C:\\x",
        shell=r"C:\Windows\System32\wsl.exe",
        wsl_distro="Ubuntu-22.04",
    )
    cmd, cwd = spawns[-1]
    assert "-d Ubuntu-22.04" in cmd
    assert "wsl.exe" in cmd
```

Run all backend tests: `cd backend && python -m pytest -v`. Green.

---

## Task 7: Frontend — system-info hook and types

**Files:**
- Create: `frontend/src/api/system.ts`
- Modify: `frontend/src/shared/types/index.ts`

- [ ] **Step 1: Types**

In `frontend/src/shared/types/index.ts`:

```typescript
export interface SystemInfo {
  platform: string;
  wsl_available: boolean;
  distros: string[];
  default_distro: string | null;
  host_ip_for_wsl: string | null;
}
```

Add to the existing `Project` type:

```typescript
wsl_distro?: string | null;
```

- [ ] **Step 2: API + hook**

`frontend/src/api/system.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import type { SystemInfo } from "@/shared/types";

export async function getSystemInfo(): Promise<SystemInfo | null> {
  const r = await fetch("/api/system/info");
  if (!r.ok) return null; // old backend without this endpoint
  return r.json();
}

export function useSystemInfo() {
  return useQuery({
    queryKey: ["system-info"],
    queryFn: getSystemInfo,
    staleTime: 5 * 60 * 1000,
  });
}
```

---

## Task 8: Frontend — conditional WSL distro dropdown

**File:** `frontend/src/features/projects/components/project-settings-dialog.tsx`

- [ ] **Step 1: Wire hook**

Inside the component:

```typescript
const { data: systemInfo } = useSystemInfo();
const isWslShell = form.shell.toLowerCase().endsWith("wsl.exe");
const showWslUi = !!systemInfo?.wsl_available && isWslShell;
```

- [ ] **Step 2: Extend form state**

```typescript
const [form, setForm] = useState({
  name: project.name,
  path: project.path,
  description: project.description || "",
  tech_stack: project.tech_stack || "",
  shell: project.shell || "__default__",
  wsl_distro: project.wsl_distro || "",
});
```

- [ ] **Step 3: Render dropdown + hint**

Immediately below the shell `Select`:

```tsx
{showWslUi && (
  <div className="space-y-2">
    <label className="text-sm font-medium">WSL Distro</label>
    <Select
      value={form.wsl_distro || "__default__"}
      onValueChange={(v) =>
        setForm({ ...form, wsl_distro: v === "__default__" ? "" : v })
      }
    >
      <SelectTrigger><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="__default__">Default distro</SelectItem>
        {systemInfo!.distros.map((d) => (
          <SelectItem key={d} value={d}>{d}</SelectItem>
        ))}
      </SelectContent>
    </Select>
    <p className="text-xs text-muted-foreground">
      Claude Code must be installed inside the selected WSL distro. See
      <a href="https://docs.claude.com/..." className="underline ml-1">
        install docs
      </a>.
    </p>
  </div>
)}
```

- [ ] **Step 4: Include `wsl_distro` in submit payload**

```typescript
updateProject.mutate(
  {
    ...form,
    shell: form.shell === "__default__" ? null : form.shell,
    wsl_distro: form.wsl_distro || null,
  },
  { onSuccess: () => onOpenChange(false) },
);
```

- [ ] **Step 5: Manual check**

1. `python start.py`.
2. Open a project, settings dialog.
3. Select shell `WSL`. Distro dropdown appears, populated.
4. Select `Ubuntu-22.04`, save. Reopen dialog — value persisted.
5. Switch shell back to cmd. Distro dropdown disappears. Saved distro retained in DB (harmless).

---

## Task 9: End-to-end manual verification

- [ ] **Step 1: Prereqs inside WSL distro**

```bash
wsl -d Ubuntu-22.04
# inside distro:
curl -fsSL https://claude.ai/install.sh | bash   # or user's preferred install
which claude   # must print a path
```

- [ ] **Step 2: Create project pointing at a WSL path**

In Manager AI frontend, create a project with path `\\wsl.localhost\Ubuntu-22.04\home\<user>\someproj` **or** a regular Windows path like `C:\dev\myproj`. Either should work. Shell = `WSL`, distro = `Ubuntu-22.04`.

- [ ] **Step 3: Spawn a terminal on an issue**

Expected sequence visible in the terminal:

```
cd /mnt/c/dev/myproj        # or /home/<user>/someproj
export MANAGER_AI_TERMINAL_ID=... && export MANAGER_AI_ISSUE_ID=...
export MANAGER_AI_BASE_URL="http://172.x.x.1:8000"
```

`echo $MANAGER_AI_BASE_URL` prints a reachable URL. `curl "$MANAGER_AI_BASE_URL/api/system/info"` returns JSON.

- [ ] **Step 4: Register MCP once and run Claude**

```bash
claude mcp add manager-ai --transport http "$MANAGER_AI_BASE_URL/mcp"
claude
```

Inside Claude Code, the Manager AI MCP tools show up (`get_issue_details`, `memory_search`, …).

- [ ] **Step 5: Regression check on non-WSL project**

Open a non-WSL project (shell = cmd or powershell). Spawn a terminal. Confirm `set VAR=...` is still used, env vars are set, nothing changed.

---

## Task 10: Docs + memory

- [ ] **Step 1: Update `CLAUDE.md`**

Under `Key Subsystems → Terminal Service`, append:

> **WSL support:** when a project's `shell` is `wsl.exe`, the terminal router translates `project.path` via `wsl_support.win_to_wsl_path`, issues a `cd` inside the PTY, and emits env vars with `export` rather than `set`. `MANAGER_AI_BASE_URL` is resolved at runtime inside bash via `ip route show default`. Optional `Project.wsl_distro` picks a specific distro (`wsl.exe -d <distro>`).

- [ ] **Step 2: Create `docs/wsl-setup.md`** — brief user guide:
  - When to use WSL shell.
  - Installing Claude Code inside the distro.
  - Registering the MCP once with `claude mcp add`.
  - Troubleshooting: WSL1 vs WSL2, firewall, mirrored networking tip.

- [ ] **Step 3: Record memories** (via `manager-ai-memories` skill or `memory_create` MCP):
  - Decision: "WSL support = Claude Code in WSL + Manager AI on Windows; no backend in Linux."
  - Pattern: "Env injection follows shell dialect (`is_wsl_shell` → `export`), not host platform."
  - Gotcha: "`wsl.exe -l -q` outputs UTF-16 LE; decode explicitly."

---

## Task 11 (optional, deferrable): Soft claude-presence check

Not required for v1 — ship without if time-boxed.

- [ ] Inject after `cd`: `command -v claude >/dev/null || echo "__MANAGER_AI_NO_CLAUDE__"`.
- [ ] In `_terminal_reader` (`backend/app/routers/terminals.py:50`) inspect buffered output for the sentinel once; if seen, strip it and emit an SSE/WebSocket event `claude_missing` via the event bus.
- [ ] Frontend toast listens for the event, shows install hint with a link. Once per session per terminal.

---

## Execution order

1. Tasks 1 → 2 → 3 → 4 (core backend, mergeable standalone).
2. Tasks 5 → 6 (DB column + spawn args).
3. Tasks 7 → 8 (frontend).
4. Task 9 (manual E2E).
5. Task 10 (docs, memories).
6. Task 11 only if bandwidth allows.

Each numbered task is a clean commit. Tasks 1–4 and 5–6 can be separate PRs.
