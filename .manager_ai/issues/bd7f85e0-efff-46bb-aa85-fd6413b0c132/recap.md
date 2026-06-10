## Recap

### Problema
`_maybe_auto_start_first()` usava `pending_count != 1` come guard, partendo solo se c'era esattamente 1 pending entry. Questo era troppo conservativo: se la coda aveva >1 pending (es. perché l'auto-processing era stato abilitato dopo che più issue erano già state accodate, o perché `startup_resume()` era fallito), la coda rimaneva bloccata finché non arrivava un Finished event.

### Soluzione
Singola riga cambiata in `backend/app/services/issue_queue_service.py:538`:
- **Prima:** `if pending_count != 1: return`
- **Dopo:** `if pending_count < 1: return`

Ora auto-start quando c'è almeno 1 pending e nessuna issue è in esecuzione. La sicurezza è garantita dal secondo guard (`running` check) e dal lock per-progetto in `_dequeue_and_run()`.

### Test
- `test_skips_when_multiple_pending` rinominato in `test_auto_starts_when_multiple_pending` con assert invertito (`assert_awaited_once` invece di `assert_not_called`)
- 4/4 test della classe `TestMaybeAutoStartFirst` passano
- 63/63 test del file `test_issue_queue_service.py` passano

### Files modificati
1. `backend/app/services/issue_queue_service.py` — change singola riga (pending_count !=1 → <1)
2. `backend/tests/test_issue_queue_service.py` — test aggiornato per nuova semantica