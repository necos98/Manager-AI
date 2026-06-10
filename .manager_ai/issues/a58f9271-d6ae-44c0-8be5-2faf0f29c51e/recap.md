## Recap: Logica duplicata MCP e REST per queue

Estratta la logica duplicata di `queue_add` e `queue_remove` in un service layer comune su `IssueQueueService`.

### Modifiche

**1. `backend/app/services/issue_queue_service.py`**
- Aggiunti import: `AsyncSession`, `AppError`
- Nuovo metodo `add_to_queue(session, project_id, issue_id)` — validazione status NEW/ACCEPTED, emissione evento `issue_status_changed → QUEUED`. Solleva `AppError` su errore.
- Nuovo metodo `remove_from_queue(session, project_id, issue_id)` — lookup QueueEntry, mark_dispatched, emissione evento. Solleva `AppError` su errore.

**2. `backend/app/mcp/shared_tools.py`**
- `queue_add()` riscritto per delegare a `issue_queue_service_ref.add_to_queue()`
- `queue_remove()` riscritto per delegare a `issue_queue_service_ref.remove_from_queue()`
- `queue_list()` e `queue_position()` fixati: ora usano `issue_queue_service_ref` invece di new `IssueQueueService()` — elimina notifier fantasma su EventService

**3. `backend/app/routers/queue.py`**
- Endpoint `POST /api/queue/add` delegato a `issue_queue_service_ref.add_to_queue()`
- Endpoint `POST /api/queue/remove` delegato a `issue_queue_service_ref.remove_from_queue()`

### Bug fix correlato
Le funzioni `queue_remove`, `queue_list` e `queue_position` in `shared_tools.py` creavano `IssueQueueService()` (nuova istanza) invece di usare la module-level ref `issue_queue_service_ref`. Questo causava notifier fantasma su EventService (pollution) e sovrascriveva la ref globale con istanze effimere. Ora tutte usano `issue_queue_service_ref`.

### Test
- 3/3 queue test passano (test_work_queue.py)
- 11/11 storage write_queue test passano
- 218/219 test totali passano (1 fallimento preesistente in test_db_backup)