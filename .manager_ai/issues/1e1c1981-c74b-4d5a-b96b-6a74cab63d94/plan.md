# Piano di implementazione: Toggle auto-processing coda issue

## Obiettivo
Aggiungere un toggle persistente (default **disattivato**) per l'auto-processing della coda issue, controllabile via MCP tool `queue_set_auto_process`. Il toggle blocca `IssueQueueService.notify()` e `startup_resume()`.

## Task

### Task 1: `default_settings.json` — Nuovo default
Aggiungere `"queue_auto_process": "false"`.

### Task 2: `issue_queue_service.py` — Module-level reference + `_enabled` flag + `load_state()` + gates
- Aggiungere `issue_queue_service_ref: Optional[IssueQueueService] = None` dopo `logger`
- Costruttore: aggiungere `self._enabled = False`, impostare `issue_queue_service_ref = self`
- Nuovo metodo `load_state()` (legge `queue_auto_process` da DB)
- Gate in `notify()`: return immediato se `not self._enabled`
- Gate in `startup_resume()`: return immediato se `not self._enabled`
- Nuovo metodo `set_enabled(enabled: bool)` (salva setting + eventualmente chiama `startup_resume()`)

### Task 3: `main.py` — Chiamata a `load_state()`
Aggiungere `await issue_queue_service.load_state()` dopo la creazione del service.

### Task 4: `shared_tools.py` — Funzioni MCP
- `queue_set_auto_process(session, enabled)` — salva setting + aggiorna singleton
- `queue_get_auto_process(session)` — legge setting

### Task 5: `orchestrator_server.py` — MCP Tools
- Importare le nuove funzioni da shared_tools
- Aggiungere `queue_set_auto_process` e `queue_get_auto_process` come tool decorati

### Task 6: `routers/queue.py` — REST API status
- Aggiungere `auto_process_enabled` a `QueueStatus` model
- Leggere il setting nell'endpoint `GET /api/queue/status`

## Ordine di implementazione
1 → 2 → 3 → 4 → 5 → 6
