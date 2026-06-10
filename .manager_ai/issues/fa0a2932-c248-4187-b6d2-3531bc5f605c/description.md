## Queue Registry — Registro interno delle issue da dispacciare

### Problema
Attualmente IssueQueueService si basa esclusivamente sullo status `QUEUED` nel DB per sapere cosa deve fare. Quando un'issue viene auto-startata (`QUEUED → REASONING`), la coda perde ogni traccia:
- Non sa che l'ha già presa in carico
- Non sa se l'ha già dispacciata
- Se qualcosa va storto, non ha modo di riprendere il controllo
- Il worker della coda non ha un registro interno — non sa cosa sta processando

L'unico modo per sapere cosa c'è "in coda" è fare query SQL sullo status QUEUED, che è volatile.

### Soluzione
Aggiungere un **QueueRegistry** — un registro interno (tabella DB o struttura in memoria) che tenga traccia di ogni operazione di dispacciamento.

### Cosa implementare

**1. Nuova entità: QueueEntry (tabella DB o struttura)**
- `id` — UUID
- `issue_id` — riferimento all'issue
- `project_id` — progetto
- `status` — `pending | dispatching | dispatched | failed`
- `order` — posizione FIFO (incrementale)
- `created_at` — quando è stata accodata
- `dispatched_at` — quando è stata presa in carico
- `error_message` — se fallita

**2. IssueQueueService aggiornato**
- Quando `queue_add` viene chiamato → crea QueueEntry con status `pending` + assegna ordine
- Quando l'auto-start parte → QueueEntry → `dispatching`
- Quando il dequeue (su FINISHED) parte → QueueEntry → `dispatched`
- Su fallimento → QueueEntry → `failed`
- Il dequeue ordina per `order` ASC (FIFO), non per `created_at`

**3. QueueRegistryService (o integrato in IssueQueueService)**
- `register(issue_id, project_id)` — crea entry
- `mark_dispatching(issue_id)` — in corso
- `mark_dispatched(issue_id)` — completato
- `mark_failed(issue_id, error)` — fallito
- `get_next_pending(project_id)` — prossimo in ordine FIFO
- `list_queue(project_id)` — lista corrente
- `list_all_global()` — lista globale (per UI globale)

**4. Vantaggi**
- La coda non perde mai il riferimento — anche se l'issue cambia status
- FIFO garantito dal registro, non dallo status volativo
- Storico delle operazioni (log di dispacciamento)
- Possibile fare UI globale della coda (query su QueueEntry invece che su status QUEUED)
- Resiliente a restart del backend (persistito su DB)

### File da modificare
- `backend/app/services/issue_queue_service.py` — riscrivere logica usando QueueEntry
- `backend/app/models/queue_entry.py` — **NUOVO**: modello SQLAlchemy per QueueEntry
- `backend/app/mcp/shared_tools.py` — aggiornare queue_add/queue_list per usare QueueEntry
- `backend/app/mcp/orchestrator_server.py` — registrare eventuali nuovi tool
- Database migration per creare tabella queue_entries