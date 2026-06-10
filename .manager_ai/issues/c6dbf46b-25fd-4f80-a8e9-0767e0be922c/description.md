## Refactoring coda: QueueEntry come unica fonte di verità (eliminare IssueStatus.QUEUED)

### Problema attuale
Il sistema di coda ha **due fonti di verità in conflitto**:

1. **`Issue.status == "Queued"`** — usato da REST API (`GET /api/queue`), `queue_add()`, `queue_remove()`, `_dequeue_and_run()`
2. **`QueueEntry.status == "pending"`** — tabella separata `queue_entries` con issue_id, project_id, order, status, usata da MCP `queue_list`, `IssueQueueService._dequeue_and_run()`, `get_next_pending()`

Queste due fonti convivono ma non sono sincronizzate strutturalmente:
- `queue_add()` cambia Issue.status → QUEUED POI emette evento che crea QueueEntry
- `queue_remove()` controlla Issue.status==QUEUED POI marca QueueEntry come DISPATCHED
- REST API lista QUEUED da Issue, MCP le lista da QueueEntry → risultati diversi
- Un restart può lasciare stati orfani

### Soluzione proposta
**Eliminare `IssueStatus.QUEUED` come indicatore di appartenenza alla coda.** La coda è definita esclusivamente dalla presenza di un `QueueEntry.status == PENDING`.

### Modifiche necessarie

#### 1. `backend/app/mcp/shared_tools.py`
- **`queue_add()`**: non cambiare più Issue.status in QUEUED. L'issue resta in NEW o ACCEPTED. Creare solo QueueEntry via `IssueQueueService.register()` + emettere evento `issue_queued`.
- **`queue_remove()`**: non controllare più Issue.status==QUEUED. Controllare solo presenza di QueueEntry PENDING. Non cambiare Issue.status.
- **`queue_list()`**: già usa QueueEntry, ma arricchire con issue_name e description dall'Issue table (join).
- **`queue_position()`**: già usa QueueEntry, ok.

#### 2. `backend/app/services/issue_queue_service.py`
- **`_dequeue_and_run()`**: non cambiare più Issue.status da QUEUED a REASONING. L'issue è ancora NEW/ACCEPTED, va portato direttamente a REASONING.
- **`_on_issue_queued()`**: non deve fare status transition (l'Issue.status non è QUEUED).
- **`startup_resume()`**: scansionare QueueEntry.PENDING all'avvio, non IssueStatus.QUEUED.

#### 3. `backend/app/routers/queue.py`
- **`GET /api/queue`**: non query `IssueService.list_by_project(status=QUEUED)`. Invece, query `QueueEntry` con `status == PENDING`, arricchire con issue_name/description da Issue table via join o lookup.
- **`GET /api/queue/status`**: count da QueueEntry, non da IssueStatus.

#### 4. `backend/mcp/orchestrator_server.py`
- **MCP `queue_list`**: già usa QueueEntry ma restituisce solo position + issue_id. Aggiungere issue_name e description arricchiti.

#### 5. `backend/app/models/issue.py`
- **`IssueStatus.QUEUED`**: valutare se rimuovere o tenere come deprecated. Se mantenuto, non deve più essere usato per logica di coda.

### Perché questo è collegato all'auto-resume
Con questo refactoring, l'auto-resume all'avvio diventa naturale: basta scansionare `QueueEntry` con `status == PENDING` e avviare la prima — niente dual-state da riconciliare.

### Cosa NON cambia
- La UI mostra le stesse informazioni
- L'MCP tool set rimane identico
- Il flusso FIFO rimane identico
- `run_issue()` rimane invariato

### File interessati
- `backend/app/mcp/shared_tools.py` — queue_add, queue_remove
- `backend/app/services/issue_queue_service.py` — _dequeue_and_run, _on_issue_queued
- `backend/app/routers/queue.py` — GET /api/queue, GET /api/queue/status
- `backend/app/models/issue.py` — eventuale rimozione QUEUED
- `backend/app/mcp/orchestrator_server.py` — queue_list arricchito

### Priorità
Alta — questo refactoring risolve strutturalmente il bug dell'auto-resume e rende il sistema di coda robusto e manutenibile.