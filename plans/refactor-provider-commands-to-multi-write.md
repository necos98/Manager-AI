# Refactoring: AgentProvider → comandi multi-write

## Perché

Oggi ogni metodo `build_*_command()` restituisce **una singola stringa** che viene scritta in una volta sola nel PTY:
```python
pty.write(provider.build_run_issue_command(id) + "\r\n")
```

Questo va bene per Claude Code (che ha slash command nativi), ma **forza Hermes a usare `-q`** (one-shot), impedendo interazioni multi-turn (es. fare domande via `ask_user_question` e ricevere risposte).

## La soluzione

I metodi tornano **`list[str]`**. Il chiamante itera e scrive ogni comando nel PTY:

- **ClaudeProvider**: torna `[comando_unico]` → 1 write (come oggi)
- **HermesProvider**: torna `[comando_avvio, messaggio_iniziale]` → 2 write

Il pattern chiamante finale:

```python
pty = service.get_pty(terminal_id)
commands = provider.build_run_issue_commands(issue_id)  # sempre list[str]
for cmd in commands:
    for var, val in replacements.items():
        cmd = cmd.replace(var, val)
    pty.write(cmd + "\r\n")
```

---

## File da modificare

| File | Cosa cambia |
|---|---|
| `backend/app/providers/base.py` | 4 metodi cambiano return type: `str` → `list[str]` + rename in `*_commands()` plurale |
| `backend/app/providers/claude_provider.py` | 4 metodi: `return [comando]` invece di `return comando` |
| `backend/app/providers/hermes_provider.py` | 4 metodi: split in comando d'avvio + messaggio iniziale (rimuovere `-q`) |
| `backend/app/services/pipeline_run/_execution.py` | Loop over commands invece di `pty.write(cmd + "\r\n")` singolo |
| `backend/app/services/terminal_operations.py` | 3 punti (run-issue, ask, manage-agent): loop come sopra |
| `backend/tests/test_agent_providers.py` | Aggiornare assertion `str` → `list[str]` |

---

## Dettaglio modifiche

### 1. `providers/base.py`

```python
# PRIMA
@abstractmethod
def build_run_issue_command(self, issue_id: str) -> str: ...

@abstractmethod
def build_run_pipeline_command(self, issue_id: str) -> str: ...

@abstractmethod
def build_ask_brainstorm_command(self, project_id: str) -> str: ...

@abstractmethod
def build_manage_agent_command(self, intent: str = "") -> str: ...

# DOPO
@abstractmethod
def build_run_issue_commands(self, issue_id: str) -> list[str]: ...

@abstractmethod
def build_run_pipeline_commands(self, issue_id: str) -> list[str]: ...

@abstractmethod
def build_ask_brainstorm_commands(self, project_id: str) -> list[str]: ...

@abstractmethod
def build_manage_agent_commands(self, intent: str = "") -> list[str]: ...
```

**`build_hook_command()` resta invariato** — torna già `list[str]` ed è usato con `create_subprocess_exec()`, non col PTY.

### 2. `providers/claude_provider.py`

```python
# PRIMA
def build_run_issue_command(self, issue_id: str) -> str:
    return f"claude ... \"/run-issue {shlex.quote(issue_id)}\""

# DOPO
def build_run_issue_commands(self, issue_id: str) -> list[str]:
    return [f"claude ... \"/run-issue {shlex.quote(issue_id)}\""]
```

Stessa logica per pipeline, ask, manage-agent.

### 3. `providers/hermes_provider.py`

```python
# PRIMA (one-shot con -q)
def build_run_issue_command(self, issue_id: str) -> str:
    return (
        f"hermes chat --skills run-issue --worktree --yolo "
        f"-q \"Work on issue {shlex.quote(issue_id)}\""
    )

# DOPO (2 write: avvio + messaggio)
def build_run_issue_commands(self, issue_id: str) -> list[str]:
    return [
        "hermes chat --skills run-issue --worktree --yolo",
        f"Work on issue {issue_id}",
    ]
```

Tutti i metodi Hermes:

| Metodo | Comando 1 (avvio) | Comando 2 (messaggio) |
|---|---|---|
| `build_run_issue_commands(id)` | `hermes chat -s run-issue --yolo` | `Work on issue {id}` |
| `build_run_pipeline_commands(id)` | `hermes chat -s run-pipeline --yolo` | `Execute pipeline step for issue {id}` |
| `build_ask_brainstorm_commands(id)` | `hermes chat -s ask-and-brainstorm --yolo` | `Brainstorming for project {id}` |
| `build_manage_agent_commands(intent)` | `hermes chat -s manage-agent --yolo` | `{intent}` (solo se intent non vuoto) |

Niente `-q`, niente `exit` → Hermes resta interattivo.

### 4. `services/pipeline_run/_execution.py`

**Punto: riga 323-325**

```python
# PRIMA
command = provider.build_run_pipeline_command(issue_id)
pty.write(f"{command}\r\n")

# DOPO
commands = provider.build_run_pipeline_commands(issue_id)
for cmd in commands:
    pty.write(cmd + "\r\n")
```

### 5. `services/terminal_operations.py`

**3 punti diversi:**

a) Run issue (riga ~221):
```python
# PRIMA
cmd = provider.build_run_issue_command(data.issue_id)
# ... log ...
pty.write(cmd + "\r\n")

# DOPO
cmds = provider.build_run_issue_commands(data.issue_id)
for cmd in cmds:
    # ... variable replacements su ogni cmd ...
    pty.write(cmd + "\r\n")
```

b) Ask & Brainstorm (riga ~268):
```python
# PRIMA
cmd = provider.build_ask_brainstorm_command(data.project_id)
pty.write(cmd + "\r\n")

# DOPO
cmds = provider.build_ask_brainstorm_commands(data.project_id)
for cmd in cmds:
    pty.write(cmd + "\r\n")
```

c) Manage Agent (riga ~363):
```python
# PRIMA
cmd = provider.build_manage_agent_command(agent_intent or "")
pty.write(cmd + "\r\n")

# DOPO
cmds = provider.build_manage_agent_commands(agent_intent or "")
for cmd in cmds:
    pty.write(cmd + "\r\n")
```

### 6. `tests/test_agent_providers.py`

Tutti i test che usano `build_*_command` devono:
- Chiamare `build_*_commands`
- Verificare che il risultato sia `list[str]`
- Usare `cmd[0]` invece di `cmd` per le assertion
- Per Hermes: verificare che `len(cmd) == 2` e che `cmd[0]` non contenga `-q`

Custom provider nel test `DummyProvider`:
```python
# PRIMA
def build_run_issue_command(self, issue_id: str) -> str:
    return f"dummy run {issue_id}"

# DOPO
def build_run_issue_commands(self, issue_id: str) -> list[str]:
    return [f"dummy run {issue_id}"]
```

---

## Ordine di implementazione

1. `base.py` — cambiare interfaccia (4 metodi)
2. `claude_provider.py` — aggiornare implementazione
3. `hermes_provider.py` — aggiornare implementazione (il grosso del cambiamento)
4. `_execution.py` — loop sulle commands
5. `terminal_operations.py` — 3 loop sulle commands
6. `test_agent_providers.py` — aggiornare test
7. Eseguire test: `python -m pytest tests/test_agent_providers.py -v`

---

## Non cambia

- `build_hook_command()` → invariato (già `list[str]`)
- `AgentProviderRegistry` → invariato
- Logica di registrazione provider
- Schema DB, API, frontend
