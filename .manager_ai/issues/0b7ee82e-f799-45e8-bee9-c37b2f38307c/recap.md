# Issue Queue System — Recap Implementazione

## Cosa è stato implementato

**5 task completati**, tutti verificati:

### Task 1: Status QUEUED nel modello
`backend/app/models/issue.py` — Aggiunto `QUEUED = "Queued"` all'enum `IssueStatus`. Transizioni: NEW→QUEUED, ACCEPTED→QUEUED, QUEUED→REASONING, QUEUED→NEW (dequeue).

### Task 2: IssueQueueService (event listener)
`backend/app/services/issue_queue_service.py` (167 linee) — `BaseNotifier` registrato su `EventService`:
- **notify()**: intercetta `issue_status_changed` con `new_status == "Finished"` → `_dequeue_and_run()`
- **notify()**: intercetta `new_status == "Queued"` → `_maybe_auto_start_first()` per auto-start della prima issue in coda
- **`_dequeue_and_run()`**: query QUEUED ordinate per `created_at`, cambia la prima in REASONING, chiama run_issue()
- **`_maybe_auto_start_first()`**: se solo 1 QUEUED e nessuna REASONING/PLANNED/ACCEPTED running → auto-start immediato
- Gestione errori con logger.exception + skip su fallimento

### Task 3: MCP tools in shared_tools.py
`backend/app/mcp/shared_tools.py` — 4 nuove funzioni (linee 1597-1730):
- **queue_add()**: valida NEW/ACCEPTED → QUEUED, emette evento
- **queue_list()**: elenca QUEUED con posizione 1-based, ordine FIFO
- **queue_remove()**: QUEUED → NEW, emette evento
- **queue_position()**: posizione 1-based o null se non QUEUED

### Task 4: Registrazione su orchestrator_server.py
`backend/app/mcp/orchestrator_server.py` — Import (linee 70-75) e registrazione (linee 401-443) dei 4 queue tool con decorator @orchestrator_mcp.tool()

### Task 5: Registrazione in main.py
`backend/app/main.py` — `_ = IssueQueueService()` nel lifespan (linea 340), import (linea 45), subito dopo NotificationService

## Comportamenti edge coperti
- Coda vuota quando FINISHED: listener non fa nulla
- Nuova QUEUED mentre running in corso: resta in coda, parte dopo
- QUEUED cancellata manualmente: non parte
- Prima QUEUED aggiunta (coda vuota, nessuna running): auto-start immediato
- Più QUEUED: ordine FIFO per created_at
- Errori loggati ma non bloccanti