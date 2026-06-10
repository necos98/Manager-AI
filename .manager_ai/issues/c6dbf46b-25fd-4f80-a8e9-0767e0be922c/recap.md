## Recap: QueueEntry single source of truth

Eliminato il dual-state tra Issue.status="Queued" e QueueEntry. La presenza in coda è ora definita esclusivamente da QueueEntry con status PENDING.

### Cosa è cambiato

**shared_tools.py — queue_add():**
- Rimosso `update_fields(status=QUEUED)` — l'issue resta in NEW o ACCEPTED
- Evento `issue_status_changed` con new_status="Queued" ancora emesso (trigger per IssueQueueService e UI)
- Return ora riporta `issue.status` originale, non QUEUED

**shared_tools.py — queue_remove():**
- Sostituito controllo `issue.status == QUEUED` con `get_pending_entry()` su QueueEntry
- Rimosso `update_fields(status=NEW)` — l'issue mantiene status originale
- Evento emesso con `new_status = issue.status` (non più sintetico QUEUED)

**issue_queue_service.py — _dequeue_and_run():**
- Aggiornato commento (codice invariato: update_status non ha validazione transizioni)

**issue_queue_service.py:**
- Aggiunto metodo pubblico `get_pending_entry(issue_id)`
- Aggiornato docstring del modulo

**routers/queue.py — GET /api/queue:**
- Sostituita query `issue_service.list_by_project(status=QUEUED)` con query diretta a QueueEntry PENDING + arricchimento issue via get_by_id

**routers/queue.py — GET /api/queue/status:**
- Count eseguito su QueueEntry PENDING invece di IssueStatus.QUEUED

**shared_tools.py — queue_list MCP tool:**
- Arricchito output con issue_name e description (prima erano stringhe vuote)

**orchestrator_server.py:**
- Aggiornate tutte le descrizioni dei tool MCP della coda

### Cosa NON è cambiato
- IssueStatus.QUEUED mantenuto come enum value deprecato (backward compat)
- UI frontend invariata
- Worker MCP tools (stessi nomi, parametri, return)
- Flusso FIFO (QueueEntry.order)
- run_issue() invariato

### Verifica
- 218 test passano (1 pre-esistente fallito: test_db_backup, non correlato)
- Sintassi valida in tutti i 4 file modificati
