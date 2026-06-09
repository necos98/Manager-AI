# Refactor PTY Terminal Creation — Implementation Plan

> **For Hermes:** Execute tasks sequentially. Each task is one focused change with verification.

**Goal:** Eliminare la duplicazione della creazione PTY in `terminal_operations.py` — 3 funzioni (`create_terminal`, `create_ask_terminal`, `create_manage_agent_terminal`) condividono ~80% della stessa logica di setup. Estrarre una funzione `_create_terminal_base()` riutilizzabile da tutte e 3.

**Architecture:** Factory method pattern leggero. Ogni funzione chiama `_create_terminal_base()` che si occupa della creazione del PTY, validazione path, risoluzione shell/WSL, iniezione env vars e reap dei terminali esistenti. Poi ogni funzione aggiunge solo la logica specifica (comando del provider, startup commands).

**Tech Stack:** Python/FastAPI, SQLAlchemy async, pytest

---

## Analisi della duplicazione attuale

### Pattern comune (tutte e 3 le funzioni)

```
1. Risolvere project_path (con fallback diverso per manage-agent)
2. Validare che project_path esista su disco
3. Ottenere Project dal DB → shell, wsl_distro
4. [OPZ] Reap terminali esistenti (ask, manage-agent)
5. service.create(issue_id, project_id, project_path, shell, wsl_distro)
6. Determinare is_wsl
7. _inject_terminal_env(service, terminal["id"], ...)
8. Leggere provider_name da SettingsService
9. Costruire comando specifico (run-issue / ask / manage-agent)
10. Scrivere comando nel PTY
```

### Differenze

| Aspetto | `create_terminal` | `create_ask_terminal` | `create_manage_agent_terminal` |
|---|---|---|---|
| **project_path** | Dal DB (project_id) | Dal DB (project_id) | Calcolato da `settings.database_url` |
| **Reap esistente** | ❌ No | ✅ Sì (stesso project_id, issue_id="") | ✅ Sì (project_id="", issue_id="") |
| **Extra env vars** | `MANAGER_AI_ISSUE_ID` | Nessuna | `MANAGER_AI_TERMINAL_ID`, `MANAGER_AI_BASE_URL`, optionals |
| **Comando provider** | `build_run_issue_command()` | `build_ask_brainstorm_command()` | `build_manage_agent_command(intent)` |
| **Startup commands** | ✅ (da DB + custom) | ❌ No | ❌ No |
| **issue_id** | `data.issue_id` | `""` | `""` |
| **project_id** | `data.project_id` | `data.project_id` | `""` |
| **Schema dati** | `TerminalCreate` | `AskTerminalCreate` | `ManageAgentTerminalCreate` |

---

## Task 1: Creare `_create_terminal_base()` — setup comune del PTY

**Objective:** Estrarre la logica di creazione PTY, path resolution, shell resolution e env injection in una funzione privata condivisa.

**Files:**
- Modify: `backend/app/services/terminal_operations.py`
- No new test (è una funzione privata, testata indirettamente via i test delle 3 funzioni pubbliche)

**Segnatura della nuova funzione:**

```python
async def _create_terminal_base(
    db: AsyncSession,
    service: TerminalService,
    *,
    project_id: str,
    issue_id: str = "",
    project_path: str | None = None,           # override per manage-agent
    shell: str | None = None,                   # da chiamante o None
    wsl_distro: str | None = None,              # da chiamante o None
    reap_project_id: str | None = None,         # se impostato, fa reap dei terminali attivi
    reap_issue_id: str = "",                    # filtro issue per reap
    extra_env: dict[str, str] | None = None,    # env vars extra da injettare
) -> tuple[dict, str, str | None, bool]:
    """Crea PTY terminal, risolve path/shell/WSL, inietta env vars.

    Returns:
        (terminal_dict, resolved_project_path, project_shell, is_wsl)
    """
```

**Step 1: Scrivere la funzione**

