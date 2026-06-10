## Recap: Evento ridondante in _dequeue_and_run

### Problema
`_dequeue_and_run()` marcava la QueueEntry come DISPATCHING sincronamente (linea 448), poi emetteva `issue_status_changed(Reasoning)` via EventService. Il notifier `IssueQueueService` stesso riceveva l'evento e spawnava `_on_issue_reasoning()` che faceva un'altra `mark_dispatching()` → no-op. Ogni dispatch sprecava un async task + una query DB.

### Soluzione
1. **`_dequeue_and_run()`**: aggiunto `"_queue_dispatching_handled": True` all'evento emesso (file `issue_queue_service.py`, linea 478)
2. **`notify()`**: nel branch `new_status == "Reasoning"`, quando il flag è presente, ritorna subito senza creare `_on_issue_reasoning` task (file `issue_queue_service.py`, linee 392-393)
3. **Test**: 2 nuovi test che verificano:
   - `test_notify_reasoning_skipped_with_flag` — con flag presente, `_on_issue_reasoning` NON viene chiamato
   - `test_notify_reasoning_flag_does_not_affect_other_statuses` — Finished e Queued continuano a funzionare anche con flag presente

### Verifica
- **63 tests passati** (61 pre-esistenti + 2 nuovi) in 4.81s
- Nessuna modifica all'interfaccia pubblica, EventService, o altri notifier
