## Specifica Tecnica: QueueEntry come unica fonte di verità

### Obiettivo
Eliminare il dual-state tra `Issue.status == "Queued"` e `QueueEntry.status == "pending"`. La presenza in coda è definita ESCLUSIVAMENTE da un QueueEntry con status PENDING. `IssueStatus.QUEUED` non viene più usato per logica di coda (mantenuto come deprecated per backward compat dei dati esistenti).

### Principio guida
Un'issue in coda è sempre NEW o ACCEPTED — mai QUEUED. Il `QueueEntry` è l'unico indicatore.

### Modifiche

#### 1. `backend/app/mcp/shared_tools.py` — queue_add()
- RIMUOVERE: `svc.update_fields(issue_id, project_id, status=IssueStatus.QUEUED)`
- L'issue resta in NEW o ACCEPTED (non cambia status)
- L'evento `issue_status_changed` con new_status="Queued" va comunque EMESSO (serve da trigger per IssueQueueService e per far invalidare la cache della UI). È un evento sintetico — non riflette un cambio reale di Issue.status ma un "segnale" per la coda.
- Il return dell'MCP tool riporta ancora `status: issue.status` (che sarà NEW o ACCEPTED, non QUEUED)
- AGGIUNGERE chiamata diretta a `IssueQueueService().register()` per creare subito il QueueEntry, invece di aspettare che l'evento lo faccia (più deterministico, meno race condition)
- AGGIUNGERE chiamata a `_maybe_auto_start_first()` invece di affidarsi all'evento

#### 2. `backend/app/mcp/shared_tools.py` — queue_remove()
- RIMUOVERE: controllo `issue.status != IssueStatus.QUEUED.value`
- SOSTITUIRE CON: controllo `IssueQueueService()._get_pending_by_issue()` — se non c'è QueueEntry PENDING, errore "Issue is not in queue"
- RIMUOVERE: `svc.update_fields(status=NEW)` — l'issue mantiene il suo status originale
- MANTENERE: `registry.mark_dispatched()` per rimuovere dalla coda
- Evento da cambiare: non più `issue_status_changed` ma emettere `issue_dequeued` (o mantenerlo come evento sintetico per compatibilità UI)

#### 3. `backend/app/services/issue_queue_service.py` — _dequeue_and_run()
- CAMBIARE: non più `await issue_service.update_status(... IssueStatus.REASONING)` da QUEUED a REASONING
- Invece: usare `create_spec()` o `update_status()` per portare da NEW/ACCEPTED direttamente a REASONING
- L'evento `issue_status_changed` con new_status=Reasoning va ancora emesso

#### 4. `backend/app/services/issue_queue_service.py` — _on_issue_queued()
- RIMUOVERE: chiamata a `self.register()` — ora la registrazione è in queue_add() direttamente
- MANTENERE: chiamata a `self._maybe_auto_start_first()`
- Quindi `_on_issue_queued()` diventa solo `_maybe_auto_start_first()`

#### 5. `backend/app/services/issue_queue_service.py` — notify()
- CAMBIARE: il listener per `new_status == "Queued"` ora ascolta per `event.get("type") == "issue_queued"` o mantiene il matching su `new_status == "Queued"` (l'evento sintetico)

**Decisione architetturale:** Manteniamo il listener su `issue_status_changed` con new_status="Queued" perché:
- La UI frontend usa già questo pattern per invalidare cache (event-context.tsx, queue.tsx)
- IssueQueueService deve ancora agire su questo evento (auto-start primo in coda)
- È un "evento di notifica" distinto dal "cambio di stato effettivo"

#### 6. `backend/app/routers/queue.py` — GET /api/queue
- RIMUOVERE: query `issue_service.list_by_project(status=IssueStatus.QUEUED)`
- SOSTITUIRE CON: query diretta a `QueueEntry` con status PENDING, arricchita con issue_name/description via lookup su IssueService
- Mantenere la stessa struttura di risposta (`QueuedIssueItem`)

#### 7. `backend/app/routers/queue.py` — GET /api/queue/status
- RIMUOVERE: `issue_service.list_by_project(status=IssueStatus.QUEUED)` per il conteggio
- SOSTITUIRE CON: `select count(*) from queue_entries where status = 'pending'`

#### 8. `backend/app/models/issue.py` — IssueStatus.QUEUED
- MANTENERE come valore deprecato (non usato per logica nuova)
- Non rimuovere — ci sono dati esistenti con status QUEUED, e la rimozione causerebbe errori in lettura/migrazione

#### 9. `backend/app/mcp/orchestrator_server.py` — queue_list arricchito
- queue_list già usa QueueRegistry, ma l'output non include issue_name e description
- AGGIUNGERE: per ogni entry pending, fare lookup di Issue per ottenere name e description
- Questo comporta un join implicito (due query) — accettabile per tool MCP a bassa frequenza

### Cosa NON cambia
- UI frontend (nessuna modifica a componenti React)
- Worker MCP tools (stessi nomi, stessi parametri, stessi return)
- Flusso FIFO (QueueEntry.order garantisce l'ordine)
- `run_issue()` rimane invariato
- Migration DB (nessuna nuova tabella — QueueEntry esiste già)

### Schema eventi (prima vs dopo)

PRIMA:
```
queue_add() → Issue.status=QUEUED → emit issue_status_changed(Queued)
  → IssueQueueService.notify() → register() + _maybe_auto_start_first()
  → _dequeue_and_run() → Issue.status=REASONING → emit(Reasoning) → run_issue()
```

DOPO:
```
queue_add() → register() diretto → _maybe_auto_start_first() → emit issue_status_changed(Queued) [sintetico]
  → IssueQueueService.notify() → (solo auto-start se necessario)
  → _dequeue_and_run() → Issue.status=REASONING → emit(Reasoning) → run_issue()
```

### Rischi e mitigazioni
- **Race condition:** Se due chiamate queue_add() arrivano in parallelo, entrambe chiamano register(). QueueEntry ha UNIQUE constraint su (issue_id, status=active)? No, non c'è unique constraint attualmente — va aggiunto un controllo in register() per evitare duplicati.
- **Backward compat:** Issues esistenti con status QUEUED in DB continuano a funzionare (il valore enum rimane). startup_resume() usa QueueEntry, non IssueStatus.
