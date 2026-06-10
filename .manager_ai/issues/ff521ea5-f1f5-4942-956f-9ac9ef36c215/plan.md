# Piano di implementazione: Test per IssueQueueService

## Strategia

Creare `backend/tests/test_issue_queue_service.py` con test strutturati in classi per dominio, usando il fixture `db_session` del conftest esistente. Ogni gruppo di test ha il suo fixture per setup.

L'approccio di test usa:
- `db_session` (in-memory SQLite) per operazioni DB
- Patch di `app.services.issue_queue_service.async_session` con sessionmaker che torna la test session
- AsyncMock per `app.services.issue_queue_service.run_issue` e `_emit_event`
- Creazione progetti via `ProjectService(db_session).create()` per IssueService lookups
- QueueEntries create direttamente via `db_session` per setup

## Task

### Task 1: Test di base — QueueEntry model, QueueEntryStatus, constructor
- Testare valori enum QueueEntryStatus
- Testare creazione QueueEntry con default
- Testare IssueQueueService.__init__() registration su EventService e module-level ref
- Testare che _enabled parta False

### Task 2: Test registry CRUD — register, mark_dispatching, mark_dispatched, mark_failed
- register() con auto-increment order, order indipendenti per progetto
- mark_dispatching() PENDING→DISPATCHING, già DISPATCHING no-op, missing entry None
- mark_dispatched() da DISPATCHING e da PENDING (rimozione manuale), missing → None
- mark_failed() da DISPATCHING/PENDING, error_message troncato 1000, missing → None

### Task 3: Test query — get_next_pending, list_queue, list_all_global, get_pending_entry
- get_next_pending() order FIFO corretto, no pending → None, ignora non-PENDING
- list_queue() ordine ASC per progetto, filtra per progetto
- list_all_global() tutte le entries
- get_pending_entry() per issue_id specifico

### Task 4: Test event handling — notify routing + _on_issue_finished/queued/reasoning
- notify() ignora eventi non issue_status_changed
- notify() ignora quando _enabled=False
- Finished → mark_dispatched + _dequeue_and_run
- Queued → register + _maybe_auto_start_first
- Reasoning → mark_dispatching
- Doppio Finished sulla stessa issue

### Task 5: Test auto-start e dequeue — _dequeue_and_run, _maybe_auto_start_first, startup_resume
- _dequeue_and_run() con pending → mark_dispatching + update_status + emit + run_issue
- _dequeue_and_run() con run_issue che fallisce → mark_failed
- _dequeue_and_run() nessun pending → no-op
- _maybe_auto_start_first() solo se pending_count==1 e nessuna running
- startup_resume() disabled → skip
- startup_resume() enabled → trova pending, auto-avvia se nessuna running

### Task 6: Test configurazione — load_state, set_enabled
- load_state() carica da settings DB
- load_state() default disabled se settings assente
- set_enabled(True) persiste e chiama startup_resume
- set_enabled(False) persiste disabled

### Task 7: Test FIFO multi-progetto
- Code indipendenti: entries progetto A non influenzano B
- Order indipendenti per progetto
- Dispatch corretto all'interno di ogni progetto
