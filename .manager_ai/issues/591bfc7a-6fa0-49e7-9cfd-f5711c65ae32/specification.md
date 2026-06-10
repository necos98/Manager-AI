# IssueQueueService() creato direttamente nelle route REST invece di usare il singleton

## Problema

In `backend/app/routers/queue.py`, due endpoint REST creano una nuova istanza `IssueQueueService()` invece di usare il singleton `issue_queue_service_ref` già importato:

1. **POST /api/queue/remove** (linea 329): `registry = IssueQueueService()`
2. **GET /api/queue/position/{issue_id}** (linea 374): `registry = IssueQueueService()`

`IssueQueueService.__init__()` chiama `event_service.register(self)` a ogni costruzione (linea 47 di `issue_queue_service.py`), registrando un nuovo notifier su EventService.

**Perché non rompe nulla:** Le operazioni chiamate (`get_pending_entry`, `list_queue`, `mark_dispatched`) non dipendono dallo stato dell'istanza (usano sessioni DB proprie). Il singleton originale rimane registrato e gestisce normalmente gli eventi.

**Effetto collaterale:** Ogni chiamata REST a questi due endpoint aggiunge un nuovo notifier alla lista di EventService. Con molte richieste, la lista cresce indefinitamente. Gli eventi emessi da `emit()` iterano su TUTTI i notifier registrati — più notifier spuri = overhead inutile a ogni evento.

## Soluzione proposta

Sostituire `IssueQueueService()` con `issue_queue_service_ref` in entrambi gli endpoint, aggiungendo un guard `if issue_queue_service_ref is None`, seguendo lo stesso pattern già usato dall'endpoint `POST /api/queue/auto-process` (linee 248-249).

**Perché safe:** `issue_queue_service_ref` è già importato a linea 21 del router. Il singleton viene creato in `main.py` (linea 306) durante il lifespan dell'applicazione, prima che qualsiasi route venga servita. Il guard None è comunque una safety net.

### File da modificare

- `backend/app/routers/queue.py` — solo due righe: linee 329 e 374

### Cosa NON fixa questa issue

Lo stesso pattern esiste in `backend/app/mcp/shared_tools.py` (linee 1649, 1697, 1731) per i tool MCP `queue_list`, `queue_remove`, `queue_position`. Questi vanno fixati separatamente perché sono serviti su un trasporto diverso (MCP vs REST) e seguono un pattern di sessione differente.

## Verifica

1. Verificare che `issue_queue_service_ref` sia importato (già presente a linea 21)
2. Controllare che il guard None sia presente
3. Testare import: `python -c "import ast; ast.parse(open('backend/app/routers/queue.py').read())"`
4. Testare gli endpoint via curl sul backend in esecuzione
