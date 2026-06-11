# Refactoring Issue Queue — Da stato-accoppiata a stato-indipendente

## Obiettivo

Rendere la coda FIFO "stupida": zero dipendenze da `IssueStatus` tranne il check `FINISHED` per determinare il completamento. La coda gestisce solo il proprio stato interno (`RUNNING` / `DONE`) e delega al `run_issue` la gestione dello stato dell'issue.

## Riepilogo flusso attuale vs nuovo

### Attuale (accoppiato a IssueStatus)

```
add_to_queue → valida NEW o ACCEPTED
             → QueueEntry PENDING
             → se nessuna issue REASONING → _dequeue_and_run()
                 → update_status(REASONING)   ← SIDE EFFECT
                 → run_issue()
_notify("issue_status_changed → Finished")
             → mark_dispatched()
             → _dequeue_and_run() prossima
```

Problemi:
- `add_to_queue()` rifiuta issue non in NEW/ACCEPTED (issue_queue_service.py:349-354)
- `_dequeue_and_run()` modifica IssueStatus a REASONING (issue_queue_service.py:597)
- `_count_active_reasoning()` inferisce "running" da IssueStatus + QueueEntry (issue_queue_service.py:463-493)
- Se `run_issue()` fallisce dopo `update_status(REASONING)`, issue resta REASONING ma QueueEntry è FAILED → ghost issue

### Nuovo (indipendente da IssueStatus)

```
add_to_queue → nessuna validazione stato issue
             → QueueEntry RUNNING (salta PENDING, va diretto)
             → TerminalService.list_active() per capire se c'è terminale vivo
             → se nessun RUNNING con terminale vivo → esegue subito
             → se c'è già un RUNNING → aspetta (event-driven)

notify("issue_status_changed → Finished")
             → cerca QueueEntry RUNNING per quell'issue
             → se trovato → mark DONE
             → cerca prossimo PENDING → RUNNING → run_issue()

Polling fallback (ogni N secondi):
             → per ogni QueueEntry RUNNING:
                 issue FINISHED? → DONE, prossimo
                 issue NOT FINISHED + terminale vivo? → aspetta
                 issue NOT FINISHED + terminale morto? → timeout → retry o FAILED
```

Vantaggi:
- `add_to_queue()` accetta issue in qualsiasi stato
- `_dequeue_and_run()` NON modifica IssueStatus
- Nessuna inferenza da IssueStatus per capire se sta girando
- Ghost issues impossibili: se terminale muore prima di FINISHED, la queue lo rileva

---

## QueueEntryStatus — Nuovi valori

**Prima:**
```python
class QueueEntryStatus(str, enum.Enum):
    PENDING = "pending"
    DISPATCHING = "dispatching"
    DISPATCHED = "dispatched"
    FAILED = "failed"
```

**Dopo:**
```python
class QueueEntryStatus(str, enum.Enum):
    PENDING = "pending"       # in attesa di essere processato
    RUNNING = "running"       # terminale spawnato, in esecuzione
    DONE = "done"             # completato (issue FINISHED)
    FAILED = "failed"         # errore durante spawn o timeout terminale
    STALLED = "stalled"       # RUNNING ma terminale morto senza FINISHED
```

`DISPATCHING` e `DISPATCHED` spariscono. Li sostituiscono `RUNNING` e `DONE`.

---

## Matrice decisionale della coda

Per ogni `QueueEntry` in stato `RUNNING`, la coda valuta:

| QueueEntry | Issue.status | terminal_id attivo | Azione |
|---|---|---|---|
| RUNNING | FINISHED | qualsiasi | → DONE, prendi prossimo PENDING |
| RUNNING | NOT FINISHED | Sì | aspetta (sta lavorando) |
| RUNNING | NOT FINISHED | No | → STALLED, dopo timeout X → retry (PENDING) o FAILED |
| PENDING | qualsiasi | — | se nessun RUNNING attivo → RUNNING + run_issue() |
| STALLED | NOT FINISHED | No (da > X sec) | → PENDING (retry) o FAILED (dopo N retry) |