Contenuto della funzione (copiando la logica esistente senza duplicazione):

```python
async def _create_terminal_base(
    db: AsyncSession,
    service: TerminalService,
    *,
    project_id: str,
    issue_id: str = "",
    project_path: str | None = None,
    shell: str | None = None,
    wsl_distro: str | None = None,
    reap_project_id: str | None = None,
    reap_issue_id: str = "",
    extra_env: dict[str, str] | None = None,
) -> tuple[dict, str, str | None, bool]:
    """Crea PTY terminal, risolve path/shell/WSL, inietta env vars.

    Returns:
        (terminal_dict, resolved_project_path, project_shell, is_wsl)
    """
    # ── Resolve project path ────────────────────────────────────────
    if project_path is not None:
        resolved_path = project_path
    else:
        resolved_path = await get_project_path(project_id, db)

    if not os.path.isdir(resolved_path):
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {resolved_path}",
        )

    # ── Resolve shell / WSL ─────────────────────────────────────────
    # If shell/wsl_distro not provided by caller, load from DB
    if shell is None or wsl_distro is None:
        project_obj = await db.get(Project, project_id) if project_id else None
        if shell is None:
            shell = project_obj.shell if project_obj else None
        if wsl_distro is None:
            wsl_distro = project_obj.wsl_distro if project_obj else None

    # ── Reap existing terminals if requested ─────────────────────────
    if reap_project_id is not None:
        for existing in service.list_active(
            project_id=reap_project_id, issue_id=reap_issue_id,
        ):
            await _teardown_terminal(existing["id"], service)

    # ── Create PTY ──────────────────────────────────────────────────
    try:
        terminal = service.create(
            issue_id=issue_id,
            project_id=project_id,
            project_path=resolved_path,
            shell=shell,
            wsl_distro=wsl_distro,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to spawn terminal: {e}"
        )

    # ── Inject env vars ─────────────────────────────────────────────
    is_wsl = is_wsl_shell(shell)
    await _inject_terminal_env(
        service,
        terminal["id"],
        project_path=resolved_path,
        project_shell=shell,
        project_id=project_id,
        db=db,
        extra_env=extra_env,
    )

    return terminal, resolved_path, shell, is_wsl
```

**Step 2: Aggiungere docstring e type hints**

**Step 3: Verificare che il modulo importi correttamente**

```bash
cd backend
python -c "from app.services.terminal_operations import _create_terminal_base; print('OK')"
```

Expected: `OK`

---

## Task 2: Refactor `create_terminal()` per usare `_create_terminal_base()`

**Objective:** Sostituire la prima metà di `create_terminal()` con una chiamata a `_create_terminal_base()`.

**Files:**
- Modify: `backend/app/services/terminal_operations.py:44-187`

**Codice risultante:**

```python
async def create_terminal(
    data, db: AsyncSession, service: TerminalService
) -> dict:
    """Create a PTY terminal, inject env vars and startup commands."""
    terminal, project_path, project_shell, is_wsl = await _create_terminal_base(
        db, service,
        project_id=data.project_id,
        issue_id=data.issue_id,
        extra_env={"MANAGER_AI_ISSUE_ID": data.issue_id},
    )

    # ── Startup commands (custom or DB-configured) ──────────────────
    if data.run_commands:
        try:
            # ... (stessa logica attuale, nessun cambiamento)
        except Exception:
            logger.warning(...)

    # ── Run-issue command dal provider ──────────────────────────────
    if data.issue_id and not data.command:
        try:
            from app.services.settings_service import SettingsService
            settings_svc = SettingsService(db)
            provider_name = await settings_svc.get("agent_provider")
            provider = AgentProviderRegistry.get(provider_name)
            cmd = provider.build_run_issue_command(data.issue_id)

            replacements = {
                "$issue_id": data.issue_id,
                "$project_id": data.project_id,
                "$project_path": win_to_wsl_path(project_path) if is_wsl else project_path,
            }
            for var, val in replacements.items():
                cmd = cmd.replace(var, val)
            logger.info("Injecting run-issue command (provider=%s): %s", provider_name, cmd)
            pty = service.get_pty(terminal["id"])
            pty.write(cmd + "\r\n")
        except Exception:
            logger.warning("Failed to inject run-issue command for terminal %s", terminal["id"], exc_info=True)

    return terminal
```

