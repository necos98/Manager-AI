## Piano di Implementazione

### Task 1: shared_tools.py — queue_add() — rimuovi status QUEUED
Rimuovere il cambio di status a QUEUED in queue_add(). Aggiungere chiamata diretta a IssueQueueService.register() + _maybe_auto_start_first().

### Task 2: shared_tools.py — queue_remove() — rimuovi controllo QUEUED
Sostituire il controllo `issue.status == QUEUED` con controllo su QueueEntry PENDING. Non cambiare Issue.status.

### Task 3: issue_queue_service.py — _dequeue_and_run() — transizione NEW/ACCEPTED → REASONING
Cambiare la transizione da QUEUED→REASONING a diretta NEW/ACCEPTED→REASONING.

### Task 4: issue_queue_service.py — _on_issue_queued() — rimuovi register()
Rimuovere la chiamata a self.register() (ora in queue_add()). Mantenere solo _maybe_auto_start_first().

### Task 5: routers/queue.py — GET /api/queue — query da QueueEntry
Sostituire la query IssueStatus.QUEUED con query diretta a QueueEntry PENDING arricchita con dati issue.

### Task 6: routers/queue.py — GET /api/queue/status — count da QueueEntry
Sostituire il conteggio da IssueStatus.QUEUED con count da QueueEntry PENDING.

### Task 7: orchestrator_server.py — queue_list — arricchisci con issue_name/description
Aggiungere issue_name e description nel risultato di queue_list MCP tool (shared_tools.py).

### Task 8: Verifica sintassi e test
Verificare che il codice compili correttamente e i test esistenti passino.
