# 🔴 Manager AI — Critical Fix Report V1

**Data:** 2026-06-05
**Versione analizzata:** `57f29fb` (branch `master`)
**File analizzati:** ~88 backend + ~30 frontend
**Issue totali trovate:** 47

---

## RIEPILOGO

| Area | File analizzati | Issue totali |
|------|----------------|-------------|
| Backend services | 28 | 35 |
| Backend routers | 27 | 20 |
| Backend models | 18 | 15 |
| Backend MCP/hooks/infra | 12 | 25 |
| Frontend | ~30 | 12 |

---

## 🔴 CRITICAL (da fixare subito)

### 1. `credential_service.py:17-21` — Chiave Fernet random persa al restart

```python
@staticmethod
def _get_fernet() -> Fernet:
    key = os.environ.get("MANAGER_AI_SECRET_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        os.environ["MANAGER_AI_SECRET_KEY"] = key
    return Fernet(key.encode() if isinstance(key, str) else key)
```

Se `MANAGER_AI_SECRET_KEY` non e' impostata, genera chiave random in memoria. Al restart del server, **tutte le credenziali diventano permanentemente illeggibili**. Deve lanciare errore hard, non degradare silenziosamente.

**Fix:** Sostituire `Fernet.generate_key()` con un errore esplicito:
```python
if not key:
    raise RuntimeError("MANAGER_AI_SECRET_KEY environment variable is required")
```

**File:** `backend/app/services/credential_service.py`
**Effort:** 30 min

---

### 2. `main.py:486-492` — CORS `allow_credentials=True` con `allow_origins=["*"]`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Combinazione invalida per lo standard CORS. I browser rifiutano richieste con credenziali quando l'origine e' wildcard.

**Fix:** Rimuovere `allow_credentials=True` o specificare origini esplicite da config.

**File:** `backend/app/main.py`
**Effort:** 10 min

---

### 3. `mcp/server.py:131-182` — Hook `ISSUE_COMPLETED` chiamato DUE volte

Il tool MCP `complete_issue` chiama `issue_service.complete_issue()` (che internamente chiama `hook_registry.fire(HookEvent.ISSUE_COMPLETED)`) e poi chiama di nuovo lo stesso hook alle linee 163-178.

```python
# issue_service.complete_issue() gia' chiama hook_registry.fire(HookEvent.ISSUE_COMPLETED)
issue = await issue_service.complete_issue(issue_id, project_id, recap)

# Poi il MCP tool lo chiama una SECONDA volta:
await hook_registry.fire(
    HookEvent.ISSUE_COMPLETED,
    HookContext(...)
)
```

**L'hook viene eseguito due volte per ogni completamento issue.**

**Fix:** Rimuovere la chiamata hook duplicata dal MCP tool (linee 163-178). La business logic deve stare nel service layer.

**File:** `backend/app/mcp/server.py`
**Effort:** 10 min

---

### 4. Nessuna autenticazione su alcun endpoint

MCP, REST, WebSocket — tutti completamente aperti. `start.py` binda il backend a `0.0.0.0` (tutte le interfacce). Chiunque in rete puo':

- Creare/leggere/eliminare issue
- Accedere a credenziali in chiaro
- Creare/eliminare agenti e pipeline
- Eseguire pipeline
- Scrivere comandi nei terminali

**Fix:** Implementare auth layer (API key o JWT) su tutti gli endpoint. Per il MCP, usare header `Authorization`.

**File:** `backend/app/main.py`, `backend/app/mcp/server.py`, tutti i router
**Effort:** 3-5 giorni

---

### 5. `pipeline_run_service.py:104-106` — Race condition commit prima del task spawn

```python
await self.session.commit()  # <-- commit qui

task = asyncio.create_task(    # <-- task creato qui
    self._execute(run.id, project_id, project_path)
)
```

Se crash tra `commit()` e `create_task()`, il chiamante vede successo ma la pipeline non parte mai. Il record rimane nello stato RUNNING per sempre.

