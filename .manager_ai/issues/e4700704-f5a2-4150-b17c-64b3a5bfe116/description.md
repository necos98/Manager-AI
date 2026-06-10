## Pulsante "Rimuovi dalla coda" nella UI globale

**Problema:** Esiste già l'MCP tool `queue_remove` per rimuovere una issue dalla coda, ma manca:
1. Un endpoint REST (`DELETE /api/queue/{project_id}/{issue_id}`) per chiamarlo dal frontend
2. Un pulsante "Rimuovi" nella pagina `/queue` del frontend

**Stato attuale:**
- MCP tool `queue_remove` implementato in `backend/app/mcp/shared_tools.py:1668` — funziona via protocollo MCP
- Pagina `/queue` esiste con tabella delle issue QUEUED (solo lettura, nessuna azione)
- Nessun endpoint REST per rimuovere dalla coda

**Soluzione proposta:**

**Backend — nuovo endpoint REST:**
```python
@router.delete("/{project_id}/{issue_id}")
async def remove_from_queue(project_id: str, issue_id: str, db: ...) -> dict:
    # Richiama la logica di queue_remove via IssueQueueService
```

**Frontend — pagina `/queue`:**
Aggiungere una colonna "Azioni" nella tabella "In coda" con un pulsante/bottone "Rimuovi" per ogni riga, che apre un confirm dialog (già usano Radix Dialog) e chiama l'API DELETE.

**File interessati:**
- `backend/app/routers/queue.py` — nuovo endpoint DELETE
- `frontend/src/features/queue/api.ts` — funzione `removeFromQueue(project_id, issue_id)`
- `frontend/src/features/queue/hooks.ts` — mutation hook `useRemoveFromQueue`
- `frontend/src/routes/queue.tsx` — colonna azioni + pulsante rimuovi

**Priorità:** Media — miglioramento UX per gestione coda