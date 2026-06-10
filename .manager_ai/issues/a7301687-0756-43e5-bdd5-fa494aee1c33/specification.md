# Specifica: Fix race condition doppio start coda

## Problema
Quando una issue finisce, `_on_issue_finished()` chiama `_dequeue_and_run()` che può essere invocato più volte (da pipeline events + `complete_issue`), causando l'avvio della stessa issue in **due terminali paralleli**.

## Root cause
Due vulnerabilità concorrenti:

### 1. QueueEntry non marcato sincronamente
`_dequeue_and_run()` chiama `get_next_pending()` che restituisce un QueueEntry PENDING, ma la marcatura a DISPATCHING avviene **dopo** `_emit_event()`, tramite `_on_issue_reasoning()` lanciato con `asyncio.create_task()` (non awaited). Tra `get_next_pending()` e l'esecuzione effettiva di `mark_dispatching()` c'è una finestra temporale in cui una seconda chiamata a `_dequeue_and_run()` trova lo stesso QueueEntry ancora PENDING.

### 2. Nessuna mutua esclusione per-progetto
`_dequeue_and_run()` non è protetto da lock. Due chiamate concorrenti per lo stesso progetto possono eseguire `get_next_pending()` prima che una delle due abbia marcato il QueueEntry.

## Soluzione

### Modifica 1: Lock per-progetto
Aggiungere `asyncio.Lock()` per-progetto in `IssueQueueService.__init__()`. `_dequeue_and_run()` acquisisce il lock all'inizio, garantendo che anche chiamate multiple ravvicinate eseguano in serie.

```python
self._dequeue_locks: dict[str, asyncio.Lock] = {}

async def _dequeue_and_run(self, project_id: str) -> None:
    lock = self._dequeue_locks.setdefault(project_id, asyncio.Lock())
    async with lock:
        # ... logica esistente ...
```

### Modifica 2: Marcatura sincrona del QueueEntry
Dentro `_dequeue_and_run()`, dopo `get_next_pending()` ma PRIMA di `update_status()` e `_emit_event()`:

```python
next_entry = await self.get_next_pending(project_id)
if next_entry is None:
    return

# ★ Marca subito come DISPATCHING (sincrono, senza attendere _on_issue_reasoning)
await self.mark_dispatching(next_entry.issue_id)
```

Così il QueueEntry viene marcato DISPATCHING **prima** che qualsiasi evento venga emesso. Anche se arriva una seconda chiamata (bloccata dal lock o meno), `get_next_pending()` non restituirà più questo entry.

### Nota su _on_issue_reasoning
`_on_issue_reasoning()` tenta `mark_dispatching()` sull'evento `issue_status_changed → REASONING`. Dopo Modifica 2, il QueueEntry è già DISPATCHING → `_get_pending_by_issue()` non lo trova → logga un warning e ritorna None. È un falso positivo innocuo.

Per evitare falsi warning, si può rendere `mark_dispatching()` tollerante allo stato "already dispatching": invece di cercare solo PENDING, cerca PENDING o DISPATCHING, e skip se già DISPATCHING.

## File interessati
- `backend/app/services/issue_queue_service.py` — unico file da modificare

## Non in scope
- Refactoring "QueueEntry come unica fonte di verità" (già fatto in c6dbf46b)
- Test automatici (da aggiungere in issue separata)
- Modifiche a pipeline_run_service.py o altri servizi