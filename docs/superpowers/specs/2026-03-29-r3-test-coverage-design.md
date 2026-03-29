# R3 — Test Coverage: Design Spec

**Data:** 2026-03-29
**Approccio:** Opzione A — revisione + gap filling. Ogni item `[ ]` del roadmap ottiene almeno un test solido; i test esistenti deboli vengono rafforzati; le 4 lacune reali vengono colmate.

---

## Contesto

R3 copre i percorsi critici non ancora testati del sistema. L'esplorazione del codebase ha rivelato che molti test esistono già (scritti in sessioni precedenti), ma alcuni casi edge mancano e altri potrebbero essere rafforzati. Il piano non butta il lavoro fatto: rivede, integra, e aggiunge.

---

## R3.1 — Servizi core

### `test_terminal_service.py`

Stato attuale: buona copertura per create/kill/resize/cleanup/concurrent. Mancano casi sul buffer.

**Da aggiungere:**

- `test_append_output_overflow_trims_from_front`
  Appende dati superiori a `MAX_BUFFER_SIZE`. Verifica che il buffer non superi il limite e che i byte più vecchi (fronte) vengano eliminati, non quelli recenti.

- `test_append_output_unknown_terminal_is_noop`
  Chiama `append_output` con un `terminal_id` inesistente. Non deve sollevare eccezioni.

- `test_get_buffered_output_empty`
  Su un terminal appena creato (nessun output ancora), `get_buffered_output` deve restituire `""`.

### `test_issue_service.py`

Stato attuale: `test_complete_issue_blocks_when_lock_held` verifica che il lock serializzi. Manca il caso in cui due task reali si contendono la stessa issue.

**Da aggiungere:**

- `test_complete_issue_concurrent_two_tasks`
  Due `asyncio.create_task` lanciano `complete_issue` sulla stessa issue contemporaneamente. Il primo deve completare con `FINISHED`; il secondo deve ricevere `InvalidTransitionError` (l'issue è già FINISHED). Nessun crash, nessuno stato corrotto.

### `test_rag_service.py`

Stato attuale: i test usano mock del pipeline, non testano la concorrenza del lock.

**Da aggiungere:**

- `test_source_lock_serializes_concurrent_calls`
  N coroutine concorrenti chiamano operazioni che acquisiscono `_source_lock` sullo stesso `source_id`. Verifica che: (1) l'esecuzione sia serializzata (contatore degli accessi sovrapposti = 0), (2) `_source_locks` venga pulito dopo l'ultima coroutine (nessun leak).

---

## R3.2 — Hook system

### `test_hook_registry.py`

Stato attuale: `_run_hook` è ben testato per eccezione, timeout, eventi. Manca il test che verifica che il *chiamante* di `fire()` non riceva eccezioni.

**Da aggiungere:**

- `test_fire_does_not_raise_when_hook_throws`
  Registra un hook che lancia `RuntimeError`. Chiama `registry.fire(...)` e `await asyncio.sleep(0.1)`. Verifica che nessuna eccezione raggiunga il test (il fire è fire-and-forget).

- `test_issue_created_hook_end_to_end`
  Crea una issue reale su DB (senza mockare `hook_registry`). Verifica che `hook_registry._background_tasks` contenga almeno una task dopo `service.create(...)`, oppure che `fire` sia stato chiamato con `HookEvent.ISSUE_CREATED`. Testa il trigger reale, non il mock.

---

## R3.3 — Router terminali

### `test_terminal_router.py`

Stato attuale: copre list/create/delete via REST. Mancano WebSocket e resize su terminal inesistente.

**Da aggiungere:**

- `test_resize_service_nonexistent_raises_key_error`
  Il resize avviene via messaggio WebSocket, non via REST endpoint. Il comportamento atteso a livello servizio: `service.resize("nonexistent", 100, 25)` solleva `KeyError`. Test diretto sul servizio (non sul router), documentato come comportamento "404-equivalente" in caso di integrazione futura.

- `test_websocket_disconnect_calls_cleanup`
  Apre una connessione WebSocket verso `/{terminal_id}/ws` usando un mock del `TerminalService`. Disconnette il client. Verifica che `service.cleanup(terminal_id)` sia stato chiamato (il `finally` nel router garantisce PTY cleanup su disconnect brusco).

---

## R3.4 — MCP tools

### `test_r2_mcp_transactions.py`

Stato attuale: copre `AppError` no-commit per due tool. Mancano `get_project_context` con UUID inesistente e rollback su errore DB.

**Da aggiungere:**

- `test_mcp_get_project_context_nonexistent_returns_error`
  Chiama `get_project_context` con un UUID inesistente. Verifica che il risultato contenga `{"error": ...}` (non sollevi eccezione non gestita).

- `test_complete_issue_mcp_no_commit_on_db_error`
  Simula un errore DB durante `complete_issue` MCP tool (il service lancia `Exception`). Verifica che `session.commit()` non venga chiamato.

---

## File coinvolti

| File | Azione |
|------|--------|
| `backend/tests/test_terminal_service.py` | Aggiungere 3 test buffer |
| `backend/tests/test_issue_service.py` | Aggiungere 1 test concurrent tasks |
| `backend/tests/test_rag_service.py` | Aggiungere 1 test lock concurrency |
| `backend/tests/test_hook_registry.py` | Aggiungere 2 test (fire no-raise, e2e) |
| `backend/tests/test_terminal_router.py` | Aggiungere 2 test (resize KeyError, WS cleanup) |
| `backend/tests/test_r2_mcp_transactions.py` | Aggiungere 2 test (project 404, no-commit on error) |

**Totale: 11 nuovi test** distribuiti in 6 file esistenti. Nessun nuovo file creato.

---

## Criteri di successo

- Tutti i `[ ]` di R3.1–R3.4 nel roadmap hanno un test verificabile che li copre.
- `pytest` passa senza warning su tutti i file modificati.
- I test di concorrenza non sono flaky (usano lock/asyncio controllati, non sleep arbitrari).
- I test WebSocket usano `httpx` + `ASGITransport` come il resto della suite.
