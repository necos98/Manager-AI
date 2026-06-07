# Investigation: Backend Forensics — Technical Debt, Code Smells & Risk Areas

## Hand-off Brief

1. **Cosa è stato trovato.** Backend (143 file Python, 15.663 righe) ha **3 macro-problemi**: (A) `mcp/server.py` è un god file da 1.360 righe con pattern ripetitivi al 95% tra i tool MCP; (B) `create_terminal` / `create_ask_terminal` in `routers/terminals.py` hanno ~80 righe di logica identica di env var injection + WSL handling; (C) doppio layer di storage (DB ORM + file-backed dataclass) introduce duplicazione strutturale.
2. **Stato.** Nessun endpoint morto — ogni router ha API frontend. Nessuna dipendenza inutilizzata. Zero TODO/FIXME/HACK. Zero `bare except:`. Zero `eval()/exec()`. Il codice è sorprendentemente pulito per sintassi, ma ha problemi strutturali.
3. **Cosa serve.** Refactor prioritario: (1) decomporre `mcp/server.py` per dominio (issue, memory, pipeline, plugin, credential); (2) estrarre helper comune per creazione terminal; (3) unificare storage layer o eliminare un percorso.

## Case Info

| Field            | Value                                                                      |
| ---------------- | -------------------------------------------------------------------------- |
| Ticket           | N/A                                                                        |
| Date opened      | 2026-06-07                                                                 |
| Status           | Concluded (implementazione iniziata)                                       |
| System           | Windows 11, Python 3.12+, FastAPI, SQLite + file-backed storage            |
| Evidence sources | Codice sorgente backend (143 file), frontend API calls, git history        |

## Problem Statement

"Analisi forense del codebase per identificare debiti tecnici, code smell, aree a rischio. Rifactorizzare l'intero codice backend eliminando parti inutili e feature non realmente utilizzate."

## Evidence Inventory

| Source                  | Status      | Notes                                                     |
| ----------------------- | ----------- | --------------------------------------------------------- |
| Source code (backend)   | Available   | 143 file .py, 15.663 righe, 47 file >100 righe            |
| Frontend API calls      | Available   | 22 file API .ts, coverage completa                        |
| Tests (backend)         | Available   | 66 file test, buona copertura                             |
| Git history             | Available   | 370 commit su backend, ~100 solo ultimo mese              |
| Schemas inventory       | Available   | 30 schemi Pydantic, alcuni non esportati in `__init__`    |
| Models inventory        | Available   | 24 modelli SQLAlchemy, tutti referenziati                 |
| Dependency analysis     | Complete    | Nessuna dipendenza inutilizzata                           |
| Dead endpoint analysis  | Complete    | 31 router registrati, tutti con API frontend corrispondente |
| Code smell analysis     | Complete    | Vedi sezione Confirmed Findings                           |
| Duplicate code analysis | Partial     | Pattern visibili, ma non ho eseguito tool deduplicazione  |

## Investigation Backlog

| # | Path to Explore                             | Priority | Status    | Notes                                                              |
| - | ------------------------------------------- | -------- | --------- | ------------------------------------------------------------------ |
| 1 | Decomporre `mcp/server.py` in moduli        | High     | Open      | 1360 righe, 55+ funzioni, 6 domini accorpati                      |
| 2 | Estrarre helper terminal creation           | High     | Open      | `create_terminal` e `create_ask_terminal` ~80 righe identiche     |
| 3 | Unificare storage layer (DB vs file-backed) | Medium   | Open      | `issue_store.py` dataclass duplica modelli ORM                    |
| 4 | Verificare `mcp/plugin_*.py` duplicazione   | Medium   | Open      | 4 file plugin (client, manager, config, proxy) forse overlap      |
| 5 | Verificare `main.py` responsabilità         | Medium   | Open      | 368 righe con startup, router registry e error handlers           |
| 6 | Valutare eliminazione `desktop_icon.py`     | Low      | Open      | Feature desktop probabilmente poco usata                          |
| 7 | Verificare `credentials_editor` vs `credentials` duplicazione | Low | Open | Due router credentials separati, forse unificabili |
| 8 | Rimuovere schemi/models non in `__all__`    | Low      | Open      | Se non esportati, forse non servono                               |

## Confirmed Findings

### Finding 1: God File — `mcp/server.py` (1.360 righe)

**Evidence:** `backend/app/mcp/server.py` — 1.360 linee, 55+ funzioni `@mcp.tool`.

