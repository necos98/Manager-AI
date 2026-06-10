## Recap: Toggle per auto-processing coda issue

### File modificati

1. **`backend/app/mcp/default_settings.json`** — Aggiunto default `"queue_auto_process": "false"`

2. **`backend/app/services/issue_queue_service.py`** — Modifiche chiave:
   - Aggiunto `issue_queue_service_ref: Optional[IssueQueueService] = None` (module-level singleton ref)
   - Costruttore: `self._enabled = False` + `issue_queue_service_ref = self`
   - Nuovo `load_state()`: legge `queue_auto_process` dal DB all'avvio
   - Gate in `notify()`: return immediato se non enabled (blocca event-driven auto-processing)
   - Gate in `startup_resume()`: skip se non enabled
   - Nuovo `set_enabled(enabled)`: persiste il setting + chiama `startup_resume()` se riattivato

3. **`backend/app/main.py`** — Chiamata `await issue_queue_service.load_state()` dopo creazione service

4. **`backend/app/mcp/shared_tools.py`** — Nuove funzioni:
   - `queue_set_auto_process(session, enabled)` — MCP tool per attivare/disattivare
   - `queue_get_auto_process(session)` — MCP tool per leggere stato

5. **`backend/app/mcp/orchestrator_server.py`** — Due nuovi MCP tool esposti:
   - `queue_set_auto_process` (con descrizione dettagliata)
   - `queue_get_auto_process`

6. **`backend/app/routers/queue.py`** — Aggiunto `auto_process_enabled` al modello `QueueStatus` e popolato nell'endpoint `GET /api/queue/status`

### Design decisions
- Gate in `notify()` blocca TUTTI i flussi event-driven (issue finished → dequeue, issue queued → auto-start, issue reasoning → mark dispatching)
- `set_enabled(true)` chiama `startup_resume()` per riprendere pending dopo riattivazione
- `set_enabled(false)` NON killà terminali attivi — la issue in corso continua
- Module-level ref `issue_queue_service_ref` evita di creare nuove istanze per il toggle (le altre funzioni registry in shared_tools.py continuano a creare istanze temporanee, ma non sono affette dal gate perché usano solo metodi registry)
