## Implementation Plan

### Task 1: Aggiungere flag `_queue_dispatching_handled` all'evento in `_dequeue_and_run()`
- Modificare la chiamata a `_emit_event()` in `_dequeue_and_run()` (linea 471-478 di `issue_queue_service.py`)
- Aggiungere `"_queue_dispatching_handled": True` all'event dict

### Task 2: Saltare `_on_issue_reasoning` in `notify()` quando il flag è presente
- Modificare `notify()` in `issue_queue_service.py`
- Nel branch `new_status == "Reasoning"`, aggiungere un check: se `event.get("_queue_dispatching_handled")` è True, saltare la creazione del task

### Task 3: Scrivere test per la nuova logica
- Aggiungere un test che verifica che `_on_issue_reasoning` NON venga chiamato quando l'evento ha il flag
- Aggiungere un test che verifica che `_on_issue_reasoning` VENGA chiamato quando l'evento NON ha il flag (comportamento normale)
- Verificare che il flag non interferisca con altri branch di `notify()` (Finished, Queued)

### Task 4: Eseguire i test esistenti
- Lanciare `pytest` per verificare che tutti i test passino