**Fix:** Invertire ordine o usare `asyncio.create_task` prima del commit con rollback su fallimento.

**File:** `backend/app/services/pipeline_run_service.py`
**Effort:** 20 min

---

## 🟠 HIGH (fix nella prossima iterazione)

### 6. `mcp/server.py` — 1438 righe, duplicazione massiccia

Ogni MCP tool ripete lo stesso pattern:
```python
async with async_session() as session:
    svc = XxxService(session)
    try:
        result = await svc.some_method(...)
        await session.commit()
        await event_service.emit({...})
        return {...}
    except AppError as e:
        return {"error": e.message}
```

Duplicazioni specifiche:
- **Serializzazione agent** ripetuta 4 volte identica (linee 996, 1016, 1036, 1065)
- **Serializzazione pipeline** ripetuta 6+ volte identica (linee 1107, 1132, 1159, 1186, 1224, 1263)
- **`issue.name or (issue.description or "")[:50] or ""`** ripetuto 15+ volte
- **Pattern event emission** duplicato 20+ volte

**Fix:**
- Creare decorator `@mcp_tool_wrapper` che gestisce session, error handling, commit
- Estrarre funzioni `_serialize_agent()`, `_serialize_pipeline()`, `_issue_display_name()`
- Ridurre file a ~400 righe

**File:** `backend/app/mcp/server.py`
**Effort:** 2-3 giorni

---

### 7. `main.py:325-473` — Lifespan di 148 righe monolitico

La funzione `lifespan` esegue 14 operazioni sequenziali:
1. Windows event loop exception handler
2. Hook registry logging
3. Database migration
4. Issue status fixup
5. Write queue + background writer init
6. Project loading into memory
7. Pending transcription recovery
8. Catalog loading
9. MCP plugin startup
10. Agent e pipeline seeding
11. Orphaned pipeline run cleanup
12. Claude resources installation
13. MCP session manager lifecycle
14. Plugin shutdown

Ogni step wrappato in `try/except` che silenzia errori. Se un progetto fallisce, gli altri non vengono caricati.

**Fix:** Decomporre in funzioni separate:
- `_startup_migrate()`
- `_startup_load_projects()`
- `_startup_seed_defaults()`
- `_startup_cleanup_orphaned_runs()`
- `_startup_install_claude_resources()`

**File:** `backend/app/main.py`
**Effort:** 1 giorno

---

### 8. `main.py:109-279` — `_load_project_into_memory` 170 righe

Funzioni interne `_opt_str()`, `_as_str()`, `_link_from_dict()` ridefinite a ogni chiamata. Helper `_read_optional_md`, `_opt_str_static`, `_as_iso`, `_task_from_dict`, `_relation_from_dict` definiti DOPO il loro utilizzo (linea 282+).

**Fix:** Estrarre in modulo separato `storage/project_loader.py` con funzioni module-level.

**File:** `backend/app/main.py`
**Effort:** 1 giorno

---

### 9. `pipeline_run_service.py:243-425` — `_execute()` di 182 righe

Unico metodo che gestisce:
- Session management
- Fetch pipeline
- Loop su step
- Creazione terminale
- Gestione WSL path
- Event emission WebSocket
- Esecuzione step
- Gestione errori
- Cleanup terminale
- Finalizzazione run

Single Responsibility Principle violato pesantemente.

**Fix:** Estrarre metodi separati:
- `_execute_single_step()`
- `_create_terminal_for_step()`
- `_handle_wsl_cd()`
- `_finalize_run()`

**File:** `backend/app/services/pipeline_run_service.py`
**Effort:** 1 giorno

---

### 10. `issue_service.py:110-116` — `get_by_id()` scan O(n) di tutti i progetti

```python
async def get_by_id(self, issue_id: str) -> IssueRecord | None:
    for project in await ProjectService(self.session).list_all(archived=False):
        rec = issue_store.load_issue(project.path, issue_id)
        if rec is not None:
            return rec
    return None
```

