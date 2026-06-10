## Bug: Doppio start della coda — race condition in _dequeue_and_run

### Problema
Quando una issue finisce, la coda a volte avvia **due issue invece di una**. Lo stesso issue (quello in testa alla coda) parte in due terminali paralleli e indipendenti, causando esecuzioni duplicate e spreco di risorse.

### Root cause
Il problema è una **race condition** tra il cambio di stato dell'issue e la marcatura del QueueEntry.

#### Flusso attuale (buggy)
1. `_on_issue_finished(progetto)` chiama `_dequeue_and_run(progetto)`
2. `_dequeue_and_run()`:
   - `get_next_pending()` → trova entry B (PENDING)
   - `issue_service.update_status(B, REASONING)` — B QUEUED → REASONING ✓
   - `_emit_event({new_status: "Reasoning", issue_id: B})`
     - Questo triggera `IssueQueueService.notify()` → `create_task(_on_issue_reasoning(B))`
     - ⚠️ **create_task NON è awaited!** `_on_issue_reasoning` parte in un secondo momento
   - `run_issue(B)` — B parte normalmente ✓
3. **[in seguito]**: `_on_issue_reasoning(B)` → `mark_dispatching(B)` → QueueEntry PENDING → DISPATCHING

Il problema: tra il passo 2 (QUEUED→REASONING) e il passo 3 (QueueEntry→DISPATCHING) c'è una finestra temporale. **Il QueueEntry di B è ancora PENDING** in quel momento.

#### Se _on_issue_finished viene chiamato DUE VOLTE:
(vuoi per concorrenza asyncio, vuoi per doppia emissione dell'evento `issue_status_changed(Finished)` dalla pipeline + dal tool `complete_issue`)

1. Prima chiamata: B QUEUED→REASONING, QueueEntry ANCORA PENDING, `run_issue(B)` parte
2. Seconda chiamata: `get_next_pending()` → **restituisce ANCORA B** (QueueEntry è ancora PENDING!)
3. `update_status(B, REASONING)` → già REASONING, no-op silenzioso
4. `run_issue(B)` → **B parte in un SECONDO terminale!**

Ora ci sono due agenti indipendenti che lavorano sulla stessa issue.

### Perché succede
- La pipeline **Full Flow** ha una regola `pipeline_completed → set_issue_status("FINISHED")` che setta la issue a FINISHED nel DB
- MA questa regola NON emette eventi WebSocket, quindi la coda non avanza da sola
- Se l'agente nell'ultimo step chiama ANCHE `complete_issue` o `force_finish_issue`, si ha una doppia via di completamento
- La combinazione delle due genera talvolta due `issue_status_changed(Finished)` ravvicinati
- `IssueQueueService.notify()` dispatches entrambi via `create_task` (non c'è lock)
- `_dequeue_and_run` non è protetto da mutua esclusione per-progetto

### Soluzione proposta
Aggiungere un `asyncio.Lock()` per-progetto su `_dequeue_and_run` e marcare il QueueEntry come DISPATCHING **sincronamente dentro** `_dequeue_and_run`, non tramite `_on_issue_reasoning` async.

#### Modifica 1: Lock per-progetto
```python
class IssueQueueService(BaseNotifier):
    def __init__(self):
        self._dequeue_locks: dict[str, asyncio.Lock] = {}
        # ...
    
    async def _dequeue_and_run(self, project_id: str) -> None:
        lock = self._dequeue_locks.setdefault(project_id, asyncio.Lock())
        async with lock:
            # ... logica esistente ...
```

Questo garantisce che anche se `_on_issue_finished` viene chiamato due volte, `_dequeue_and_run` esegue una volta sola.

#### Modifica 2: Marcatura sincrona del QueueEntry
In `_dequeue_and_run`, dopo `get_next_pending()` ma PRIMA di emettere eventi:
```python
next_entry = await self.get_next_pending(project_id)
if next_entry is None:
    return

# ★ Marca subito come DISPATCHING (sincrono)
await self.mark_dispatching(next_entry.issue_id)

# Poi procedi col resto
await issue_service.update_status(...)
await session.commit()
await _emit_event(...)
```

Così anche se arriva una seconda chiamata (bloccata dal lock o meno), `get_next_pending` non restituisce più questo entry perché non è più PENDING.

### File interessati
- `backend/app/services/issue_queue_service.py` — aggiungere lock + marcatura sincrona

### Note
Questo bug è INDIPENDENTE dal refactoring "QueueEntry come unica fonte di verità" (schedulato separatamente). Il refactoring non risolve il doppio start — servono entrambi i fix.