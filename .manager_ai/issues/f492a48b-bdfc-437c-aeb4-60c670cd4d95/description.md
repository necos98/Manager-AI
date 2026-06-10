## Indicatore stato processo coda (dispatching attivo/in pausa/fermo)

**Problema:** Non c'è un modo per capire se il processo che si occupa dello smistamento automatico della coda (il "queue dispatch") è effettivamente attivo. La UI mostra solo il toggle **Paused** (basato su `work_queue_paused`), ma questo non dice se il servizio sta girando.

**Cosa manca:**
- Un indicatore che comunichi se `IssueQueueService` sta attivamente processando la coda (es. `_dequeue_and_run` in esecuzione)
- Sapere se il sistema è in uno stato "bloccato" (es. nessun task di dispatch attivo ma ci sono issue QUEUED)

**Soluzione proposta:**

**Backend — `GET /api/queue/status`:**
Aggiungere campo `dispatching: bool` che indica se c'è almeno una issue in stato `DISPATCHING` (QueueEntry) o `REASONING` (IssueStatus).

Schema aggiornato:
```python
class QueueStatus(BaseModel):
    queued_count: int
    running_count: int
    dispatching_count: int  # Nuovo: issue in fase di dispatch attivo
    paused: bool
```

**Frontend — pagina `/queue`:**
Aggiungere badge/indicatore:
- 🟢 **Attivo** — se dispatching_count > 0 o running_count > 0
- 🟡 **In attesa** — se ci sono issue QUEUED ma nessuna in elaborazione
- 🔴 **Fermo** — se paused=true
- ⚪ **Inattivo** — se coda vuota

**File interessati:**
- `backend/app/routers/queue.py` — aggiungere `dispatching_count` a QueueStatus
- `frontend/src/features/queue/api.ts` — aggiornare interfaccia QueueStatus
- `frontend/src/routes/queue.tsx` — aggiungere indicatore visivo

**Priorità:** Media — utile per debug e monitoraggio