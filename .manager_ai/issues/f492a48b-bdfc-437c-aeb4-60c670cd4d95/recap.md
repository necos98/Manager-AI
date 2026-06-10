## Recap: Indicatore stato dispatch coda

### Cosa è stato fatto
Aggiunto un indicatore visivo di stato del dispatch sulla pagina `/queue` per sapere se il servizio di coda sta attivamente processando issue.

### Modifiche

**1. Backend — `backend/app/routers/queue.py`**
- Aggiunto `dispatching_count: int` allo schema `QueueStatus`
- Aggiunta query per contare le `QueueEntry` in stato `DISPATCHING` in `get_queue_status()`

**2. Frontend — `frontend/src/features/queue/api.ts`**
- Aggiunto `dispatching_count: number` all'interfaccia `QueueStatus`

**3. Frontend — `frontend/src/routes/queue.tsx`**
- Aggiunta logica per determinare lo stato dispatch corrente (Attivo/In attesa/Fermo/Inattivo)
- Aggiunto badge nell'header con pallino colorato + label testuale

### Stati dell'indicatore
| Indicatore | Condizione |
|------------|-----------|
| 🟢 Attivo (verde) | `dispatching_count > 0 \|\| running_count > 0` |
| 🟡 In attesa (giallo) | `queued_count > 0` ma nessun dispatching/running attivo |
| 🔴 Fermo (rosso) | `paused = true` e nessun dispatching/running |
| ⚪ Inattivo (grigio) | Coda vuota, nulla in esecuzione |

### Verifica
- Backend: sintassi Python verificata con `ast.parse()`
- Schema Pydantic: `QueueStatus(dispatching_count=...)` testato con `model_dump()`
- Frontend: JSX strutturalmente valido, nessun componente rotto
