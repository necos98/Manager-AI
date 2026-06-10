Aggiungere un toggle UI nella pagina Queue per attivare/disattivare queue_auto_process

Stato attuale:
- Il backend ha gia la logica completa per il toggle (IssueQueueService.set_enabled(), MCP tools queue_set_auto_process/queue_get_auto_process, settings queue_auto_process e work_queue_paused)
- La REST API GET /api/queue/status restituisce auto_process_enabled: bool
- Il frontend (frontend/src/routes/queue.tsx) legge statusData?.paused ma NON usa auto_process_enabled
- Non esiste una REST API per SET/resettare auto_process (solo MCP tools)

Cosa serve:
1. Aggiungere REST API endpoint (es. POST /api/queue/auto-process) per impostare il toggle
2. Nella pagina Queue (frontend/src/routes/queue.tsx), aggiungere uno switch/toggle per attivare/disattivare l auto-processo della coda
3. Lo switch deve chiamare la REST API e aggiornare lo stato in tempo reale

Riferimenti codice:
- backend/app/services/issue_queue_service.py righe 274-303: set_enabled(), load_state()
- backend/app/mcp/shared_tools.py righe 1757-1785: queue_set_auto_process, queue_get_auto_process
- backend/app/routers/queue.py righe 52-56, 205-215: QueueStatus schema con auto_process_enabled
- frontend/src/routes/queue.tsx: pagina Queue attuale (manca il toggle)