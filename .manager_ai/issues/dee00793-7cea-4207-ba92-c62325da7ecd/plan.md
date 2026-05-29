# Implementation Plan: Pipeline PTY

## Files

- **Modify:** `backend/app/services/pipeline_run_service.py` — riscrivere `_execute()` e `_run_step()` per usare PTY reali
- **Modify:** `backend/app/services/agent_service.py` — cambiare `terminal_command` in `DEFAULT_AGENTS`

## Tasks

### Task 1: Change DEFAULT_AGENTS terminal_command

**File:** `backend/app/services/agent_service.py:7-74`

Cambiare `terminal_command` per tutti e 6 gli agenti da `claude -p "..."` a:
```
claude --dangerously-skip-permissions "/run-pipeline $issue_id"
```

Tutti gli agenti usano lo stesso comando base. Il ruolo specifico arriva via `MANAGER_AI_AGENT_INTENT`.

---

### Task 2: Rewrite `_run_step()` to use PTY instead of subprocess

**File:** `backend/app/services/pipeline_run_service.py:262-318`

Sostituire completamente `_run_step()`. Invece di `asyncio.create_subprocess_shell` + `push_output`:

```python
async def _run_step(
    self,
    term_id: str,
    agent_name: str,
    intent: str,
    command: str,
    project_path: str,
    run_id: str,
    issue_id: str,
) -> bool:
    import platform
    from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

    pty = terminal_service.get_pty(term_id)

    # Create session so we can await pty_dead
    session = TerminalSession()
    _sessions[term_id] = session
    _ensure_reader(term_id, terminal_service)

    is_windows = platform.system() == "Windows"

    # Inject env vars in shell dialect
    if is_windows:
        pty.write(f"set MANAGER_AI_AGENT_NAME={agent_name}\r\n")
        pty.write(f"set MANAGER_AI_AGENT_ROLE={agent_name}\r\n")
        pty.write(f"set MANAGER_AI_AGENT_INTENT={intent}\r\n")
        pty.write(f"set MANAGER_AI_ISSUE_ID={issue_id}\r\n")
        pty.write(f"set MANAGER_AI_RUN_ID={run_id}\r\n")
        # Inject command + shell exit so PTY closes when done
        pty.write(f"{command}\r\n")
        pty.write(f"exit\r\n")
    else:
        import shlex
        pty.write(f"export MANAGER_AI_AGENT_NAME={shlex.quote(agent_name)}\n")
        pty.write(f"export MANAGER_AI_AGENT_ROLE={shlex.quote(agent_name)}\n")
        pty.write(f"export MANAGER_AI_AGENT_INTENT={shlex.quote(intent)}\n")
        pty.write(f"export MANAGER_AI_ISSUE_ID={shlex.quote(issue_id)}\n")
        pty.write(f"export MANAGER_AI_RUN_ID={shlex.quote(run_id)}\n")
        # Inject command + shell exit
        pty.write(f"{command}; exit\n")

    # Wait for PTY process to exit
    await session.pty_dead.wait()

    return session.pty_died_naturally
```

**Rimuovere:**
- `stream_output()` coroutine interna
- `stream_task` e `asyncio.wait_for`
- `proc.kill()` e timeout logic (PTY non supporta timeout diretto — se serve lo aggiungiamo dopo)

---

### Task 3: Change `_execute()` to use `terminal_service.create()` (real PTY)

**File:** `backend/app/services/pipeline_run_service.py:152-229`

Cambiare la creazione del terminale:

```python
# Prima (line 154-159):
term = await terminal_service.create_log(
    project_id=project_id,
    issue_id="",
    project_path=project_path,
    label=f"{agent_name} (step {i + 1}/{len(steps)})",
)

# Dopo:
term = terminal_service.create(
    issue_id=run.issue_id,
    project_id=project_id,
    project_path=project_path,
)
```

Rimuovere tutte le chiamate a `await terminal_service.destroy_log(term_id)` — il PTY si auto-pulisce quando il processo esce (il reader chiama `mark_closed()` a EOF).

---

### Task 4: Add imports and verify

**File:** `backend/app/services/pipeline_run_service.py:1-22`

Aggiungere import:
```python
from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader
```

(Anche se l'import sara' fatto inline in `_run_step()` per evitare circular import, verificare che funzioni.)

---

### Task 5: Test and reseed

1. Riavviare il backend
2. Cancellare la pipeline esistente (UI o API)
3. Riavviare il backend per reseedare agenti + pipeline con i nuovi DEFAULT_AGENTS
4. Creare una issue di test
5. Avviare la pipeline e verificare che:
   - Il terminale appaia nella UI
   - L'output di Claude sia visibile in tempo reale
   - Lo step passi a COMPLETED quando Claude esce
   - La pipeline completi tutti gli step
