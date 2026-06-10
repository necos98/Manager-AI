# Unit Test per IssueQueueService

## Obiettivo

Creare copertura unitaria completa per `IssueQueueService` (`backend/app/services/issue_queue_service.py`), le sue classi helper (`QueueEntry`, `QueueEntryStatus` in `backend/app/models/queue_entry.py`), e il suo ciclo di vita FIFO evento-driven.

## Panoramica del sistema

`IssueQueueService` è un `BaseNotifier` registrato su `EventService` all'avvio. Ascolta eventi `issue_status_changed` e gestisce la coda FIFO persistente via tabella `queue_entries`. I punti salienti dell'architettura:

- **QueueEntry** — Modello SQLAlchemy con status: PENDING → DISPATCHING → DISPATCHED / FAILED
- **Registrazione FIFO** — Ogni `register()` assegna `order = max_order + 1` per progetto, serializzato via per-project `asyncio.Lock`
- **Event-driven** — Eventi Finished → mark_dispatched + dequeue next; Queued → register + maybe_auto_start; Reasoning → mark_dispatching
- **Auto-start** — `_maybe_auto_start_first()` avvia la prima issue se è l'unica in coda e nessuna è in esecuzione
- **Race safety** — `_dequeue_and_run()` marca DISPATCHING *prima* di emettere eventi, così eventi Finished concorrenti non trovano l'entry ancora PENDING
- **Disable toggle** — `_enabled = False` fa skippare tutto il notify()
- **Startup resume** — All'avvio, scansiona progetti con pending entries e auto-avvia se nessuna issue è running

## Test da implementare

### 1. QueueEntry model & QueueEntryStatus
- Verificare che QueueEntryStatus enum abbia tutti i valori (PENDING, DISPATCHING, DISPATCHED, FAILED)
- Verificare che QueueEntry crei campi con default corretti (id UUID, status PENDING, etc.)

### 2. Constructor & Registration
- Verificare che IssueQueueService.__init__() chiami event_service.register(self)
- Verificare che imposti issue_queue_service_ref globale

### 3. register(issue_id, project_id)
- Crea QueueEntry con order auto-incrementante per progetto
- Due progetti separati hanno order indipendenti
- Order parte da 1 se non ci sono entries

### 4. mark_dispatching(issue_id)
- PENDING → DISPATCHING con dispatched_at impostato
- Se già DISPATCHING, no-op (ritorna entry senza errore)
- Se nessun entry trovato, ritorna None

### 5. mark_dispatched(issue_id)
- DISPATCHING → DISPATCHED
- PENDING → DISPATCHED (rimozione manuale dalla coda)
- Nessun entry trovato → ritorna None

### 6. mark_failed(issue_id, error_message)
- DISPATCHING → FAILED con error_message
- PENDING → FAILED
- error_message troncato a 1000 caratteri
- Nessun entry → ritorna None

### 7. get_next_pending(project_id)
- Ritorna l'entry con order minore in stato PENDING
- Nessun pending → ritorna None
- Ignora entries DISPATCHING/DISPATCHED/FAILED

### 8. list_queue(project_id) & list_all_global()
- Ordine ASC per order
- Solo entries del progetto specificato (list_queue)
- Tutti i progetti (list_all_global)
- Campi serializzati correttamente

### 9. load_state() & set_enabled()
- load_state() carica settings "queue_auto_process" dal DB
- set_enabled(True) persiste e chiama startup_resume
- set_enabled(False) persiste disabled
- Default a disabled se settings non trovato

### 10. notify() event routing
- Ignora eventi con tipo != "issue_status_changed"
- Ignora eventi quando _enabled=False
- Finished → chiama _on_issue_finished (mark_dispatched + dequeue)
- Queued → chiama _on_issue_queued (register + maybe_auto_start)
- Reasoning → chiama _on_issue_reasoning (mark_dispatching)

### 11. _on_issue_finished
- Chiama mark_dispatched(issue_id)
- Chiama _dequeue_and_run(project_id)
- Doppio Finished sulla stessa issue: mark_dispatched restituisce None la seconda volta (entry già DISPATCHED), _dequeue_and_run continua comunque

### 12. _dequeue_and_run
- Prende per-project lock
- get_next_pending → mark_dispatching → update_status a REASONING → emit evento → run_issue
- Se run_issue fallisce → mark_failed
- Nessun pending → esce senza fare nulla
- Race window chiusa: mark_dispatching chiamato prima di emettere eventi

### 13. _maybe_auto_start_first
- Non fa nulla se pending_count != 1
- Non fa nulla se c'è già una issue running (REASONING)
- Chiama _dequeue_and_run se pending_count==1 e nessuna running

### 14. startup_resume
- Se disabled → skip
- Trova progetti con pending entries
- Auto-avvia solo progetti senza issue REASONING in esecuzione

### 15. get_pending_entry
- Ritorna QueueEntry PENDING per issue_id specifico
- None se non esiste

### 16. FIFO multi-progetto
- Code indipendenti per progetti diversi
- QueueEntries di progetto A non influenzano progetto B
- Dispatch FIFO corretto all'interno di ogni progetto

## Strategia di test

Utilizzare il fixture `db_session` dal conftest esistente (SQLite in-memory), con le seguenti tecniche:

- **Patches necessarie**: `app.services.issue_queue_service.async_session` → test sessionmaker; `run_issue` → AsyncMock; `_emit_event` → AsyncMock
- **Setup**: Creare progetti via ProjectService nel test DB; Creare QueueEntries direttamente via db_session per setup
- **Verifica**: Leggere lo stato del DB dopo ogni operazione per assert; usare AsyncMock per verificare chiamate a run_issue/_emit_event
- **Race conditio**n: Test sincrono dei lock (non serve concorrenza reale — i lock sono asyncio.Lock; testare che lo stato sia corretto dopo operazioni sequenziali simulate)

## File da creare

`backend/tests/test_issue_queue_service.py` — Nuovo file di test con tutti i test sopra.
