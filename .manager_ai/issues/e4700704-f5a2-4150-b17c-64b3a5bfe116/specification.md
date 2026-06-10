## Pulsante "Rimuovi dalla coda" nella UI globale

**Problema:** Esiste già l'MCP tool `queue_remove` per rimuovere una issue dalla coda, ma mancava un modo per farlo dalla UI web.

**Stato attuale (implementato):**
- Endpoint REST `POST /api/queue/remove` in `backend/app/routers/queue.py` — accetta `{project_id, issue_id}`
- Funzione `removeFromQueue()` in `frontend/src/features/queue/api.ts`
- Mutation hook `useRemoveFromQueue` in `frontend/src/features/queue/hooks.ts`
- Pulsante "Rimuovi" (icona Trash2) nella tabella "In coda" della pagina `/queue` in `frontend/src/routes/queue.tsx`
- Confirm dialog con Radix prima della rimozione
- WebSocket event `queue_entry_removed` per invalidamento real-time

**Dettagli implementativi:**
- Backend: delega a `IssueQueueService.remove_from_queue()` con fallback `_queue_remove_direct`
- Frontend: `useRemoveFromQueue` mutation invalida le query `queue.queued`, `queue.status`, `queue.all` dopo la rimozione
- Event context: `queue_entry_removed` invalida anche `queue.position`