**Step 2: Verifica sintassi**

```bash
cd backend
python -c "import py_compile; py_compile.compile('app/services/terminal_operations.py', doraise=True); print('OK')"
```

Expected: `OK`

**Step 3: Eseguire test terminal**

```bash
cd backend
python -m pytest tests/test_terminal_router.py tests/test_terminal_service.py -v --tb=line
```

Expected: PASS

---

## Task 3: Refactor `create_ask_terminal()` per usare `_create_terminal_base()`

**Objective:** Sostituire la logica di setup PTY in `create_ask_terminal()` con una chiamata a `_create_terminal_base()` con `reap_existing`.

**Files:**
- Modify: `backend/app/services/terminal_operations.py:190-265`

**Codice risultante:**

```python
async def create_ask_terminal(
    data, db: AsyncSession, service: TerminalService
) -> dict:
    """Create an Ask & Brainstorming terminal, reaping any prior one."""
    terminal, project_path, project_shell, is_wsl = await _create_terminal_base(
        db, service,
        project_id=data.project_id,
        issue_id="",
        reap_project_id=data.project_id,
        reap_issue_id="",
    )

    # ── Ask command dal provider ────────────────────────────────────
    try:
        from app.services.settings_service import SettingsService
        settings_svc = SettingsService(db)
        provider_name = await settings_svc.get("agent_provider")
        provider = AgentProviderRegistry.get(provider_name)
        cmd = provider.build_ask_brainstorm_command(data.project_id)

        variables = {
            "$project_id": data.project_id,
            "$project_path": win_to_wsl_path(project_path) if is_wsl else project_path,
        }
        for var, val in variables.items():
            cmd = cmd.replace(var, val)
        logger.info("Ask terminal %s command: %s", terminal["id"], cmd)
        pty = service.get_pty(terminal["id"])
        pty.write(cmd + "\r\n")
    except Exception:
        logger.warning("Failed to inject ask command for terminal %s", terminal["id"], exc_info=True)

    return terminal
```

**Rimozione:** Si eliminano le righe 194-237 (path resolution, DB query, reap, create, env inject).

**Step 2-3:** Verifica sintassi + test come in Task 2.

---

## Task 4: Refactor `create_manage_agent_terminal()` per usare `_create_terminal_base()`

**Objective:** Sostituire la logica di setup PTY in `create_manage_agent_terminal()`. Questa funzione ha il path calcolato e env vars aggiuntive.

**Files:**
- Modify: `backend/app/services/terminal_operations.py:268-359`

**Codice risultante:**

