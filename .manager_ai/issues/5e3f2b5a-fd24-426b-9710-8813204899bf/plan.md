## Piano di implementazione

### Task 1: Aggiungere lock per-progetto in register()

Aggiungere un campo `self._register_locks: dict[str, asyncio.Lock]` e un helper `_get_register_lock(project_id)` in `IssueQueueService.__init__()`, esattamente come già esiste `_dequeue_locks`. Avvolgere il corpo di `register()` in `async with self._get_register_lock(project_id):`.

### Task 2: Aggiungere UniqueConstraint a QueueEntry (difesa in profondità)

Creare migrazione Alembic che aggiunge `UniqueConstraint('project_id', 'order', name='uq_queue_entries_project_order')` alla tabella `queue_entries`. Anche se il lock applicativo dovesse fallire, il DB impedisce duplicati.
