## Recap — Queue management from issue detail page + remove from Queue section

### Implementazione completata

**Task 1 — Backend REST endpoints** (`backend/app/routers/queue.py`)
- `POST /api/queue/add` — aggiunge issue alla coda (valida NEW/ACCEPTED, emette evento per IssueQueueService)
- `POST /api/queue/remove` — rimuove issue dalla coda (marca QueueEntry come dispatched)
- `GET /api/queue/position/{issue_id}` — ottiene posizione FIFO di una specifica issue
- Aggiunte import: `HTTPException`, `AppError`

**Task 2 — Frontend API/hooks** (`features/queue/api.ts`, `features/queue/hooks.ts`)
- `addToQueue(projectId, issueId)` e `removeFromQueue(projectId, issueId)` — chiamate REST
- `fetchQueuePosition(issueId, projectId)` — query posizione
- Hook `useQueuePosition` (auto-refetch 10s)
- Mutazioni `useAddToQueue` e `useRemoveFromQueue` con cache invalidation

**Task 3 — Issue detail page** (`features/issues/components/issue-actions.tsx`)
- Issue NEW o ACCEPTED e non in coda → pulsante "Add to Queue" con icona ListPlus
- Issue in coda → pulsante "Remove from Queue (#posizione)" con icona ListX (stile amber)
- Loading state con spinner durante le operazioni
- Queue position si aggiorna automaticamente ogni 10s

**Task 4 — Queue page** (`routes/queue.tsx`)
- Colonna "Actions" nella tabella "In coda"
- Pulsante Trash2 per rimuovere ogni issue con conferma Dialog
- Conferma mostra nome issue, opzioni Cancel/Remove
- Cache invalidation automatica dopo rimozione

### Note
- Le issue mantengono il loro status originale (NEW o ACCEPTED) — QueueEntry è il record autoritativo
- L'add emette un evento synthetico `issue_status_changed(Queued)` che triggera l'IssueQueueService.notify() per creare il QueueEntry
- Il remove marca il QueueEntry come dispatched (non lo elimina) — tracciabilità FIFO preservata