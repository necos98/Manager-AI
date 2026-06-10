## Obiettivo
Permettere all'utente di aggiungere/rimuovere una issue dalla coda (Queue) direttamente dalla pagina di dettaglio dell'issue, e di eliminare una issue programmata in coda direttamente dalla sezione Queue globale.

## Contesto
Manager AI ha già un sistema di coda FIFO persistente (QueueEntry DB table) con dispatch automatico. I tool MCP `queue_add`, `queue_remove`, `queue_list` esistono già in `shared_tools.py`. Il frontend ha una pagina Queue globale (`/queue`) che elenca le issue in coda e in esecuzione, ma:
- Non c'è modo di aggiungere/rimuovere una issue dalla coda dalla pagina issue detail
- Non c'è un pulsante per rimuovere una issue dalla coda nella pagina Queue

## Requisiti Funzionali

### 1. Backend — REST endpoints
Aggiungere tre nuovi endpoint al router `queue.py`:

1. **`POST /api/queue/add`** — Aggiunge una issue alla coda
   - Body: `{project_id: string, issue_id: string}`
   - Validazione: issue deve essere in status NEW o ACCEPTED
   - Crea QueueEntry e emette evento `issue_status_changed` → `new_status=Queued`
   - L'IssueQueueService registra il QueueEntry tramite event listener

2. **`POST /api/queue/remove`** — Rimuove una issue dalla coda
   - Body: `{project_id: string, issue_id: string}`
   - Verifica che l'issue abbia un QueueEntry PENDING
   - Marca QueueEntry come dispatched (non la elimina — mantiene tracciabilità)
   - Emette evento per cache invalidation frontend

3. **`GET /api/queue/position/{issue_id}`** — Ottiene la posizione in coda di una specifica issue
   - Parametri: issue_id (path param), project_id (query param)
   - Restituisce `{position: number | null, issue_id, in_queue: boolean, status}`
   - Usato dal frontend per decidere se mostrare "Add to Queue" o "Remove from Queue"

### 2. Frontend — Issue detail page
Aggiungere pulsanti per gestire la coda nella `IssueActions` component:

- **Se l'issue NON è in coda** e lo status è NEW o ACCEPTED: mostra pulsante "Add to Queue"
- **Se l'issue È in coda**: mostra posizione in coda e pulsante "Remove from Queue"

Nuovo hook `useQueuePosition(issueId)` in `features/queue/hooks.ts` che interroga `GET /api/queue/position/{issue_id}?project_id={projectId}`.

### 3. Frontend — Queue page
Aggiungere un pulsante "Remove" su ogni riga della tabella "In coda" nella pagina Queue.

- Pulsante "Remove" nella colonna azioni (accanto al creato)
- Conferma prima di rimuovere (Dialog)
- Dopo la rimozione, invalidare la query cache della coda

## Dettagli Implementativi

- `queue_add` backend: importare `IssueQueueService` e chiamare `register()`, poi emettere evento con status "Queued" (come fa già il tool MCP)
- `queue_remove` backend: chiamare `get_pending_entry()` e `mark_dispatched()` su IssueQueueService
- Le issue mantengono il loro status originale (NEW o ACCEPTED) — QueueEntry è il record autoritativo
- Evento `issue_status_changed` con `new_status` fittizio "Queued" per triggerare IssueQueueService e invalidare cache frontend

## Non Incluso
- Non modificare la coda FIFO esistente o la logica di auto-start
- Non modificare IssueStatus.QUEUED (deprecato ma mantenuto per backward compat)
- Non aggiungere auto-process toggle nell'issue detail (già presente nella pagina Queue)
