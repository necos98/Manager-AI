# Specifica: Toggle per auto-processing coda issue

## Contesto

`IssueQueueService` (in `backend/app/services/issue_queue_service.py`) è sempre attivo incondizionatamente:

- Nel costruttore si registra su `EventService` come `BaseNotifier`
- `notify()` processa **ogni** evento `issue_status_changed` e fa partire la prossima issue in coda
- `startup_resume()` all'avvio fa partire le issue pending
- Non c'è modo di disabilitare questo comportamento senza killare manualmente le issue

La issue deve aggiungere **un toggle persistente** (default **disabilitato**) controllabile via MCP tool, con gate in `IssueQueueService` per bloccare l'auto-processing a runtime.

## Modifiche necessarie

### 1. `default_settings.json` — Nuovo default

Aggiungere riga:
```
"queue_auto_process": "false"
```

### 2. `IssueQueueService` (`issue_queue_service.py`) — Gate + singleton ref

**a) Module-level reference:**
Aggiungere dopo la definizione di `logger`:
```python
issue_queue_service_ref: Optional[IssueQueueService] = None
```
Il costruttore imposta `issue_queue_service_ref = self`.

**b) `__init__`:**
Aggiungere:
```python
self._enabled = False  # default finché load_state() non viene chiamato
```

**c) Nuovo metodo `load_state()`:**
```python
async def load_state(self) -> None:
    try:
        async with async_session() as session:
            from app.services.settings_service import SettingsService
            svc = SettingsService(session)
            val = await svc.get("queue_auto_process")
            self._enabled = val.lower() == "true"
    except Exception:
        logger.warning("Failed to load queue_auto_process setting; defaulting to disabled")
        self._enabled = False
```

**d) Gate in `notify()` (riga 308):**
Aggiungere subito dopo il logging, prima di qualsiasi processing:
```python
if not self._enabled:
    return
```

**e) Gate in `startup_resume()` (riga 217):**
Aggiungere all'inizio del `try`:
```python
if not self._enabled:
    logger.info("Auto queue processing is disabled — skipping startup_resume")
    return
```

**f) Nuovo metodo `set_enabled(enabled: bool)`:**
```python
async def set_enabled(self, enabled: bool) -> None:
    self._enabled = enabled
    async with async_session() as session:
        svc = SettingsService(session)
        await svc.set("queue_auto_process", "true" if enabled else "false")
        await session.commit()
    logger.info("Queue auto-processing %s", "enabled" if enabled else "disabled")
    if enabled:
        asyncio.create_task(self.startup_resume())
```

### 3. `main.py` — Chiamata a `load_state()`

Dopo la riga 306 (`issue_queue_service = IssueQueueService()`), aggiungere:
```python
await issue_queue_service.load_state()
```
Questa chiamata deve essere DENTRO il blocco `try` (riga 298) perché sia protetta dal catch generico.

### 4. `shared_tools.py` — Funzioni MCP condivise

**`queue_set_auto_process(session, enabled: bool)`:**
```python
async def queue_set_auto_process(session: AsyncSession, enabled: bool) -> dict:
    # 1. Salva il setting in DB
    svc = SettingsService(session)
    await svc.set("queue_auto_process", "true" if enabled else "false")
    await session.commit()
    # 2. Ricarica lo stato nel service singleton
    from app.services.issue_queue_service import issue_queue_service_ref
    if issue_queue_service_ref is not None:
        await issue_queue_service_ref.set_enabled(enabled)
    return {"enabled": enabled, "status": "updated"}
```

**`queue_get_auto_process(session)`:**
```python
async def queue_get_auto_process(session: AsyncSession) -> dict:
    svc = SettingsService(session)
    val = await svc.get("queue_auto_process")
    enabled = val.lower() == "true"
    return {"enabled": enabled}
```

### 5. `orchestrator_server.py` — MCP Tools

Aggiungere import per le nuove funzioni:
```python
queue_set_auto_process as _queue_set_auto_process,
queue_get_auto_process as _queue_get_auto_process,
```

Aggiungere due tool nella sezione `# ── 8) Issue Queue Tools ────`:

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
        return await _queue_set_auto_process(session, enabled)


@orchestrator_mcp.tool(
    description="Get the current auto-processing toggle state for the queue. "
                "Returns whether automatic queue processing is currently enabled."
)
async def queue_get_auto_process() -> dict:
    async with async_session() as session:
        return await _queue_get_auto_process(session)
```

### 6. REST API — Queue status endpoint (`backend/app/routers/queue.py`)

**Modello `QueueStatus`:**
Aggiungere campo `auto_process_enabled: bool`.

**Endpoint `GET /api/queue/status`:**
Dopo `paused = await settings_service.get("work_queue_paused")`, aggiungere:
```python
auto_process_str = await settings_service.get("queue_auto_process")
auto_process_enabled = auto_process_str.lower() == "true"
```
Passare `auto_process_enabled=auto_process_enabled` nel costruttore di `QueueStatus`.

### 7. Frontend (opzionale, bassa priorità)

- La UI della coda (`frontend/src/features/queue/`) può opzionalmente esporre un toggle usando `GET /api/queue/status` e una chiamata MCP o un nuovo endpoint REST per settarlo
- **Non implementato in questa issue** — sarà una issue separata

## Comportamenti attesi

| Scenario | Comportamento |
|----------|---------------|
| App si avvia | `_enabled = False`. `startup_resume()` salta. Le issue in coda NON partono. |
| Aggiungo issue alla coda | `notify()` ritorna subito (gate). QueueEntry registrata ma non parte. |
| Finisce una issue (via `issue_status_changed → Finished`) | `notify()` ritorna subito. Nessuna auto-dequeue. |
| Chiamo `queue_set_auto_process(true)` via MCP | `_enabled = true`, setting salvato. Se ci sono pending, chiama `startup_resume()` e fa partire la prima. |
| Disattivo mentre gira una issue | La issue in corso NON viene killata — `set_enabled(false)` non tocca terminali attivi. |
| Riattivo | Chiama `startup_resume()` che fa partire la prima pending se nessuna è in esecuzione. |
