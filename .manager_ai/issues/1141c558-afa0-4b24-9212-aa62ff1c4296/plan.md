## Implementation Plan: URL quotation in shell commands

### Overview

Add `quote_url_for_shell()` helper to `wsl_support.py` and apply it to 6 vulnerable `pty.write()` sites across `terminals.py` and `projects.py`. No new dependencies. No behavioral changes — only quoting mechanism changes.

---

### Step 1: Add `quote_url_for_shell()` helper to `wsl_support.py`

**File:** `backend/app/services/wsl_support.py`

Add this function:

```python
import shlex

def quote_url_for_shell(url: str, is_wsl: bool) -> str:
    """Quote a URL for safe insertion into a shell command.

    - is_wsl=True  → single-quoted via shlex.quote() for bash
    - is_wsl=False → double-quoted for cmd.exe
    """
    if is_wsl:
        return shlex.quote(url)
    # cmd.exe strips outer double quotes from arg parsing,
    # preventing space/&/| splitting
    return f'"{url}"'
```

**Rationale:** `wsl_support.py` is already imported by both `terminals.py` and `projects.py`. Adding `shlex` to its imports is clean — keeps quoting logic in one place. `shlex` is stdlib, no new dependency.

---

### Step 2: Apply helper to `terminals.py` (4 sites)

**File:** `backend/app/routers/terminals.py`

**Import change (line 28):**
```
from app.services.wsl_support import get_host_ip_for_wsl, is_wsl_shell, win_to_wsl_path
```
→
```
from app.services.wsl_support import get_host_ip_for_wsl, is_wsl_shell, quote_url_for_shell, win_to_wsl_path
```

**Site A — create_terminal WSL export (lines 146-149):**
```python
# BEFORE:
pty.write(
    f'export MANAGER_AI_BASE_URL='
    f'"http://{host_ip}:{port}"\r\n'
)
# AFTER:
pty.write(
    f'export MANAGER_AI_BASE_URL='
    f'{quote_url_for_shell(f"http://{host_ip}:{port}", is_wsl=True)}\r\n'
)
```

**Site B — create_terminal WSL localhost fallback (lines 151-154):**
```python
# BEFORE:
pty.write(
    f'export MANAGER_AI_BASE_URL='
    f'"http://localhost:{port}"\r\n'
)
# AFTER:
pty.write(
    f'export MANAGER_AI_BASE_URL='
    f'{quote_url_for_shell(f"http://localhost:{port}", is_wsl=True)}\r\n'
)
```

**Site C — create_ask_terminal WSL export (lines 291-294):**
Same pattern as Site A, but in create_ask_terminal.

**Site D — create_ask_terminal WSL localhost fallback (lines 296-299):**
Same pattern as Site B, but in create_ask_terminal.

---

### Step 3: Apply helper to `projects.py` (2 sites)

**File:** `backend/app/routers/projects.py`

**Import change (line 21):**
```
from app.services.wsl_support import get_host_ip_for_wsl, is_wsl_shell, win_to_wsl_path
```
→
```
from app.services.wsl_support import get_host_ip_for_wsl, is_wsl_shell, quote_url_for_shell, win_to_wsl_path
```

**Site E — WSL claude mcp add (lines 477-480):**
```python
# BEFORE:
pty.write(
    "claude mcp remove ManagerAi 2>/dev/null; "
    f'claude mcp add ManagerAi --transport http "{url}"\r\n'
)
# AFTER:
pty.write(
    "claude mcp remove ManagerAi 2>/dev/null; "
    f"claude mcp add ManagerAi --transport http {quote_url_for_shell(url, is_wsl=True)}\r\n"
)
```
Note: Command becomes f-string (inner quotes removed, function wraps in shlex.quote).

**Site F — cmd.exe claude mcp add (lines 483-486):**
```python
# BEFORE:
pty.write(
    "claude mcp remove ManagerAi 2>nul & "
    f'claude mcp add ManagerAi --transport http {url}\r\n'
)
# AFTER:
pty.write(
    "claude mcp remove ManagerAi 2>nul & "
    f"claude mcp add ManagerAi --transport http {quote_url_for_shell(url, is_wsl=False)}\r\n"
)
```

---

### Step 4: Add tests

**New file:** `backend/tests/test_url_quoting.py`

Test cases:
1. `quote_url_for_shell("http://192.168.1.1:8000/mcp/", is_wsl=True)` → `'http://192.168.1.1:8000/mcp/'` (shlex.quote adds single quotes)
2. `quote_url_for_shell("http://192.168.1.1:8000/mcp/", is_wsl=False)` → `"http://192.168.1.1:8000/mcp/"` (double-quote wrapped)
3. URL with shell metacharacters: `quote_url_for_shell("http://x;rm -rf /:8000/", is_wsl=True)` → wrapped in single quotes by shlex, metacharacters inert
4. URL with spaces: `quote_url_for_shell("http://x y:8000/", is_wsl=True)` → properly quoted
5. Edge: empty URL returns `''` for WSL, `'""'` for cmd.exe

---

### Files changed (summary)

| File | Action |
|------|--------|
| `backend/app/services/wsl_support.py` | Add `import shlex` + `quote_url_for_shell()` function |
| `backend/app/routers/terminals.py` | Add import + 4 quoting fixes |
| `backend/app/routers/projects.py` | Add import + 2 quoting fixes |
| `backend/tests/test_url_quoting.py` | New test file |

### Acceptance verification

1. Backend code compiles (imports, no syntax errors)
2. `pytest tests/test_url_quoting.py -v` passes all test cases
3. Backend starts: `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` starts without errors
4. No changes to existing `shlex.quote()` usage for `cd` commands or `_inject_env_vars()`