Il `terminal_id` si recupera da `TerminalService.list_active(issue_id=...)`. È in RAM, quindi:
- Al restart del server, tutti i terminal_id spariscono
- Le QueueEntry RUNNING diventano STALLED dopo timeout
- STALLED → retry automatico → re-spawna terminale

---

## File modificati

### 1. `backend/app/models/queue_entry.py`

**Cosa cambia:**
- `QueueEntryStatus` enum: sostituire `DISPATCHING`/`DISPATCHED` con `RUNNING`/`DONE`/`STALLED`
- Aggiungere campi al model `QueueEntry`:
  - `retry_count: int` (default 0) — contatore retry per STALLED
  - `last_terminal_id: Optional[str]` — traccia ultimo terminale spawnato
  - `status_changed_at: Optional[datetime]` — timestamp ultimo cambio stato

**Migration Alembic necessaria:** Sì (nuove colonne + update valori enum)

### 2. `backend/app/services/issue_queue_service.py`

**Riscrittura maggiore.** Metodi da modificare:

#### `register()` (righe 68-96)
- **Prima**: imposta `status=PENDING`
- **Dopo**: imposta `status=PENDING` (invariato)

#### `add_to_queue()` (righe 327-374)
- **Prima**: valida `IssueStatus` in `{NEW, ACCEPTED}` (riga 349)
- **Dopo**: **Rimuovere validazione stato issue**. Qualsiasi issue può essere accodata.
- **Dopo**: emette evento `queue_entry_created` (invariato)

#### `_dequeue_and_run()` (righe 569-653)
- **Prima**: 
  1. `get_next_pending()` → `mark_dispatching()`
  2. `issue_service.update_status(REASONING)` ← **RIMUOVERE**
  3. `run_issue()` 
  4. Emette `issue_status_changed → Reasoning`
- **Dopo**:
  1. `get_next_pending()` → `mark_running()`
  2. `run_issue()` direttamente (NON tocca IssueStatus)
  3. Salva `terminal_id` restituito da `run_issue()` nel QueueEntry (`last_terminal_id`)
  4. **NON emette** `issue_status_changed` (la coda non modifica stato issue)
  5. Emette `queue_entry_running` (nuovo tipo evento)

#### `mark_running()` — NUOVO metodo
```python
async def mark_running(self, issue_id: str, terminal_id: str) -> Optional[QueueEntry]:
    """Mark a PENDING QueueEntry as RUNNING and record the terminal_id."""
```
Sostituisce `mark_dispatching()`.

#### `mark_done()` — NUOVO metodo
```python
async def mark_done(self, issue_id: str) -> Optional[QueueEntry]:
    """Mark a RUNNING QueueEntry as DONE."""
```
Sostituisce `mark_dispatched()`.

#### `mark_stalled()` — NUOVO metodo
```python
async def mark_stalled(self, issue_id: str) -> Optional[QueueEntry]:
    """Mark a RUNNING QueueEntry as STALLED (terminal died without FINISHED)."""
```

#### `mark_dispatched()` — RIMUOVERE
Sostituito da `mark_done()`.

#### `mark_dispatching()` — RIMUOVERE
Sostituito da `mark_running()`.

#### `get_next_pending()` (righe 176-191)
- **Prima**: filtra per `status == PENDING`
- **Dopo**: filtra per `status == PENDING` (invariato)

#### `_count_active_reasoning()` (righe 463-493)
- **RIMUOVERE completamente**. Sostituito da `_count_active_running()`.

#### `_count_active_running()` — NUOVO metodo
```python
async def _count_active_running(self, project_id: str) -> int:
    """Conta QueueEntry in stato RUNNING per questo progetto."""
```
Interroga `QueueEntry.status == RUNNING` direttamente. Non guarda IssueStatus.

#### `notify()` (righe 499-525) — Riscrittura logica eventi

