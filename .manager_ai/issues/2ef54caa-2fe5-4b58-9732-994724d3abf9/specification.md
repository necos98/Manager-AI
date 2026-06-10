## Analisi

### Problema
Cliccando sul pulsante cestino (rimozione dalla queue) di una issue in coda, il dialog di conferma si chiude ma la issue rimane in coda. L'utente vede la issue ricomparire dopo il refresh della lista.

### Root cause
`IssueQueueService.mark_dispatched()` gestisce solo la transizione **DISPATCHING → DISPATCHED**, ma quando l'utente rimuove manualmente una issue dalla queue, il QueueEntry è ancora in stato **PENDING** (non ancora avviato per l'elaborazione).

Il metodo fallisce silenziosamente (log warning + return None), ma il chiamante in `routers/queue.py:remove_from_queue` ignora il valore di ritorno e risponde comunque 200 OK. Il QueueEntry resta PENDING per sempre.

Confronto con `mark_failed()` che invece gestisce correttamente **entrambi** gli stati (DISPATCHING e PENDING, lines 136-139).

### Fix
Modificare `mark_dispatched()` in `issue_queue_service.py` per cercare un entry PENDING se non trova un entry DISPATCHING — stesso pattern già usato da `mark_failed()`.

### Impatto
- **Normale issue completata**: DISPATCHING → DISPATCHED (invariato)
- **Rimozione manuale dalla queue**: PENDING → DISPATCHED (nuovo, fixato)
- **Rimozione di issue già in esecuzione**: se una issue è in stato DISPATCHING, funziona già
