## Implementation Plan

### Task 1 — Backend: REST endpoints for queue add/remove/position
Aggiungere tre endpoint REST nel file `backend/app/routers/queue.py`:
- `POST /api/queue/add` — body: `{project_id, issue_id}`, validazione (NEW/ACCEPTED), registra QueueEntry, emette evento
- `POST /api/queue/remove` — body: `{project_id, issue_id}`, verifica pending, mark_dispatched, emette evento
- `GET /api/queue/position/{issue_id}` — query param `project_id`, calcola posizione FIFO, restituisce `{position, issue_id, in_queue, status}`

### Task 2 — Frontend API: new queue functions and hooks
Aggiungere in `frontend/src/features/queue/api.ts`:
- `addToQueue(projectId, issueId)` → POST /api/queue/add
- `removeFromQueue(projectId, issueId)` → POST /api/queue/remove
- `fetchQueuePosition(issueId, projectId)` → GET /api/queue/position/{issueId}?project_id=...

Aggiungere in `frontend/src/features/queue/hooks.ts`:
- `useQueuePosition(issueId, projectId)` — hook per leggere la posizione in coda di una issue
- `useAddToQueue()` — mutation per aggiungere
- `useRemoveFromQueue()` — mutation per rimuovere

### Task 3 — Frontend: Issue detail page queue buttons
Modificare `frontend/src/features/issues/components/issue-actions.tsx` per mostrare pulsanti "Add to Queue" / "Remove from Queue" nella IssueActions, basandosi sul queue position hook. Condizioni:
- Issue in NEW o ACCEPTED e non in coda → mostra pulsante "Add to Queue"
- Issue in coda → mostra posizione e pulsante "Remove from Queue"
- Issue in altri stati → nessun pulsante queue

### Task 4 — Frontend: Queue page remove button
Modificare `frontend/src/routes/queue.tsx` per aggiungere una colonna "Actions" con pulsante "Remove" su ogni riga della tabella "In coda", con conferma Dialog.