**Prima:**
```python
if event_type == "issue_status_changed":
    if new_status == "Finished" and self._enabled:
        asyncio.create_task(self._on_issue_finished(project_id, issue_id))
    elif new_status == "Reasoning" and self._enabled:
        ...
```

**Dopo:**
```python
if event_type == "issue_status_changed" and new_status == "Finished":
    # Marca DONE solo se esiste QueueEntry RUNNING per questa issue
    # (verifica: QueueEntry.status == RUNNING, non si fida dell'evento)
    asyncio.create_task(self._on_issue_finished(project_id, issue_id))

if event_type == "queue_entry_created":
    # Auto-start se nessun RUNNING attivo per il progetto
    asyncio.create_task(self._on_issue_queued(project_id, issue_id))
```

#### `_on_issue_finished()` (righe 527-537) — Riscrittura
```python
async def _on_issue_finished(self, project_id: str, issue_id: str) -> None:
    """Issue FINISHED → cerca QueueEntry RUNNING → DONE → prossimo."""
    # 1. Cerca QueueEntry RUNNING per questa issue
    # 2. Se trovato → mark_done()
    # 3. Se non trovato → log warning (issue finita fuori dalla coda)
    # 4. _dequeue_and_run() prossimo PENDING
```

#### `_on_issue_queued()` (righe 539-557) — Semplificazione
- Rimuovere riferimento a `_on_issue_reasoning` (non esiste più)
- Usare `_count_active_running()` invece di `_count_active_reasoning()`

#### `_on_issue_reasoning()` (righe 559-567)
- **RIMUOVERE**. La coda non reagisce più a `issue_status_changed → Reasoning`.

#### `startup_resume()` (righe 244-284)
- **Prima**: cerca `QueueEntry.PENDING`, controlla `_count_active_reasoning()`, auto-start
- **Dopo**: cerca `QueueEntry.PENDING`, controlla `_count_active_running()`, auto-start
- **Dopo**: per ogni `QueueEntry.RUNNING` senza terminale attivo, marca `STALLED`

#### `remove_from_queue()` (righe 376-418)
- **Prima**: marca `DISPATCHED` (issue mantiene status originale)
- **Dopo**: se PENDING → marca `DONE` (rimosso prima di partire). Se RUNNING → errore (non si può rimuovere issue in esecuzione). Emette `queue_entry_removed`.

#### `list_queue()` (righe 193-217) — Aggiornare status renderizzati
- Aggiungere `last_terminal_id` e `retry_count` alla risposta

### 3. `backend/app/routers/queue.py`

**Modifiche minori:**

#### `GET /api/queue` (righe 83-134)
- Nessun cambiamento logico (filtra già per `PENDING`)

#### `GET /api/queue/running` (righe 137-181)
- **Prima**: interroga `TerminalService.list_active()` per terminali attivi
- **Dopo**: interroga `QueueEntry.status == RUNNING` come fonte primaria, incrocia con `TerminalService` per dettagli terminale

#### `GET /api/queue/status` (righe 184-230)
- **Prima**: conta `PENDING` + `DISPATCHING`
- **Dopo**: conta `PENDING` + `RUNNING` + `STALLED`

Schema `QueueStatus`:
```python
class QueueStatus(BaseModel):
    queued_count: int        # PENDING
    running_count: int       # RUNNING
    stalled_count: int       # STALLED (nuovo)
    paused: bool
    auto_process_enabled: bool
```

#### `GET /api/queue/position/{issue_id}` (righe 311-358)
- Aggiornare logica per cercare anche RUNNING, non solo PENDING

### 4. `backend/app/mcp/shared_tools.py`

**Modifiche minori:**

#### `queue_add()` (righe 1609-1628)
- **Prima**: delega a `IssueQueueService.add_to_queue()` che valida NEW/ACCEPTED
- **Dopo**: rimuovere il commento "Validates that the issue is in NEW or ACCEPTED status". Il comportamento è gestito dal service.

#### `queue_list()` (righe 1631-1670)
- Aggiornare per includere informazioni su `RUNNING` e `STALLED`