```python
async def create_manage_agent_terminal(
    data, db: AsyncSession, service: TerminalService
) -> dict:
    """Create a Manage Agent terminal."""
    # Calcola project_path (unico per manage-agent — non dal DB)
    project_path = str(Path(app_settings.database_url).parent.parent.resolve())
    if not os.path.isdir(project_path):
        project_path = str(Path(__file__).resolve().parent.parent.parent)

    # Fetch agent intent before creating terminal
    agent_intent = ""
    if data.agent_id:
        try:
            from app.services.agent_service import AgentService
            agent_svc = AgentService(db)
            agent = await agent_svc.get_by_id(data.agent_id)
            agent_intent = agent.intent
        except Exception:
            logger.warning("Failed to fetch agent %s for terminal", data.agent_id, exc_info=True)

    # Build custom env vars (manage-agent specific)
    extra_env = {}
    pty = service.get_pty(terminal["id"])
    port = str(app_settings.backend_port)
    extra_env = {
        "MANAGER_AI_TERMINAL_ID": terminal["id"],
        "MANAGER_AI_BASE_URL": f"http://localhost:{port}",
    }
    if data.agent_id:
        extra_env["MANAGER_AI_AGENT_ID"] = data.agent_id
        extra_env["MANAGER_AI_AGENT_INTENT"] = agent_intent

    terminal, project_path, project_shell, is_wsl = await _create_terminal_base(
        db, service,
        project_id="",
        issue_id="",
        project_path=project_path,
        extra_env=extra_env,
        reap_project_id="",
        reap_issue_id="",
    )

    # ── Manage-agent env vars (inietta via PTY dopo create) ─────────
    try:
        pty = service.get_pty(terminal["id"])
        # ... env vars set via PTY write (stessa logica attuale)
    except Exception:
        logger.warning("Failed to inject env vars for manage-agent terminal %s", terminal["id"], exc_info=True)

    # ── Manage-agent command dal provider ───────────────────────────
    try:
        from app.services.settings_service import SettingsService
        settings_svc = SettingsService(db)
        provider_name = await settings_svc.get("agent_provider")
        provider = AgentProviderRegistry.get(provider_name)
        cmd = provider.build_manage_agent_command(
            agent_intent if data.agent_id else ""
        )
        logger.info("Manage-agent terminal %s command: %s", terminal["id"], cmd)
        pty = service.get_pty(terminal["id"])
        pty.write(cmd + "\r\n")
    except Exception:
        logger.warning("Failed to inject manage-agent command for terminal %s", terminal["id"], exc_info=True)

    return terminal
```

**NOTA IMPORTANTE:** La funzione `create_manage_agent_terminal` ha **env vars via PTY** (righe 311-336) scritte DOPO la creazione del terminale, in aggiunta a quelle passate via `_inject_terminal_env`. Questo è un pattern diverso — le env vars gestite via PTY rimangono separate da quelle passate a `_create_terminal_base`.

**Step 2-3:** Verifica sintassi + test.

---

## Task 5: Test di integrazione

**Objective:** Verificare che il refactoring non abbia rotto nulla.

**Files:**
- Modify: `backend/tests/test_terminal_router.py` (aggiungere test per `create_terminal_base` indirettamente)
- Run: full test suite

**Test da eseguire:**

```bash
# Terminal tests
cd backend
python -m pytest tests/test_terminal_router.py -v --tb=line

# Terminal service tests
python -m pytest tests/test_terminal_service.py -v --tb=line

# WSL tests
python -m pytest tests/test_terminals_wsl.py -v --tb=line

# Full suite (escluso test_db_backup che è pre-esistente fallito)
python -m pytest tests/ --ignore=tests/test_db_backup.py -x -q --tb=line
```

Expected: Tutti PASS

---

## Riepilogo ordine di esecuzione

| Ordine | Task | Modifica | Righe eliminate |
|---|---|---|---|
| 1 | Task 1 | Creare `_create_terminal_base()` (~50 righe) | — |
| 2 | Task 2 | Refactor `create_terminal()` (~140→~70 righe) | -70 |
| 3 | Task 3 | Refactor `create_ask_terminal()` (~75→~35 righe) | -40 |
| 4 | Task 4 | Refactor `create_manage_agent_terminal()` (~90→~60 righe) | -30 |
| 5 | Task 5 | Test di integrazione | — |

**Risultato finale:** ~140 righe eliminate di codice duplicato. La logica di creazione PTY è centralizzata in 1 funzione invece di essere replicata in 3.

---

## Principi applicati

- **DRY:** Il pattern di creazione PTY è scritto 1 volta e usato 3 volte
- **YAGNI:** La funzione base non introduce nuove feature — solo refactoring della logica esistente
- **Test TDD:** Ogni task termina con verifica test per garantire assenza regressioni
- **Minimal diff:** La logica specifica di ogni funzione (comandi provider, startup commands, env vars PTY) rimane invariata
