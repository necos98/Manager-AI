## Queue Registry - Implementazione completata

### Cosa è stato fatto

**Task 1** — Nuovo modello `QueueEntry` in `backend/app/models/queue_entry.py` con:
- Enum `QueueEntryStatus`: pending, dispatching, dispatched, failed
- Colonna `order` per FIFO incrementale per progetto
- `dispatched_at` e `error_message` per tracciabilità
- Registrato in `models/__init__.py` per discovery Alembic

**Task 2** — `IssueQueueService` esteso con metodi QueueRegistryService:
- `register()`, `mark_dispatching()`, `mark_dispatched()`, `mark_failed()`
- `get_next_pending()`, `list_queue()`, `list_all_global()`
- `_dequeue_and_run()` ora usa `get_next_pending()` invece di `list_by_project(status=QUEUED)`
- Flusso eventi ristrutturato: `_on_issue_queued` → register, `_on_issue_reasoning` → mark_dispatching, `_on_issue_finished` → mark_dispatched + dequeue
- `_maybe_auto_start_first()` usa QueueEntry count invece di QUEUED status count

**Task 3** — MCP shared_tools aggiornati:
- `queue_list()` usa `registry.list_queue()` (filtra pending) invece di query su QUEUED status
- `queue_remove()` marca QueueEntry come dispatched
- `queue_position()` usa registry per calcolare posizione FIFO
- `queue_add()` non modificato — l'evento Queued triggera già register()

**Task 4** — Migration DB generata e applicata (`777aa4b0afca`)

**Task 5** — Verifica con 11 test su flusso completo + edge cases (tutti passati)

### Vantaggi ottenuti
- Registro persistente su DB (resiliente a restart)
- FIFO garantito da `order` incrementale, non da status volatile
- Tracciabilità completa: `dispatched_at` su ogni dispacciamento
- Nessuna perdita di riferimenti: anche se l'issue cambia status, QueueEntry rimane
- Base per UI globale della coda via `list_all_global()`