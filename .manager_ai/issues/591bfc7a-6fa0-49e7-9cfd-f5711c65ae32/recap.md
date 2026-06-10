## Recap

### Problema
In `backend/app/routers/queue.py`, gli endpoint `POST /api/queue/remove` e `GET /api/queue/position/{issue_id}` creavano nuove istanze `IssueQueueService()` invece di usare il singleton `issue_queue_service_ref` già importato a livello di modulo.

`IssueQueueService.__init__()` chiama `event_service.register(self)` a ogni costruzione, registrando un nuovo notifier su EventService. Questo non rompeva la funzionalità ma inquinava la lista dei notifier — ogni richiesta REST aggiungeva un notifier fantasma che veniva iterato a ogni emissione di evento.

### Soluzione applicata
- **remove_from_queue()** (linea 329): sostituito `registry = IssueQueueService()` con `registry = issue_queue_service_ref` + guard None → 503
- **get_queue_position()** (linea 374): sostituito `registry = IssueQueueService()` con `registry = issue_queue_service_ref` + guard None → 503
- Rimosse le import locali `from app.services.issue_queue_service import IssueQueueService` non più necessarie

### Verifica
- Sintassi Python verificata (ast.parse)
- Backend testato su porta 8001: entrambi gli endpoint restituiscono risposte corrette
- Nessuna chiamata a `IssueQueueService()` costruttore rimasta nel file

### Non fixato (fuori scope)
Lo stesso pattern in `backend/app/mcp/shared_tools.py` (queue_list, queue_remove, queue_position) — da fixare separatamente.