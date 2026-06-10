## Implementation Plan: Queue Registry

### Overview

Aggiungere una tabella `queue_entries` e un `QueueRegistryService` per tracciare persistentemente lo stato di dispacciamento delle issue in coda. L'attuale `IssueQueueService` verrà esteso con metodi di registry. I tool MCP `queue_add/queue_list/queue_remove/queue_position` verranno aggiornati per usare il registry invece di query sullo status QUEUED.

### Tasks

**Task 1: Nuovo modello QueueEntry**
- Creare `backend/app/models/queue_entry.py` con SQLAlchemy model `QueueEntry`
- Colonne: id (UUID), issue_id, project_id, status (Enum: pending/dispatching/dispatched/failed), order (Integer), created_at, dispatched_at (nullable), error_message (nullable)
- Registrare in `__init__.py` per discovery automatica di Alembic

**Task 2: Aggiornare IssueQueueService → QueueRegistryService**
- Aggiungere metodi: register(), mark_dispatching(), mark_dispatched(), mark_failed(), get_next_pending(), list_queue(), list_all_global()
- Modificare _dequeue_and_run() per usare get_next_pending() invece di list_by_project(status=QUEUED)
- Modificare _maybe_auto_start_first() per chiamare register() e mark_dispatching()
- Aggiungere chiamate a mark_dispatching() quando QUEUED → REASONING, mark_dispatched() su Finished

**Task 3: Aggiornare MCP shared_tools**
- `queue_add()`: dopo status change a QUEUED, chiamare `registry.register()`
- `queue_list()`: usare `registry.list_queue()` invece di list_by_project(status=QUEUED)
- `queue_remove()`: oltre a cambiare status, marcare QueueEntry come dispatched
- `queue_position()`: usare registry per calcolare posizione FIFO

**Task 4: Database migration**
- Generare migration con `alembic revision --autogenerate`
- Applicare con `alembic upgrade head`

**Task 5: Verifica e test**
- Verificare che IssueQueueService si registri ancora come BaseNotifier
- Verificare che i tool MCP queue_* funzionino con il nuovo registry
- Testare il flusso: queue_add → register() → mark_dispatching() → mark_dispatched()
- Verificare che il registro sia persistente (leggere da DB dopo riavvio)
