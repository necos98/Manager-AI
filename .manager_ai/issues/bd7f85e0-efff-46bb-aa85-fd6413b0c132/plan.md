# Piano di implementazione

## Modifica 1: `issue_queue_service.py` — rilassare il guard in `_maybe_auto_start_first`

**File:** `backend/app/services/issue_queue_service.py` (riga 538)

**Cambio:** Sostituire `if pending_count != 1:` con `if pending_count < 1:`

Questo è un change di una singola riga. La logica:
- `pending_count == 0` → nessuna pending entry → return (nessun cambiamento)
- `pending_count >= 1` → almeno una pending entry → procedi al secondo guard (controllo running)
- Il secondo guard (controllo running) e il lock per-progetto in `_dequeue_and_run()` garantiscono sicurezza

## Modifica 2: aggiornare il test `test_skips_when_multiple_pending`

**File:** `backend/tests/test_issue_queue_service.py` (riga 770)

**Cambio:** Il test attualmente registra 2 issue (iss-1, iss-2) e si aspetta che `_dequeue_and_run` NON sia chiamato. Con il nuovo comportamento, deve aspettarsi che `_dequeue_and_run` SIA chiamato (perché ci sono >=1 pending e nulla è in esecuzione).

Il test va rinominato in `test_auto_starts_when_multiple_pending` e l'assert cambiato da `assert_not_called()` a `assert_awaited_once_with(project.id)`.

## Verifica

1. Eseguire `test_auto_starts_when_only_pending` — deve passare (invariato)
2. Eseguire `test_auto_starts_when_multiple_pending` — deve passare (aggiornato)
3. Eseguire `test_skips_when_issue_running` — deve passare (invariato)
4. Eseguire `test_skips_when_no_pending_entries` — deve passare (invariato)
5. Eseguire tutta la classe `TestMaybeAutoStartFirst` per confermare