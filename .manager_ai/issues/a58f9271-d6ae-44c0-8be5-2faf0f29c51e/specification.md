# Spec: Estrarre logica duplicata queue_add/queue_remove in IssueQueueService

## Stato attuale

La logica di `queue_add` e `queue_remove` è duplicata in due punti:

1. **MCP** → `backend/app/mcp/shared_tools.py` (righe 1597–1720)
2. **REST** → `backend/app/routers/queue.py` (righe 267–362)

Entrambi i percorsi fanno:
- Fetch dell'issue via `IssueService.get_for_project()`
- Validazione status (NEW o ACCEPTED)
- Emissione evento `issue_status_changed` via `_emit_event()`
- Restituzione di `{id, project_id, status}`

**Differenze minori:**
- MCP usa `issue_display_name(issue)`, REST usa `issue.name or ""` per l'event name
- MCP restituisce `{"error": msg}` su errore, REST solleva `HTTPException`
- REST aggiunge `"message": "..."` alla risposta

**Bug correlato (singleton pattern):**
In `shared_tools.py`, le funzioni `queue_remove` (riga 1697), `queue_list` (riga 1649) e `queue_position` (riga 1731) creano `IssueQueueService()` — un nuovo costruttore — invece di usare `issue_queue_service_ref`. Questo:
- Crea un notifier fantasma su EventService (pollution)
- Sovrascrive `issue_queue_service_ref` con un'istanza effimera

## Soluzione

### 1. Aggiungere metodi a IssueQueueService

Aggiungere `add_to_queue()` e `remove_from_queue()` a `IssueQueueService` che:
- Accettano `session`, `project_id`, `issue_id`
- Fanno la validazione (status NEW/ACCEPTED)
- Emettono l'evento `issue_status_changed → QUEUED`
- Sollevano `AppError` per errori di validazione (coerente con altri service)
- Restituiscono `{"id", "project_id", "status"}`

### 2. Refactor MCP shared_tools.py

- `queue_add()` → chiama `issue_queue_service_ref.add_to_queue()`, wrappa AppError in dict di errore
- `queue_remove()` → chiama `issue_queue_service_ref.remove_from_queue()`, wrappa AppError in dict di errore
- `queue_list()` e `queue_position()` → usano `issue_queue_service_ref` invece di `IssueQueueService()`

### 3. Refactor REST routers/queue.py

- `add_to_queue()` endpoint → chiama `issue_queue_service_ref.add_to_queue()`, wrappa AppError in `HTTPException`
- `remove_from_queue()` endpoint → chiama `issue_queue_service_ref.remove_from_queue()`, wrappa AppError in `HTTPException`
- Mantiene i field aggiuntivi specifici REST (message, issue_name lookup aggiuntivo)

### 4. Non modificare

- `queue_list`, `queue_position`, `queue_set_auto_process`, `queue_get_auto_process` in shared_tools.py (solo fix singleton)
- `list_global_queue`, `list_global_running`, `get_queue_status`, `set_auto_process`, `get_queue_position` in routers/queue.py (non duplicati)

## Criteri di accettazione

1. `queue_add` via MCP continua a funzionare (test con issue in stato NEW)
2. `queue_add` via REST continua a funzionare
3. `queue_remove` via MCP continua a funzionare
4. `queue_remove` via REST continua a funzionare
5. Nessun nuovo `IssueQueueService()` creato in shared_tools.py o routers/queue.py
6. EventService non riceve notifier duplicati a ogni chiamata MCP