**Detail:** Questo file contiene TUTTI i tool MCP dell'applicazione, coprendo 6 domini distinti:
1. Issue tools (get_issue_details, get_issue_status, create_issue, set_issue_name, complete_issue, create_spec, edit_spec, create_plan, edit_plan, accept_issue, cancel_issue, force_finish_issue)
2. Memory tools (memory_create, memory_update, memory_delete, memory_link, memory_unlink)
3. File tools (list_project_files, read_project_file)
4. Pipeline tools (create_pipeline, run_pipeline, add_step, remove_step, reorder_steps, add_event_rule, etc.)
5. Plugin tools (list_plugins, get_plugin_config, enable_plugin, disable_plugin)
6. Credential tools (list_credentials, get_credential, set_credential, delete_credential)
7. Agent tools (create_agent, list_agents, get_agent, update_agent, delete_agent)
8. Project tools (get_project_context, update_project_context)
9. UI tools (ask_user_question)

**Pattern ripetitivo** — quasi ogni tool segue ESATTAMENTE questa struttura:
```python
@mcp.tool(description=...)
@mcp_tool_wrapper
async def some_tool(session, project_id: str, issue_id: str, ...) -> dict:
    service = SomeService(session)
    result = await service.some_method(...)
    await session.commit()
    await event_service.emit({...})
    return {...}
```

Questa struttura si ripete identica ~30 volte. Una decorator-factory o un base class handler ridurrebbe il codice del 40-50%.

### Finding 2: Duplicazione massiccia — `routers/terminals.py` (645 righe)

**Evidence:** `backend/app/routers/terminals.py:93-342` — `create_terminal` (riga 93) e `create_ask_terminal` (riga 234).

**Detail:** Le due funzioni condividono ~80 righe di logica identica:
- Lookup project path + validazione
- Fetch project shell config + WSL distro
- `service.create(...)` call con try/except identico
- WSL path translation + `cd` injection
- Env var injection (MANAGER_AI_TERMINAL_ID, MANAGER_AI_PROJECT_ID, MANAGER_AI_BASE_URL)
- WSL host IP resolution (if/else per WSL vs Windows)
- Custom project variable injection
- Gestione errori con warning logger

La differenza è solo: (a) `create_ask_terminal` fa teardown dei terminali esistenti prima, (b) esclude `MANAGER_AI_ISSUE_ID`, (c) inietta `ask_brainstorm_command` invece di `run_commands`.

`create_manage_agent_terminal` (riga 343) e `create_log_terminal` (riga 424) seguono pattern simile ma con varianti maggiori.

### Finding 3: Doppio storage layer — ORM models vs file-backed dataclass

**Evidence:** `backend/app/storage/issue_store.py:13-55` definisce `TaskRecord`, `RelationRecord`, `FeedbackRecord`, `IssueRecord` come dataclass. `backend/app/models/` definisce `Task`, `Issue`, `IssueFeedback`, `IssueRelation` come modelli SQLAlchemy.

**Detail:** Issue e Task hanno DUE rappresentazioni:
- **Modelli ORM** (`models/issue.py`, `models/task.py`): usati per query DB, relazioni, hook
- **Dataclass file-backed** (`storage/issue_store.py`): usati per read/write su filesystem `.manager_ai/`

I campi sono quasi identici. La logica di serializzazione/deserializzazione (frontmatter parsing, file I/O) è in `issue_store.py` e `memory_store.py`. Questo crea:
- Duplicazione di definizioni (cambiamenti vanno fatti in due posti)
- Overhead di conversione (`from_record()` sui Pydantic schema)
- Complessità cognitiva (capire "dov'è il source of truth?")

### Finding 4: Classe Linux PTY embedded in `terminal_service.py`

**Evidence:** `backend/app/services/terminal_service.py:33-50` — classe `PTY` per Linux definita dentro lo stesso file del servizio terminal.

**Detail:** Su piattaforme non-Windows, viene definita una classe PTY completa (con `spawn`, resize, read, write) dentro `terminal_service.py` invece che in un modulo separato. Questo mescola l'implementazione del servizio con l'implementazione del driver PTY. Su Windows, usa `winpty.PTY` da libreria esterna. La classe Linux PTY non è testabile isolatamente.

### Finding 5: `main.py` responsabilità multiple (368 righe)

**Evidence:** `backend/app/main.py` — 368 righe che gestiscono:
1. Import e registrazione di 31 router
2. Lifespan startup (DB init, secret key, write queue, proactor policy, event service, MCP mount)
3. Error handlers globali
4. CORS middleware
5. Avvio server

