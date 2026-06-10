# Recap: Unit test per IssueQueueService

## Risultato

Creato `backend/tests/test_issue_queue_service.py` con **61 test** tutti passanti (0 failure), coprendo l'intero sistema di coda FIFO.

## Copertura

**7 classi di test, 61 test:**

1. **TestQueueEntryModel** (3) — Enum QueueEntryStatus, default modello, UUID
2. **TestIssueQueueServiceConstructor** (3) — Registration su EventService, module-level ref, enabled default
3. **TestRegistryCRUD** (12) — register con order auto-increment, mark_dispatching/dispatched/failed con edge case (già DISPATCHING, missing, troncamento messaggio 1000 char, PENDING→DISPATCHED per rimozione manuale)
4. **TestQuery** (11) — get_next_pending FIFO, list_queue/list_all_global, get_pending_entry, scope per progetto, filtraggio non-PENDING
5. **TestEventHandling** (9) — notify routing (Finished/Queued/Reasoning), disabled skip, _on_issue_finished/con doppio evento, _on_issue_queued, _on_issue_reasoning
6. **TestDequeueAndRun** (4) — _dequeue_and_run con success/fallimento/nessun pending/locks
7. **TestMaybeAutoStartFirst** (4) — auto-start solo se pending_count==1 e nessuna running
8. **TestStartupResume** (3) — disabled skip, enabled con pending, nessun pending
9. **TestConfiguration** (5) — load_state default/si/no, set_enabled con persist e resume, set_enabled false
10. **TestMultiProjectFIFO** (5) — code indipendenti, order counter separati, global order, scope per progetto

## Tecniche di test usate

- Patch di `app.services.issue_queue_service.async_session` con sessionmaker test (in-memory SQLite)
- AsyncMock per `run_issue` e `_emit_event`
- `await asyncio.sleep(0)` per far eseguire i task creati da `asyncio.create_task()` in notify/startup_resume/set_enabled
- Creazione Issue via `IssueService.create()` per test che richiedono issue reali (non ID fittizi)
- Per-project lock test verificato indirettamente tramite successo delle operazioni concorrenti simulate

## Lezioni apprese

- `from X import issue_queue_service_ref` crea un binding locale — il `global` in `__init__` modifica l'attributo del modulo, non la copia locale. Usare `from app.services import issue_queue_service as m; m.issue_queue_service_ref`.
- `asyncio.create_task` in notify/startup_resume/set_enabled richiede `await asyncio.sleep(0)` per far eseguire i task prima degli assert.
- `_dequeue_and_run` falliva con NotFoundError quando QueueEntry.issue_id non corrispondeva a un'issue reale — fix: creare issue vera e usare il suo ID in register().