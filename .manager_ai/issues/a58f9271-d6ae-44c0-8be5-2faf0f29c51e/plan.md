# Piano: Refactor queue_add/queue_remove in IssueQueueService

## Task 1: Aggiungere add_to_queue() e remove_from_queue() a IssueQueueService

Aggiungere due metodi pubblici a `IssueQueueService` in `issue_queue_service.py`:
- `add_to_queue(session, project_id, issue_id)` — validazione, emissione evento
- `remove_from_queue(session, project_id, issue_id)` — lookup QueueEntry, mark_dispatched, emissione evento

Sollevano `AppError` per errori di validazione (status non valido, non in coda).

## Task 2: Refactor MCP shared_tools.py — queue_add e queue_remove

Riscrivere `queue_add()` e `queue_remove()` in `shared_tools.py` per chiamare i nuovi metodi del service. Fixare `queue_list()` e `queue_position()` per usare `issue_queue_service_ref` invece di new `IssueQueueService()`.

## Task 3: Refactor REST routers/queue.py — add_to_queue e remove_from_queue

Riscrivere gli endpoint `add_to_queue()` e `remove_from_queue()` in `routers/queue.py` per chiamare i nuovi metodi del service. Mantenere i field REST-specific (message, HTTPException).
