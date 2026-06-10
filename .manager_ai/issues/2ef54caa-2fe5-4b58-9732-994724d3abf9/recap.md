## Recap

**Problema:** Il pulsante cestino per rimuovere una issue dalla queue mostrava il dialog di conferma ma la issue rimaneva in coda.

**Root cause:** `IssueQueueService.mark_dispatched()` gestiva solo DISPATCHING → DISPATCHED, ma la rimozione manuale dalla queue trova il QueueEntry in stato PENDING. Il metodo falliva silenziosamente (log warning) e l'entry restava PENDING per sempre.

**Fix:** Aggiunto fallback a `_get_pending_by_issue()` in `mark_dispatched()` quando non viene trovato un entry DISPATCHING — stesso pattern già usato da `mark_failed()`.

**File modificato:** `backend/app/services/issue_queue_service.py` — metodo `mark_dispatched` (line 116-135)