**Detail:** Non eccessivo ma al limite. La sezione startup (lifespan) ha già una decomposizione parziale in helper `_startup_*`, ma merita un modulo separato `app/startup.py`.

### Finding 6: Schema e Model gap — non tutto è in `__all__`

**Evidence:** `backend/app/schemas/__init__.py` esporta solo 14 schemas su ~30 esistenti.

**Detail:** Schemi non esportati: `activity.py`, `credential.py`, `credential_preset.py`, `export_import.py`, `library.py`, `memory.py`, `project_file.py`, `project_link.py`, `project_setting.py`, `project_variable.py`, `prompt_template.py`, `question.py`, `setting.py`, `system.py`, `terminal.py`, `terminal_command.py`, `pipeline_event_rule.py`. 

Questi sono comunque importati direttamente dai router che li usano, quindi non sono "morti", ma l'`__init__` incoerente è un code smell organizzativo.

## Deduced Conclusions

### Deduction 1: Il pattern MCP tool è un candidato perfetto per una factory/generatore

**Based on:** Finding 1 — 30+ tool MCP con struttura identica.

**Reasoning:** Ogni tool MCP segue lo schema: crea servizio → chiama metodo → commit → emetti evento → return dict. Questo è un caso da libro di testo per un decorator o una funzione factory che genera tool dinamicamente. Una soluzione basata su registrazione dichiarativa o class-based handler ridurrebbe `server.py` da 1.360 a ~500 righe.

**Conclusion:** Il refactor #1 prioritario è decomporre `mcp/server.py` in moduli per dominio, e introdurre un pattern che elimini la duplicazione boilerplate.

### Deduction 2: La creazione terminal ha un "template method" non estratto

**Based on:** Finding 2 — `create_terminal` e `create_ask_terminal` condividono ~80% di logica.

**Reasoning:** Estraendo un helper `_prepare_terminal_environment(service, terminal, project_path, project_shell, project_wsl_distro, env_extra)` si eliminerebbero ~100 righe di duplicazione. Le varianti (ask, manage-agent, log) differiscono solo per: (1) pre-conditions, (2) env vars subsets, (3) comandi startup.

**Conclusion:** Refactor medio-prioritario con impatto immediato sulla manutenibilità.

### Deduction 3: Storage layer duale è un debito architetturale

**Based on:** Finding 3 — ORM models + file-backed dataclass coesistono.

**Reasoning:** Il progetto è migrato da DB-centrico a file-centrico per issues/memories. I modelli ORM esistono ancora per progetti, pipeline, agents e per le relazioni DB. La convivenza è funzionale ma aumenta la superficie di bug (es. un aggiornamento a `IssueRecord` richiede aggiornare anche il modello ORM se serve per hook/query). Non è un bloccante ma è debito da gestire.

**Conclusion:** Refactor a medio termine. Valutare se eliminare i modelli ORM per issue/task/feedback o unificare con un adapter pattern.

## Hypothesized Paths

### Hypothesis 1: Feature desktop (`desktop_icon.py`, pywebview) è inutilizzata

**Status:** Open

**Theory:** Il file `backend/app/desktop_icon.py` (2.423 righe? No, 2.423 byte) e le dipendenze pywebview/pythonnet sono per una UI desktop separata dal frontend web. Potrebbe essere un esperimento abbandonato o una feature usata raramente.

**Supporting indicators:** La feature non ha API frontend associata nel codice React. Non ci sono route registrate per funzioni desktop.

**Would confirm:** Cercare riferimenti a `desktop_icon` o `pywebview` in frontend o in user docs.

**Would refute:** Trovare utenti che usano attivamente la UI desktop o documentazione che la descrive come integrata.

**Resolution:** Open — da verificare con Jacob.

### Hypothesis 2: Plugin system ha overlap tra `plugin_client.py`, `plugin_manager.py`, `plugin_proxy.py`

**Status:** Open

**Theory:** Il sistema MCP plugin ha 4 file nella cartella `mcp/`: `plugin_client.py` (366 righe), `plugin_manager.py` (303 righe), `plugin_proxy.py` (244 righe), `plugin_config.py` (128 righe). Potrebbero avere responsabilità sovrapposte o confini poco chiari.

**Supporting indicators:** La complessità di 4 file per un sistema di plugin suggerisce possibili overlap. Il `catalog.py` (111 righe) aggiunge un quinto.

**Would confirm:** Leggere i 4 file e mappare dipendenze incrociate.

**Would refute:** Trovare che ogni file ha una responsabilità distinta e non overlapping.

**Resolution:** Open — da verificare.