#### `queue_remove()` (righe 1673-1690)
- Aggiungere guard: non si può rimuovere issue con QueueEntry RUNNING

### 5. `backend/app/mcp/orchestrator_server.py`

- Import già aggiornati. Verificare che i nomi delle funzioni importate corrispondano.

### 6. `backend/app/main.py`

**Nessuna modifica strutturale.** L'inizializzazione di `IssueQueueService` (riga 306) e `startup_resume()` (riga 309) restano invariate.

### 7. `backend/app/services/terminal_service.py`

**Nessuna modifica.** Già espone `list_active(project_id, issue_id)` che useremo per incrociare RUNNING + terminale.

### 8. Frontend — Modifiche minori

#### `frontend/src/features/queue/api.ts`
- Aggiornare tipi per riflettere nuovi status (`running`, `done`, `stalled`)

#### `frontend/src/features/queue/hooks.ts`
- Aggiornare logica hook per nuovi status

#### `frontend/src/routes/queue.tsx`
- Badge/stato per RUNNING, STALLED

#### `frontend/src/features/projects/components/work-queue-status.tsx`
- Aggiornare conteggi (togliere `dispatching_count`, aggiungere `stalled_count`)

---

## Rimozioni

| Cosa | File | Righe |
|---|---|---|
| Validazione `NEW/ACCEPTED` in `add_to_queue` | `issue_queue_service.py` | 349-354 |
| `update_status(REASONING)` in `_dequeue_and_run` | `issue_queue_service.py` | 597-599 |
| `_count_active_reasoning()` | `issue_queue_service.py` | 463-493 |
| `_on_issue_reasoning()` | `issue_queue_service.py` | 559-567 |
| `mark_dispatching()` | `issue_queue_service.py` | 98-130 |
| `mark_dispatched()` | `issue_queue_service.py` | 132-151 |
| `_get_dispatching_by_issue()` | `issue_queue_service.py` | 448-461 |
| `_queue_dispatching_handled` guard in `notify()` | `issue_queue_service.py` | 522-523 |
| Enum `DISPATCHING`, `DISPATCHED` | `queue_entry.py` | 13-14 |

## Aggiunte

| Cosa | File |
|---|---|
| `mark_running(issue_id, terminal_id)` | `issue_queue_service.py` |
| `mark_done(issue_id)` | `issue_queue_service.py` |
| `mark_stalled(issue_id)` | `issue_queue_service.py` |
| `_count_active_running(project_id)` | `issue_queue_service.py` |
| `_find_running_entry(session, issue_id)` | `issue_queue_service.py` |
| Enum `RUNNING`, `DONE`, `STALLED` | `queue_entry.py` |
| Campi `retry_count`, `last_terminal_id`, `status_changed_at` | `queue_entry.py` |
| `stalled_count` in `QueueStatus` | `routers/queue.py` |

---

## Rollout

1. **Migration DB**: creare colonne `retry_count`, `last_terminal_id`, `status_changed_at` su `queue_entries`. Aggiornare enum values: `pending` resta, `dispatching` → `running`, `dispatched` → `done`, `failed` resta.
2. **Deploy backend**: nuovo codice non tocca stato issue, quindi rollback sicuro.
3. **Test manuale**:
   - Aggiungere issue in coda → deve spawnare terminale
   - Aggiungere seconda issue → deve aspettare (PENDING)
   - Completare prima issue (FINISHED) → seconda parte
   - Kill terminale senza FINISHED → dopo timeout → STALLED → retry
   - Riavvio server con issue RUNNING → STALLED → retry → funziona
4. **Frontend**: aggiornare label e badge (solo cosmetico, non bloccante)

---

## Non cambia

- `queue_auto_process` setting e toggle abilita/disabilita
- `TerminalService` — nessuna modifica
- `run_issue_service.py` — nessuna modifica
- `EventService` — nessuna modifica
- API REST `/api/queue/add`, `/api/queue/remove` — stessa firma, comportamento interno diverso
- MCP tools `queue_add`, `queue_remove`, `queue_list` — stessa firma