Con 50 progetti = 50 letture disco per ogni lookup. Chiamato da `terminals.py` linea 500 per ogni terminale attivo (O(N*M)).

**Fix:** Mantenere un indice `issue_id → project_id` in memoria (es. dictionary globale aggiornato a ogni creazione issue).

**File:** `backend/app/services/issue_service.py`
**Effort:** 2 ore

---

### 11. `mcp/server.py` — `find_task` scan O(n) ripetuto 3 volte

Stesso pattern copy-paste in 3 tool MCP:
- `update_task_status` (linee 436-442)
- `update_task_name` (linee 492-498)
- `delete_task` (linee 523-529)

```python
for project in await ProjectService(session).list_all(archived=False):
    from app.storage import issue_store as _is
    found = _is.find_task(project.path, task_id)
    if found is not None:
        issue, _ = found
        task_issue_id = issue.id
        break
```

**Fix:** Estrarre `_find_task_issue(task_id)` come utility. Mantenere indice `task_id → (issue_id, project_id)`.

**File:** `backend/app/mcp/server.py`
**Effort:** 1 ora

---

### 12. `terminal_service.py:138` — Command injection WSL distro

```python
pty.spawn(f'"{shell_to_use}" -d {wsl_distro}', cwd=spawn_cwd)
```

`wsl_distro` validato con regex (linea 121) ma interpolato direttamente in stringa shell. `shell_to_use` viene da `MANAGER_AI_SHELL` env var controllabile dall'utente.

**Fix:** Usare `shlex.quote()` su entrambi i valori. Validare `shell_to_use` come path assoluto a un eseguibile.

**File:** `backend/app/services/terminal_service.py`
**Effort:** 1 ora

---

### 13. `terminals.py:482-486` e `projects.py:476-486` — URL non quotato in comandi shell

```python
pty.write(f"claude mcp add ManagerAi --transport http \"{url}\"\r\n")
```

`shlex.quote()` non usato per l'URL. Se host IP contiene metacaratteri shell → command injection.

**Fix:** Usare `shlex.quote(url)`.

**File:** `backend/app/routers/terminals.py`, `backend/app/routers/projects.py`
**Effort:** 30 min

---

### 14. `start.py:106-108` — Processi orfani su Windows

```python
if IS_WINDOWS:
    ret = subprocess.run([str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]).returncode
    sys.exit(ret)
```

Su Windows, re-exec spawna nuovo processo ed esce. Se utente killla il terminale, il processo figlio sopravvive come orfano.

**Fix:** Gestire segnali di terminazione (SIGTERM, CTRL_C_EVENT) e propagarli al child process.

**File:** `start.py`
**Effort:** 1 ora

---

## 🟡 MEDIUM (debito tecnico da pianificare)

### 15. Modelli senza ForeignKey constraint

| Modello | Colonna | Rischio |
|---------|---------|---------|
| `project_credential.py:11` | `project_id` | Nessun FK a `projects.id` |
| `project_skill.py:10` | `project_id` | Nessun FK a `projects.id` |
| `prompt_template.py:12` | `project_id` | Nessun FK, nullable |

**Fix:** Aggiungere `ForeignKey("projects.id")` dove applicabile.

---

### 16. PK type inconsistente tra modelli

- **UUID `String(36)`:** project, issue, agent, task, pipeline, pipeline_run, memory, file, question, credential
- **Auto-increment `Integer`:** issue_relation, project_skill, project_variable, prompt_template, terminal_command

**Fix:** Standardizzare su UUID `String(36)` per tutti i modelli.

---

### 17. Modelli senza indici necessari

| Modello | Colonna | Query frequente |
|---------|---------|-----------------|
| `issue.py` | `status` | Filtro per stato |
| `issue.py` | `priority` | Ordinamento |
| `issue.py` | `category` | Filtro per categoria |
| `issue.py` | `project_id` | Lookup per progetto |
| `agent.py` | `name` | Lookup per nome (no `UniqueConstraint`) |
| `project.py` | `name` | Lookup per nome |

