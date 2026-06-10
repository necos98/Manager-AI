## Specifica: Eliminare evento ridondante in _dequeue_and_run

### Problema
In `IssueQueueService._dequeue_and_run()`, il flusso è:
1. `mark_dispatching()` — marca la QueueEntry come DISPATCHING (sincrono, linea 448)
2. `update_status()` — cambia l'issue status in REASONING (linea 456-458)
3. `_emit_event()` — emette `issue_status_changed(Reasoning)` (linea 471-478)
4. L'evento viaggia via `EventService` a tutti i notifier, incluso `IssueQueueService` stesso
5. `IssueQueueService.notify()` riceve l'evento, vede `new_status == "Reasoning"` e spawna `_on_issue_reasoning()` via `asyncio.create_task`
6. `_on_issue_reasoning()` chiama `mark_dispatching()` — che trova già DISPATCHING e fa no-op

Risultato: **un async task sprecato** + **una query DB extra** (SELECT + UPDATE no-op) per ogni dispatch di issue in coda.

### Soluzione proposta
Aggiungere un flag `_queue_dispatching_handled: True` all'evento emesso in `_dequeue_and_run()`. In `notify()`, quando `new_status == "Reasoning"` e il flag è presente, saltare la creazione del task `_on_issue_reasoning()` perché la marcatura DISPATCHING è già stata fatta sincronamente.

### Criteri di accettazione
1. `_dequeue_and_run()` emette l'evento `issue_status_changed` con il flag `_queue_dispatching_handled: True`
2. `notify()` NON crea un task `_on_issue_reasoning()` quando il flag è presente
3. `notify()` continua a creare `_on_issue_reasoning()` normalmente quando il flag NON è presente (altri path che portano a REASONING)
4. Tutti i test esistenti continuano a passare
5. Il WebSocket notifier continua a ricevere l'evento correttamente (il flag non interferisce con altri notifier)

### Non incluso in questa issue
- Refactoring di `EventService` per filtraggio per notifier
- Modifiche al pattern di emissione eventi in altri punti del codice