## Missing Evidence

| Gap                       | Impact                                    | How to Obtain                      |
| ------------------------- | ----------------------------------------- | ---------------------------------- |
| Test coverage per modulo  | Non so quali aree sono fragili            | `pytest --cov`                     |
| Duplicazione esatta righe | Non ho conteggio preciso overlap plugin   | Strumento deduplicazione (pylint)  |
| Utilizzo reale feature    | Non so se desktop_icon è usato            | Chiedere a Jacob                   |
| Performance profiling     | Non so quali endpoint sono lenti          | APM o profiling                    |
| Frontend page usage       | Non so quali pagine frontend sono usate   | Analytics o chiedere a Jacob       |

## Source Code Trace

| Element             | Detail                                                    |
| ------------------- | --------------------------------------------------------- |
| God file #1         | `backend/app/mcp/server.py:1-1360` — 55+ tool functions   |
| Duplicazione #1     | `backend/app/routers/terminals.py:93-234` vs `:234-342`   |
| Duplicazione #2     | `backend/app/storage/issue_store.py:13-55` vs models/     |
| Linux PTY embedded  | `backend/app/services/terminal_service.py:33+`            |
| Startup complexity  | `backend/app/main.py` — lifespan + router registry        |
| Unused export gap   | `backend/app/schemas/__init__.py` — solo 14/30 esportati  |

## Conclusion

**Confidence:** High per i primi 3 finding (god file MCP, duplicazione terminal, doppio storage). Medium per il resto.

L'analisi forense del backend rivela che **il codice non ha feature morte o endpoint inutilizzati** — ogni router ha corrispondenza frontend, ogni modello è referenziato. Non ci sono `except:` nudi, `eval()`, o password hardcoded. La qualità sintattica è buona.

I problemi sono **strutturali/organizzativi**:
1. **CRITICO:** `mcp/server.py` è ingestibile a 1.360 righe — decomporre per dominio (6 moduli)
2. **ALTO:** Duplicazione terminal creation — estrarre helper comune
3. **MEDIO:** Doppio storage layer — decidere se unificare o accettare
4. **BASSO:** Schemi non in `__all__`, Linux PTY embedded, startup monolitico

## Recommended Next Steps

### Fix direction

1. **Refactor MCP server** (`bmad-quick-dev` o `bmad-create-story`):
   - Creare `app/mcp/tools/issues.py`, `app/mcp/tools/memories.py`, `app/mcp/tools/pipelines.py`, `app/mcp/tools/plugins.py`, `app/mcp/tools/credentials.py`, `app/mcp/tools/projects.py`
   - Introdurre decorator/base class che automatizzi il pattern: service call → commit → event → return
   - Mantenere `server.py` come entry point che registra i moduli

2. **Estrarre helper terminal** (`bmad-quick-dev`):
   - Creare `_prepare_terminal_env(service, terminal, project_path, project_shell, wsl_distro, env_vars, custom_vars)`
   - Refactorare i 4 endpoint creation per usare l'helper
   - Stimato: -100 righe, +chiarezza

3. **Valutare unificazione storage** (decisione architetturale):
   - Opzione A: Eliminare `issue_store.py` e usare solo DB (breaking change)
   - Opzione B: Eliminare modelli ORM per issue/task e usare solo file-backed (coerente con architettura attuale)
   - Opzione C: Accettare dualità e non fare nulla (debito gestibile)

### Diagnostic

- Eseguire `pytest --cov` per identificare aree scoperte
- Chiedere a Jacob: desktop_icon serve ancora? Feature pywebview è usata?

## Reproduction Plan

N/A — non è un bug, è audit strutturale.

## Side Findings

- Il codice è sorprendentemente pulito per assenza di TODO/FIXME/HACK (zero occurrences)
- Tutti i router hanno API frontend corrispondente (31/31) — buona disciplina
- 66 file test per 143 file sorgente = 46% ratio test/sorgente, buono
- L'architettura file-backed (`storage/`) vs DB (`models/`) è una migrazione in corso, non finita
- `pyproject.toml` nel backend ha `asyncio_mode = "auto"` ma alcuni file di test potrebbero non rispettarlo

## Follow-up: 2026-06-07

### Nuove evidenze da raccogliere
- [ ] Verificare overlap tra `plugin_client.py`, `plugin_manager.py`, `plugin_proxy.py`
- [ ] Eseguire `pylint` con `--disable=all --enable=duplicate-code`
- [ ] Verificare se `create_log_terminal` e `create_manage_agent_terminal` condividono pattern