**Fix:** Aggiungere `index=True` e `UniqueConstraint` dove necessario.

---

### 18. `terminal_service.py:106` — `threading.Lock` in contesto async

```python
self._lock = threading.Lock()
```

Lock sincrono usato in metodi chiamati da coroutine async. Rischio blocco event loop se conteso.

**Fix:** Usare `asyncio.Lock` e rendere i metodi che lo usano async.

---

### 19. `terminal_service.py` — Nessun TTL per terminali

I terminali vengono aggiunti ma mai rimossi automaticamente per inattivita'. Se `mark_closed` non viene chiamato (es. crash), il dizionario cresce indefinitamente (memory leak).

**Fix:** Aggiungere TTL configurabile con cleanup periodico.

---

### 20. `issue_service.py:37-38` — `_issue_completion_locks` dict senza cleanup

```python
_issue_completion_locks: dict[str, asyncio.Lock] = {}
```

Module-level dict cresce per sempre. Ogni issue completata lascia un lock nel dict.

**Fix:** Rimuovere lock dal dict dopo `async with lock:` completa.

---

### 21. `plugin_client.py:281-300` — Leak processi zombie

`_exit_transport()` ha timeout di 3s (session) e 5s (transport). Se entrambi i timeout sono superati, il processo subprocess rimane in esecuzione senza kill esplicito.

**Fix:** Aggiungere `process.kill()` dopo timeout.

---

### 22. `plugin_proxy.py:152` — Cattura `BaseException`

```python
except BaseException as e:
```

`CancelledError`, `KeyboardInterrupt`, `SystemExit` tutti catturati e convertiti in `{"error": ...}`. `CancelledError` deve essere ri-lanciato.

**Fix:** Usare `except Exception` invece di `except BaseException`.

---

### 23. `background_writer.py:104-119` — Fire-and-forget event emission

```python
asyncio.create_task(event_service.emit(...))
```

Task creato senza reference tracking. Eccezioni perse silenziosamente.

**Fix:** Tracciare il task e loggare eccezioni nel callback.

---

### 24. `memory_store_core.py:75` — Crash su `created_at=None`

```python
idx.sort(key=lambda e: (e.get("created_at", ""), e.get("id", "")))
```

Se `created_at` e' esplicitamente `None`, `e.get("created_at", "")` restituisce `None`, e `None < str` lancia `TypeError`.

**Fix:** `e.get("created_at") or ""`

---

### 25. `start.py:172-178` — Build produzione anche in dev

Nessun flag `--dev`. Build frontend (~30-60s) eseguita sempre.

**Fix:** Aggiungere flag `--dev` che skippa `npm run build` e usa `npm run dev`.

---

### 26. `alembic/env.py:9` — Importa solo 3 modelli

```python
from app.models import Project, Question, Task
```

Molti modelli (Agent, Pipeline, PipelineRun, PipelineStepRun, PipelineMessage, Issue, Memory, ProjectLink, ProjectFile, Credential...) non importati esplicitamente. Se import ordering cambia, Alembic potrebbe non rilevare tabelle in `autogenerate`.

**Fix:** Importare esplicitamente tutti i modelli che hanno tabelle corrispondenti.

---

### 27. Migrazione `6c15726f26d6` — Downgrade vuoto

```python
def downgrade() -> None:
    pass
```

La migrazione droppa le tabelle `agents`, `pipelines`, `pipeline_runs`, `agent_step_runs`, `agent_messages` ma non fornisce modo di ricrearle. Rollback oltre questa migrazione impossibile.

**Fix:** Documentare che questa e' una migrazione one-way e aggiungere commento esplicito.

---

### 28. `config.py:17` — `.env` risolto da CWD

```python
model_config = {"env_file": ".env"}
```

Pydantic risolve `.env` relativo alla directory corrente, non alla posizione del file. Se avviato da directory diversa, settings usano default invece del file `.env`.

**Fix:** Risolvere path relativo a `Path(__file__).parent.parent / ".env"`.

---

### 29. `$issueId.tsx` — Componente monolite di 324 righe

