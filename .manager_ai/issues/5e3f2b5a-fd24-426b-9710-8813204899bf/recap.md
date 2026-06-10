## Recap: Race condition ordine FIFO in register() — Fixed

### Problema
Due chiamate concorrenti a `IssueQueueService.register()` per lo stesso progetto aprivano sessioni DB separate. Entrambe leggevano lo stesso `max(order)` (nessuna aveva ancora committato) e creavano entry con lo stesso `order`, rompendo la garanzia FIFO.

### Fix applicati

**1. Lock applicativo per-progetto in register() (primario)**
- Nuovo `self._register_locks: dict[str, asyncio.Lock]` in `__init__()`
- Helper `_get_register_lock(project_id)` — stesso pattern già usato per `_dequeue_locks`
- Body di `register()` avvolto in `async with self._get_register_lock(project_id):`
- Overhead trascurabile: lock conteso solo durante la finestra di commit (~ms)

**2. UniqueConstraint su QueueEntry (difesa in profondità)**
- Aggiunto `UniqueConstraint('project_id', 'order', name='uq_queue_entries_project_order')` al modello QueueEntry
- Nuova migrazione Alembic `8cbf6da8b8c2` che applica il constraint

### File modificati
- `backend/app/services/issue_queue_service.py` — lock helper + register lock
- `backend/app/models/queue_entry.py` — UniqueConstraint
- `backend/alembic/versions/8cbf6da8b8c2_add_unique_constraint_queue_entries_.py` — migrazione

### Verifica
- 218 test passati (0 regressioni, 1 pre-existing failure in test_db_backup)
- Import test: register lock funziona, unique constraint presente nel model e nel DB
- Sintassi Python verificata su entrambi i file modificati