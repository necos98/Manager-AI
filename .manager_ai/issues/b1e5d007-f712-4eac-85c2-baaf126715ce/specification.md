## Issue Queue & Running — UI Globale

### Obiettivo
Creare una pagina globale `/queue` che mostri lo stato della coda delle issue a livello **globale** (tutti i progetti), con sezioni "In esecuzione" e "In coda".

---

### Stato attuale del codebase

**Backend (esistente):**
- `IssueStatus.QUEUED` nel modello Issue (file-backed `issue_store`)
- `IssueQueueService` (BaseNotifier su EventService) — auto-dequeue FIFO per-progetto quando una issue passa a Finished
- `IssueService.list_by_project()` — filtra per status ma è per-progetto
- `TerminalService.list_active()` — elenca terminali attivi con `project_id` e `issue_id`
- `IssueService.get_by_id()` — risolve una issue su qualsiasi progetto (O(1) reverse index)
- Nessun endpoint REST globale per coda/running

**Frontend (esistente):**
- TanStack Router con `routeTree.gen.ts` auto-generato
- `project-sidebar.tsx` — sezione "Global" con Dashboard, Terminals, Agents, Provider, Questions, Pipelines, Settings
- EventContext WebSocket per aggiornamenti real-time

---

### 1. Backend API endpoints

#### Nuovo file: `backend/app/routers/queue.py`
Router globale non-scoped a un project.

#### `GET /api/queue` — Lista globale QUEUED
- Attraversa TUTTI i progetti non-archiviati
- Per ogni progetto, chiama `IssueService.list_by_project(status=IssueStatus.QUEUED)`
- Ritorna lista piatta con: `{position, issue_id, issue_name, issue_description (primi 100 char), project_id, project_name, created_at}`
- Ordinata per `created_at` ASC (FIFO globale)
- Aggiunge posizione numerica (1-based)

#### `GET /api/queue/running` — Lista globale in esecuzione
- Ottiene tutti i terminali attivi via `TerminalService.list_active()`
- Per ogni terminale, arricchisce con issue_name e project_name
- Filtra solo terminali con `project_id` e `issue_id` non vuoti (esclude standalone)
- Ritorna: `{issue_id, issue_name, project_id, project_name, terminal_id, started_at, issue_status}`

#### `GET /api/queue/status` — Stato globale della coda
- Totale QUEUED count
- Totale RUNNING count
- work_queue_paused da SettingsService

#### Schema di risposta (queue.py come file separato con schemi interni)

### 2. Frontend — Nuova pagina `/queue`

#### Nuovo file: `frontend/src/routes/queue.tsx`
- Pagina globale (non dentro un progetto)
- Due sezioni principali:

**Sezione "In esecuzione"**
- Card/lista di issue attualmente con terminale attivo
- Per ogni issue: spinner animato, issue_name → link alla issue, project_name → link al progetto
- Stato "Nessuna issue in esecuzione" quando vuoto
- Auto-refresh via WebSocket (eventi `terminal_created` / `terminal_closed`)

**Sezione "In coda"**
- Lista ordinata di issue QUEUED
- Per ogni issue: posizione numerica, issue_name → link, project_name → link, created_at
- Prima riga evidenziata (next to run)
- Stato "Nessuna issue in coda" quando vuoto
- Contatore: "X issue in coda"
- Auto-refresh via WebSocket (eventi `issue_status_changed` con new_status=Queued/Reasoning)

#### Registrazione route
- Aggiungere `import { Route as QueueRouteImport } from "./routes/queue"` in `routeTree.gen.ts`
- Aggiungere `const QueueRoute = QueueRouteImport.update({ id: "/queue", path: "/queue", getParentRoute: () => rootRouteImport })`
- Aggiungere a `FileRoutesByFullPath`, `FileRoutesById`, `FileRouteTypes`
- Aggiungere a `RootRouteChildren`

#### Navigazione sidebar
- In `project-sidebar.tsx`, sezione "Global": aggiungere voce "Queue" tra Dashboard e Terminals con icona `ListOrdered` (o `List`)

#### API hooks
- Nuovo file o estensione in `frontend/src/features/queue/`:
  - `api.ts`: funzioni `fetchGlobalQueue()`, `fetchGlobalRunning()` via fetch
  - `hooks.ts`: React Query hooks con refetch automatico, invalidazione su eventi WebSocket
- In `event-context.tsx`: subscribe a `issue_status_changed`, `terminal_created`, `terminal_closed` per invalidare query cache

### 3. WebSocket real-time
L'EventService già emette:
- `issue_status_changed` con `new_status`, `project_id`, `issue_id` — usare per aggiornare coda
- Eventi terminale (`terminal_created`, `terminal_closed`) — esistenti? Se no, emetterli da terminal_service

### 4. Cosa NON serve
- ❌ Nessuna azione CRUD dalla UI (nessun drag&drop, pulsanti remove/pause per item singoli)
- ❌ Nessuna gestione priorità — solo FIFO visivo
- ❌ Nessun filtro per progetto sulla pagina globale
- ❌ Nessuna modifica a `IssueQueueService` — solo lettura

### 5. Dipendenze
- `lucide-react` — icona `ListOrdered` per sidebar (già presente come dipendenza)