`IssueDetailPage` gestisce: terminali (open/close/split), pipeline progress, issue detail, domande pending, dialog di conferma, resizable panels. `TerminalWithQuestions` renderizzato 6+ volte con props identici. Blocco `pendingQuestions` duplicato 3 volte.

**Fix:** Estrarre componenti separati:
- `TerminalPanel`
- `PipelinePanel`
- `PendingQuestionsSection`
- `TerminalLimitDialog`
- `CloseConfirmDialog`
- Hook `useTerminalLayout`

**File:** `frontend/src/routes/projects/$projectId/issues/$issueId.tsx`
**Effort:** 4 ore

---

### 30. `mcp/server.py:957` — `ask_user_question` blocca worker fino a 3600s

```python
await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
```

Blocca un worker ASGI per tutta l'attesa della risposta utente. Con N worker e N domande concorrenti, il pool e' esaurito.

**Fix:** Usare un meccanismo di long-polling o connection upgrading invece del blocking wait.

---

## 🟢 LOW (code quality)

### 31-37. Duplicazione codice

| # | Cosa | Dove |
|---|------|------|
| 31 | `_parse_dt()` | `schemas/task.py:46-51` e `schemas/issue_relation.py:57-62` |
| 32 | `_coerce_dt()` | `schemas/memory.py:49-54` e `schemas/project_file.py:44-49` |
| 33 | `_snippet()` | `memory_service.py:268-282` e `file_service.py:254-268` |
| 34 | Step-run dict serialization | `pipeline_run_service.py` in 3 metodi (~50 righe totali) |
| 35 | Agent serialization | `mcp/server.py` in 4 tool |
| 36 | Pipeline serialization | `mcp/server.py` in 6 tool |
| 37 | Hook metadata builder | `issue_service.py` in `accept_issue`, `cancel_issue`, `complete_issue`, `force_finish_issue` |

---

### 38-47. Issues minori

| # | Issue | File |
|---|-------|------|
| 38 | `logger` usato ma `import logging` mancante | `file_service.py:78,80,87` |
| 39 | Colonna `metadata` confligge con `Base.metadata` SQLAlchemy | `project_file.py:25` |
| 40 | Leak GDI handles (`LoadImageW` senza `DestroyIcon`) | `desktop_icon.py` |
| 41 | Monkey-patch fragile di `uvicorn.loops.asyncio.asyncio_setup` | `_ensure_proactor.py:17` |
| 42 | Prompt hardcoded in italiano | `hooks/handlers/enrich_context.py:41-56` |
| 43 | 6 agent default hardcoded inline (dovrebbero essere in config/seeds) | `agent_service.py:11-63` |
| 44 | `project_variable_service.py` lancia `KeyError` invece di `NotFoundError` | `project_variable_service.py:45,55` |
| 45 | `_sessions` e `_stop_reader` importati da modulo privato | `pipeline_run_service.py:23` |
| 46 | Nessun `AbortController` nelle chiamate fetch frontend | `frontend/src/features/*/api.ts` |
| 47 | Polling ogni 3 secondi invece di WebSocket events | `$issueId.tsx:50` |

---

## SERVICE SENZA TEST

Nessun file di test trovato per questi servizi critici:

| Service | Rischio |
|---------|---------|
| `pipeline_run_service.py` | PIU' COMPLESSO — async task, step rejection, session lifecycle |
| `issue_service.py` | CORE — workflow issue, hook firing, lock completion |
| `credential_service.py` | SICUREZZA — encryption/decryption Fernet |
| `terminal_service.py` | INFRA — PTY lifecycle, WebSocket, WSL |
| `plugin_client.py` | INFRA — subprocess MCP, connessione/disconnessione |
| `plugin_manager.py` | INFRA — start/stop/restart plugin |
| `memory_service.py` | CORE — search FTS, link/unlink, CRUD |

---

## MATRICE PRIORITA / AZIONE

