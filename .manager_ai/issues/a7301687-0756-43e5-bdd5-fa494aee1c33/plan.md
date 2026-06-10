# Piano: Fix race condition doppio start coda

## Task 1: Lock per-progetto in _dequeue_and_run
Aggiungere `self._dequeue_locks: dict[str, asyncio.Lock] = {}` in `__init__()`. Avvolgere il corpo di `_dequeue_and_run()` con `async with lock`.

**File**: `backend/app/services/issue_queue_service.py`
**Righe coinvolte**: `__init__` (dopo `event_service.register(self)`) e `_dequeue_and_run()` (dopo `try:`)

## Task 2: Marcatura sincrona QueueEntry in _dequeue_and_run
Dopo `get_next_pending()` e il check `if next_entry is None`, chiamare `await self.mark_dispatching(next_entry.issue_id)` PRIMA di `update_status()` e `_emit_event()`.

Inoltre, modificare `_on_issue_reasoning()` per gestire il caso "already DISPATCHING" senza loggare falsi warning: cercare sia PENDING che DISPATCHING in `mark_dispatching()`, e se già DISPATCHING ritorna subito.

**File**: `backend/app/services/issue_queue_service.py`

## Verifica
Dopo le modifiche, verificare con import test che la sintassi e la logica siano corrette.

**NON in scope**: test automatici con pytest (da issue separata)