# Pipeline PTY: Replace headless subprocess with real PTY terminals

## Problem

`_run_step()` attualmente usa `asyncio.create_subprocess_shell()` (headless, no PTY) e streamma l'output in un "log terminal" virtuale (`create_log()` con `pty=None` e `asyncio.Queue`).

L'utente vuole che ogni step della pipeline giri in un vero terminale PTY, esattamente come il flusso "RUN ISSUE", con il comando:

```
claude --dangerously-skip-permissions "/run-pipeline $issue_id"
```

Questo e' il comportamento originale che e' stato cambiato.

## Infrastruttura esistente

`terminal_session.py` e' stato progettato esplicitamente per supportare terminali PTY-backed per la pipeline. Il docstring dice:

> Extracted from `app.routers.terminals` so that the pipeline executor can create PTY-backed command terminals and await completion without depending on the HTTP/WS layer.

`TerminalSession` ha:
- `pty_dead: asyncio.Event` — segnala quando il processo PTY esce
- `pty_died_naturally: bool` — True se il PTY e' uscito da solo (non killato)
- `reader_task` — il reader che bufferizza output e setta `pty_dead`

Il pipeline executor puo' awaitare `session.pty_dead.wait()` per sapere quando Claude ha finito.

## Design

### 1. `_execute()` — usare `terminal_service.create()` invece di `create_log()`

**Prima:**
```python
term = await terminal_service.create_log(
    project_id=project_id, issue_id="",
    project_path=project_path,
    label=f"{agent_name} (step {i + 1}/{len(steps)})",
)
```

**Dopo:**
```python
term = terminal_service.create(
    issue_id=run.issue_id,
    project_id=project_id,
    project_path=project_path,
)
```

Rimuovere tutte le chiamate a `destroy_log()` — il PTY si pulisce da solo via `mark_closed()` quando il processo esce.

### 2. `_run_step()` — riscrittura completa

Invece di `asyncio.create_subprocess_shell` + `push_output`:

1. Ottenere il PTY: `pty = terminal_service.get_pty(term_id)`
2. Creare `TerminalSession`: `session = TerminalSession()`, registrarla in `_sessions[term_id]`
3. Avviare il reader: `_ensure_reader(term_id, terminal_service)`
4. Iniettare env vars nel dialetto della shell (pattern da `routers/terminals.py:_inject_env_vars`):
   - Windows cmd.exe: `set MANAGER_AI_AGENT_NAME=...`
   - Linux/bash: `export MANAGER_AI_AGENT_NAME="..."`
   - Variabili: `MANAGER_AI_AGENT_NAME`, `MANAGER_AI_AGENT_ROLE`, `MANAGER_AI_AGENT_INTENT`, `MANAGER_AI_ISSUE_ID`, `MANAGER_AI_RUN_ID`
5. Iniettare il comando: `claude --dangerously-skip-permissions "/run-pipeline $issue_id"`
6. Appendere exit shell: `; exit` (bash) o `& exit` (cmd) cosi' la shell esce quando Claude finisce
7. Awaitare `session.pty_dead.wait()` — il reader setta questo Event quando il processo PTY esce
8. Ritornare `session.pty_died_naturally`

### 3. `DEFAULT_AGENTS` — cambiare `terminal_command`

**Prima (esempio SpecWriter):**
```
claude -p "Write a detailed specification for issue $issue_id. ..."
```

**Dopo (tutti gli agenti):**
```
claude --dangerously-skip-permissions "/run-pipeline $issue_id"
```

Il ruolo specifico dell'agente viene passato via `MANAGER_AI_AGENT_INTENT` (system_prompt). `/run-pipeline` usa il contesto dell'issue per determinare il lavoro da fare.

### 4. Nuovi import in `pipeline_run_service.py`

```python
import platform
from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader
```

## Note

- **Reseed**: Dopo il cambio di `DEFAULT_AGENTS`, le pipeline esistenti devono essere cancellate e il backend riavviato (memory `3e9f3825`).
- **`_safe_flush_session`**: Ora logga warning negli except (fixato in memoria `6aa7879a`).
- L'output del terminale e' visibile in UI via WebSocket esistente — il `TerminalPanel` frontend si connette al terminal_id dello step.
