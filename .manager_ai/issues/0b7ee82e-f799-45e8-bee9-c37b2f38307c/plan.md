# Piano di Implementazione — Issue Queue System

## Task 1: Aggiungere status QUEUED al modello

**File:** `backend/app/models/issue.py`
Aggiungere `QUEUED = "Queued"` all'enum `IssueStatus`.

## Task 2: Creare IssueQueueService (event listener)

**Nuovo file:** `backend/app/services/issue_queue_service.py`
- Classe `IssueQueueService(BaseNotifier)` che si registra su `EventService`
- `notify(event)`: filtra `issue_status_changed` con `new_status == "Finished"`
- `_dequeue_and_run(project_id)`: query QUEUED issues ordinate per `created_at`, cambia la prima in REASONING e chiama `run_issue()`
- Usa `async_session()`, `IssueService`, `run_issue_service.run_issue()`

## Task 3: Aggiungere MCP tools a shared_tools.py

**File:** `backend/app/mcp/shared_tools.py`
Aggiungere 4 funzioni:
- `queue_add(project_id, issue_id)` — validazione NEW/ACCEPTED → QUEUED, auto-start se prima in coda
- `queue_list(project_id)` — elenca QUEUED con posizione
- `queue_remove(project_id, issue_id)` — QUEUED → NEW/CANCELED
- `queue_position(project_id, issue_id)` — posizione in coda

## Task 4: Registrare MCP tools su orchestrator_server.py

**File:** `backend/app/mcp/orchestrator_server.py`
Importare e registrare i 4 queue tool con decorator `@orchestrator_mcp.tool()`

## Task 5: Registrare IssueQueueService in main.py

**File:** `backend/app/main.py`
Aggiungere `_ = IssueQueueService()` nel lifespan dopo NotificationService

## Ordine di esecuzione
1 → 2 → 3 → 4 → 5
(I task 2 e 3 sono indipendenti ma 3 è prima di 4 per dipendenza)