| # | Issue | Severita' | Effort | Azione |
|---|-------|-----------|--------|--------|
| 1 | Fernet key persa al restart | CRITICAL | 30min | Alzare errore se env var mancante |
| 2 | CORS invalido | CRITICAL | 10min | Rimuovere `allow_credentials` |
| 3 | Hook ISSUE_COMPLETED 2x | CRITICAL | 10min | Rimuovere chiamata duplicata in MCP tool |
| 4 | Nessuna auth | CRITICAL | 3-5gg | Implementare auth layer |
| 5 | Race condition pipeline start | CRITICAL | 20min | Invertire ordine: task prima di commit |
| 6 | MCP server 1438 righe | HIGH | 2-3gg | Refactor con decorator + helper |
| 7 | Lifespan monolite | HIGH | 1gg | Decomporre in 5 funzioni |
| 8 | `_load_project_into_memory` 170 righe | HIGH | 1gg | Estrarre in modulo separato |
| 9 | `_execute()` 182 righe | HIGH | 1gg | Split in 4 metodi |
| 10 | `get_by_id()` O(n) scan | HIGH | 2h | Indice issue_id → project_id in memoria |
| 11 | `find_task` O(n) ×3 | HIGH | 1h | Utility condivisa + indice |
| 12 | Command injection WSL | HIGH | 1h | `shlex.quote()` + validazione shell path |
| 13 | URL non quotato shell | HIGH | 30min | `shlex.quote()` su URL |
| 14 | Processi orfani start.py | HIGH | 1h | Gestire segnali terminazione |
| 15 | FK mancanti (3 modelli) | MEDIUM | 1h | Aggiungere `ForeignKey` constraint |
| 16 | PK type inconsistente | MEDIUM | 2h | Standardizzare su UUID |
| 17 | Indici mancanti (6 colonne) | MEDIUM | 1h | Aggiungere `index=True` |
| 18 | `threading.Lock` in async | MEDIUM | 1h | Migrare a `asyncio.Lock` |
| 19 | Terminal senza TTL | MEDIUM | 2h | Aggiungere cleanup periodico |
| 20 | Lock dict senza cleanup | MEDIUM | 30min | Rimuovere lock dopo uso |
| 21 | Processi zombie plugin | MEDIUM | 1h | Aggiungere `process.kill()` dopo timeout |
| 22 | `BaseException` catch | MEDIUM | 10min | Cambiare in `except Exception` |
| 23 | Fire-and-forget event | MEDIUM | 30min | Tracciare task e loggare errori |
| 24 | Crash `created_at=None` | MEDIUM | 10min | Usare `or ""` invece di `get()` |
| 25 | Build produzione in dev | MEDIUM | 1h | Aggiungere flag `--dev` |
| 26 | Alembic import 3 modelli | MEDIUM | 30min | Importare tutti i modelli |
| 27 | Downgrade vuoto | MEDIUM | 10min | Documentare come one-way |
| 28 | `.env` path CWD | MEDIUM | 10min | Path relativo a `__file__` |
| 29 | `$issueId.tsx` 324 righe | MEDIUM | 4h | Estrarre componenti |
| 30 | `ask_user_question` blocca worker | MEDIUM | 3h | Long-polling invece di block |
| 31-37 | Codice duplicato | LOW | 3h | Estrarre funzioni condivise |
| 38-47 | Issues minori | LOW | 3h | Varie fix puntuali |

---

## NOTE

- **Pattern ricorrente piu' dannoso:** scansione O(n) di tutti i progetti per trovare un record (`get_by_id`, `find_task`). Appare in 6+ service e 3+ MCP tool. Richiede un indice centralizzato `record_id → project_id`.
- **Pattern architetturale da rivedere:** ibrido DB (SQLite) + filesystem (`.manager_ai/`) senza chiara separazione. Issues, tasks, memories su disco; agents, pipelines, runs su DB. Forza pattern di scan cross-store.
- **MCP server.py** e' il file piu' grande (1438 righe) e con piu' debito tecnico. Refactor prioritario dopo i fix CRITICAL.
