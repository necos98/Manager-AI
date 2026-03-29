# R1 — Affidabilità del Core: Design Spec

**Data:** 2026-03-29
**Scope:** Correggere i punti dove il sistema può lasciare stato inconsistente o perdere task asincrone silenziosamente. Basato su gap-analysis del codice reale rispetto alla ROADMAP — include solo ciò che effettivamente manca.

---

## Contesto

Questo documento copre quattro aree di R1. Due item della ROADMAP originale (R1.2 hook error propagation, R1.4 RAG embed logging nel service) risultano già implementati nel codice corrente; il piano si concentra sui gap reali.

---

## R1.1 — Race condition su `complete_issue`

### Problema

`issue_service.complete_issue()` esegue in sequenza:
1. Check task pending
2. `issue.status = FINISHED`
3. `session.flush()`

Due richieste concorrenti sulla stessa issue possono entrambe superare il check al passo 1 prima che una delle due esegua il flush, risultando in doppio completamento o stato inconsistente.

### Soluzione

Un `dict[str, asyncio.Lock]` module-level in `issue_service.py` mappa `issue_id → Lock`. `complete_issue` acquisisce il lock per l'issue prima di entrare nel check/flush.

**Flusso:**
```
acquire _issue_locks[issue_id]
  → check pending tasks
  → issue.status = FINISHED
  → session.flush()
  → fire hook
finally:
  release lock
  remove lock from dict
```

La seconda chiamata concorrente acquisirà il lock dopo il flush della prima e riceverà `InvalidTransitionError` perché l'issue sarà già FINISHED — comportamento corretto. Chi era già in attesa sul lock tiene un riferimento diretto, quindi la rimozione dal dict non lo disturba.

**File:** `backend/app/services/issue_service.py`

---

## R1.2 — Hook timeout e task tracking

### Problema

`HookRegistry.fire()` chiama `asyncio.create_task()` senza salvare il riferimento alla task. In Python, una task non referenziata può essere garbage-collected prima del completamento. Inoltre non esiste un timeout per l'esecuzione di un hook, quindi un hook bloccato rimane in esecuzione indefinitamente.

La gestione errori (log, eventi `hook_failed`, activity) è già presente e corretta — non viene modificata.

### Soluzione

**Task tracking:** aggiungere `_background_tasks: set[asyncio.Task]` come attributo di `HookRegistry`. Pattern standard:

```python
task = asyncio.create_task(self._run_hook(hook_class, context))
self._background_tasks.add(task)
task.add_done_callback(self._background_tasks.discard)
```

**Timeout:** in `_run_hook`, wrappare `hook.execute(context)` con `asyncio.wait_for(..., timeout=300)`. `asyncio.TimeoutError` viene catturato e trattato come le altre eccezioni: log + evento `hook_failed` + activity log.

Il timeout è hardcoded a 300s. Renderlo configurabile richiederebbe un sistema di config per gli hook non ancora presente — fuori scope.

**File:** `backend/app/hooks/registry.py`

---

## R1.3 — PTY cleanup garantito e resize lock

### Problema A — PTY non liberata su disconnect brusco

Il WebSocket handler `terminal_ws` in `terminals.py` usa `asyncio.wait()` per attendere il completamento di `pty_to_ws` o `ws_to_pty`. Quando una delle due completa (es. disconnect del client), le task pendenti vengono cancellate — ma non c'è un blocco `finally` che garantisca il cleanup della PTY.

Se la connessione cade bruscamente prima della normale chiusura, la PTY rimane in memoria.

### Soluzione A

Avvolgere il blocco `asyncio.wait` in `try/finally`. Nel `finally`, chiamare `service.cleanup(terminal_id)` — metodo nuovo, idempotente (no-op se il terminale non esiste).

```python
try:
    done, pending = await asyncio.wait([pty_read_task, ws_read_task],
                                       return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
except Exception:
    pty_read_task.cancel()
    ws_read_task.cancel()
finally:
    service.cleanup(terminal_id)
```

**File:** `backend/app/routers/terminals.py`

### Problema B — `resize()` fuori dal lock

`TerminalService.resize()` legge e muta `_terminals[terminal_id]` senza acquisire `self._lock`, mentre altri metodi (es. `kill()`, `mark_closed()`) lo acquisiscono. Race condition possibile se resize e close avvengono concorrentemente.

### Soluzione B

Spostare l'intero corpo di `resize()` dentro `with self._lock:`. La struttura del metodo rimane identica.

**File:** `backend/app/services/terminal_service.py`

---

## R1.4 — MCP embed task tracking

### Problema

In `mcp/server.py`, `asyncio.create_task(rag.embed_issue(...))` viene chiamato senza salvare il riferimento. La task può essere garbage-collected silenziosamente prima del completamento. Non c'è log del lancio della task.

La gestione errori in `rag_service.py` è già corretta (logger.exception + evento `embedding_failed`) — non viene toccata.

### Soluzione

Stesso pattern di R1.2: set module-level `_background_tasks` in `server.py`, task salvata e rimossa via `add_done_callback`. Logger debug con `issue_id` al momento del lancio.

```python
task = asyncio.create_task(rag.embed_issue(...))
_background_tasks.add(task)
task.add_done_callback(_background_tasks.discard)
logger.debug("embed_issue task started for issue %s", issue_id_val)
```

**File:** `backend/app/mcp/server.py`

---

## Test

Ogni area include un test che copre il percorso critico:

| Area | Test |
|------|------|
| R1.1 | Due chiamate `complete_issue` concorrenti sulla stessa issue: solo una deve avere successo, l'altra `InvalidTransitionError` |
| R1.2 | Hook che lancia eccezione: flusso principale non interrotto, evento `hook_failed` emesso; hook che supera 300s: cancellato con `hook_failed` |
| R1.3 | Disconnect WebSocket brusco: `service.cleanup` chiamato; `resize()` concorrente a `kill()`: nessun crash |
| R1.4 | Task embed creata: riferimento presente in `_background_tasks` durante esecuzione, rimosso al completamento |

---

## File modificati

| File | Motivo |
|------|--------|
| `backend/app/services/issue_service.py` | Lock per-issue in `complete_issue` |
| `backend/app/hooks/registry.py` | Task tracking + timeout 300s |
| `backend/app/routers/terminals.py` | `finally` block per PTY cleanup |
| `backend/app/services/terminal_service.py` | `resize()` dentro il lock; nuovo metodo `cleanup()` |
| `backend/app/mcp/server.py` | Task tracking per embed |
| `backend/tests/` | Test per ogni area |
