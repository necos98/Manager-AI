## Specifica: Indicatore stato dispatch coda

### Problema
La UI della pagina `/queue` mostra solo un toggle **Paused** (basato su `work_queue_paused`) e un toggle **Auto-process** (basato su `queue_auto_process`). Non c'è modo di capire se il servizio di dispatch (`IssueQueueService`) sta effettivamente girando o se c'è una issue in fase di dispatching attivo.

### Stato attuale
- `GET /api/queue/status` restituisce: `{ queued_count, running_count, paused, auto_process_enabled }`
- Frontend `/queue` mostra solo `{n} running` e `{n} queued` in header, più il toggle Paused in `work-queue-status.tsx` e Auto-process nella pagina globale.
- Non esiste un indicatore che comunichi "il sistema sta processando attivamente la coda".

### Soluzione proposta

**Backend — `backend/app/routers/queue.py`:**

Aggiungere campo `dispatching_count: int` allo schema `QueueStatus`:
```python
class QueueStatus(BaseModel):
    queued_count: int
    running_count: int
    dispatching_count: int  # Nuovo
    paused: bool
    auto_process_enabled: bool
```

In `get_queue_status()`, contare le `QueueEntry` con `status == QueueEntryStatus.DISPATCHING` su tutti i progetti:
```python
result = await db.execute(
    select(sa_func.count(QueueEntry.id))
    .where(QueueEntry.status == QueueEntryStatus.DISPATCHING)
)
dispatching_count: int = result.scalar() or 0
```

**Frontend — `frontend/src/features/queue/api.ts`:**

Aggiungere `dispatching_count: number` all'interfaccia `QueueStatus`.

**Frontend — `frontend/src/routes/queue.tsx`:**

In header (area delle statistiche a destra, accanto a `{n} running` / `{n} queued`), aggiungere un **badge/indicatore di stato dispatch** con 4 stati:

| Stato | Colore/Icona | Condizione |
|-------|-------------|------------|
| 🟢 Attivo | Testo verde + pallino verde | `dispatching_count > 0 \|\| running_count > 0` |
| 🟡 In attesa | Testo giallo + pallino giallo | `queued_count > 0 && nessun dispatching/running` |
| 🔴 Fermo | Testo rosso + pallino rosso | `paused === true` (solo se non attivo) |
| ⚪ Inattivo | Testo grigio + pallino grigio | coda vuota e nessuna esecuzione |

Logica di priorità: se `paused=true` ma c'è running/dispatching, mostra **Attivo** (le issue in esecuzione continuano). Lo stato **Fermo** si mostra solo quando paused=true E non c'è nulla in esecuzione.

Posizionamento: dopo i contatori `{n} running` / `{n} queued`, prima del toggle Auto-process.

### File modificati
1. `backend/app/routers/queue.py` — aggiungere `dispatching_count` a QueueStatus + logica count
2. `frontend/src/features/queue/api.ts` — aggiungere `dispatching_count: number` a QueueStatus
3. `frontend/src/routes/queue.tsx` — aggiungere indicatore visivo nell'header

### Non modificato
- `work-queue-status.tsx` (progetto-specific) — non rilevante per questa issue globale
- Nessuna modifica a servizi backend o modelli — solo il router queue.py
