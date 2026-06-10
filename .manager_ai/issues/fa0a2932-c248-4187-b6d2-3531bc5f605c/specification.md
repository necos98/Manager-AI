## Queue Registry — Registro interno delle issue da dispacciare

### Problema

Attualmente `IssueQueueService` si basa esclusivamente sullo status `QUEUED` nel DB per sapere cosa deve fare. Quando un'issue viene auto-startata (`QUEUED → REASONING`), la coda perde ogni traccia:

- Non sa che l'ha già presa in carico
- Non sa se l'ha già dispacciata
- Se qualcosa va storto, non ha modo di riprendere il controllo
- Il worker della coda non ha un registro interno — non sa cosa sta processando

L'unico modo per sapere cosa c'è "in coda" è fare query SQL sullo status QUEUED, che è volatile: appena l'issue passa a REASONING, sparisce dalla coda.

### Soluzione

Aggiungere un **QueueRegistry** — una tabella DB `queue_entries` che tenga traccia di ogni operazione di accodamento e dispacciamento. Il registro è persistito su DB (SQLite) quindi resiliente a restart del backend.

### Cosa implementare

#### 1. Nuovo modello: QueueEntry (`backend/app/models/queue_entry.py`)

Colonne:
- `id` (UUID string, PK)
- `issue_id` (string, FK → issues.id)
- `project_id` (string, FK → projects.id, NOT NULL)
- `status` (Enum: `pending | dispatching | dispatched | failed`)
- `order` (Integer, NOT NULL — posizione FIFO incrementale per progetto)
- `created_at` (DateTime, server_default=now)
- `dispatched_at` (DateTime, nullable — quando è stata presa in carico)
- `error_message` (Text, nullable — se fallita)

Relazioni: nessuna (tabella di registro, non ORM-managed oltre alla definizione).

#### 2. Aggiornare IssueQueueService (`backend/app/services/issue_queue_service.py`)

Si trasforma da semplice `BaseNotifier` a `QueueRegistryService` con metodi:

- `register(issue_id, project_id)` — crea QueueEntry con status `pending`, assegna `order` = max order per quel progetto + 1
- `mark_dispatching(issue_id)` — status → `dispatching`, setta `dispatched_at`
- `mark_dispatched(issue_id)` — status → `dispatched`
- `mark_failed(issue_id, error)` — status → `failed`, setta `error_message`
- `get_next_pending(project_id)` — prossima entry con status `pending`, ordinata per `order` ASC
- `list_queue(project_id)` — lista corrente delle entry per progetto (tutti gli status)
- `list_all_global()` — lista globale di tutte le entry (per UI globale futura)

Flusso eventi aggiornato:
- **`queue_add` chiamato** → `register()` crea QueueEntry `pending`
- **Auto-start parte (Queued → Reasoning)** → `mark_dispatching()`
- **Issue finita (Finished)** → `mark_dispatched()`
- **Fallimento** → `mark_failed()`

Il dequeue ora ordina per `order` ASC (FIFO), non per l'implicito `created_at` dell'issue. Usa `get_next_pending()` invece di `list_by_project(status=QUEUED)`.

#### 3. Aggiornare MCP shared_tools (`backend/app/mcp/shared_tools.py`)

- `queue_add()` — dopo aver cambiato status a QUEUED, chiama anche `register()` sul QueueRegistry
- `queue_list()` — invece di query su status QUEUED, usa `list_queue()` del registry
- `queue_remove()` — oltre a cambiare status, marca la QueueEntry come `dispatched` (rimossa dalla coda attiva)
- `queue_position()` — usa il registry invece di contare QUEUED issues

#### 4. Database migration

Creare migration con `alembic revision --autogenerate` per la tabella `queue_entries`.

#### 5. Vantaggi

- La coda non perde mai il riferimento — anche se l'issue cambia status, QueueEntry rimane
- FIFO garantito dal `order` incrementale del registro, non dallo status volatile
- Storico persistente delle operazioni (log di dispacciamento)
- Possibile fare UI globale della coda (query su QueueEntry invece che su status QUEUED)
- Resiliente a restart del backend (persistito su SQLite)
- Tracciabilità: sappiamo esattamente quando un'issue è stata presa in carico (`dispatched_at`)

### Non incluso (scope futuri)

- Query per UI globale con filtri/paginazione avanzati
- Notifiche Telegram su fallimenti di dispacciamento
- Retry automatico su failed entries
