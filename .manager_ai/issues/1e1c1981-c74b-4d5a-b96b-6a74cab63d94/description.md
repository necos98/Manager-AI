## Toggle per l'auto-processing della coda issue

### Contesto
Attualmente `IssueQueueService` è sempre attivo: non appena una issue viene aggiunta alla coda o ne finisce una, la prossima parte automaticamente. Non c'è un modo per disabilitare questo comportamento se non fermando manualmente le issue.

### Obiettivo
Aggiungere un toggle per attivare/disattivare l'auto-processing della coda, con default **disattivato** all'avvio del software. Attivabile manualmente (via UI) o tramite MCP tool.

### Modifiche necessarie

**1. `default_settings.json` — Nuovo setting**
- Aggiungere `"queue_auto_process": "false"` (default disabilitato)
- Tenere `work_queue_paused` per la semantica esistente (blocco manuale di `get_next_issue`)

**2. `issue_queue_service.py` — Gate principale**
- `__init__`: leggere `queue_auto_process` da SettingsService e salvarlo come `self._enabled`
- `notify()` (riga 308): se `not self._enabled`, ritornare subito senza processare eventi
- `startup_resume()` (riga 217): se `not self._enabled`, saltare tutto
- Aggiungere metodo `async set_enabled(enabled: bool)` che aggiorna il setting + eventualmente chiama `startup_resume()` se riattivato

**3. `orchestrator_server.py` — Nuovo MCP tool**
- `queue_set_auto_process(enabled: bool)`: imposta il setting e ricarica lo stato nel service
- Opzionale: `queue_get_auto_process()` per leggere lo stato attuale

**4. `shared_tools.py` — Eventuale**
- Aggiungere una funzione `queue_set_auto_process(session, enabled)` chiamabile dall'orchestrator

**5. UI (opzionale)**
- `GET /api/queue/status` già espone `paused` — aggiungere anche `auto_process_enabled`
- Frontend: toggle nella pagina della coda

### Dettagli implementativi

**IssueQueueService (issue_queue_service.py):**
```python
# In __init__:
self._enabled = False  # default until loaded from DB

# Nuovo metodo:
async def load_state(self) -> None:
    async with async_session() as session:
        svc = SettingsService(session)
        val = await svc.get("queue_auto_process")
        self._enabled = val.lower() == "true"

# In notify(), riga 308:
if not self._enabled:
    return

# In startup_resume(), riga 217:
if not self._enabled:
    logger.info("Auto queue processing is disabled — skipping startup_resume")
    return

# Nuovo metodo:
async def set_enabled(self, enabled: bool) -> None:
    self._enabled = enabled
    async with async_session() as session:
        svc = SettingsService(session)
        await svc.set("queue_auto_process", "true" if enabled else "false")
        await session.commit()
    if enabled:
        await self.startup_resume()
```

**main.py:**
- Dopo `issue_queue_service = IssueQueueService()`, aggiungere:
```python
await issue_queue_service.load_state()
```
- `startup_resume()` già viene chiamato subito dopo, ma ora rispetterà `load_state()`

**MCP orchestrator_server.py:**
```python
@orchestrator_mcp.tool(
    description="Enable or disable automatic queue processing. "
                "When disabled (default), issues added to the queue will NOT "
                "auto-start — you must start them manually via run_issue. "
                "When enabled, the queue automatically dequeues and runs "
                "the next pending issue after one finishes."
)
async def queue_set_auto_process(enabled: bool) -> dict:
    async with async_session() as session:
        from app.services.settings_service import SettingsService
        svc = SettingsService(session)
        await svc.set("queue_auto_process", "true" if enabled else "false")
        await session.commit()
    # Reload the service state
    from app.services.issue_queue_service import issue_queue_service_ref
    svc_ref = issue_queue_service_ref  # need a module-level reference
    await svc_ref.set_enabled(enabled)
    return {"enabled": enabled, "status": "updated"}
```

**Nota:** Serve rendere `IssueQueueService` accessibile globalmente (o passare un riferimento) — al momento in main.py è una variabile locale. Si può aggiungere un module-level reference in `issue_queue_service.py` o usare `event_service` per trovarlo.

### Comportamenti attesi

| Scenario | Comportamento |
|----------|---------------|
| Software si avvia | Coda disattivata. Le issue in coda NON partono |
| Aggiungo issue alla coda | Si registra QueueEntry ma non parte |
| Finisce una issue | Non parte la prossima automaticamente |
| Attivo via MCP `queue_set_auto_process(true)` | Ricontrolla le pending e fa partire la prima se nessuna è in esecuzione |
| Disattivo mentre gira una issue | La issue in corso continua — non viene killata |
| Riattivo | Chiama startup_resume() per eventuali pending