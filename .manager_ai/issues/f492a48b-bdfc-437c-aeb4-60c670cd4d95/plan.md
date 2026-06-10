## Piano di implementazione: Indicatore stato dispatch coda

### Task 1: Backend — Aggiungere `dispatching_count` a QueueStatus + logica count
**File:** `backend/app/routers/queue.py`
- Aggiungere `dispatching_count: int` allo schema `QueueStatus`
- In `get_queue_status()`, dopo i count esistenti, aggiungere query per contare QueueEntry con status DISPATCHING
- Ritornare `dispatching_count` nel dizionario QueueStatus

### Task 2: Frontend — Aggiungere `dispatching_count` all'interfaccia QueueStatus
**File:** `frontend/src/features/queue/api.ts`
- Aggiungere `dispatching_count: number` all'interfaccia `QueueStatus`

### Task 3: Frontend — Aggiungere indicatore visivo nell'header della pagina /queue
**File:** `frontend/src/routes/queue.tsx`
- Estrarre `dispatching_count` da `statusData`
- Aggiungere logica per determinare lo stato corrente (attivo/in attesa/fermo/inattivo)
- Renderizzare badge con pallino colorato + testo descrittivo
- Posizionamento: dopo i contatori `{n} running` / `{n} queued`, prima del toggle Auto-process
