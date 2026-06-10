## Queue non riparte automaticamente dopo restart

**Problema:** Quando Manager AI viene chiuso e riaperto, la coda non riprende automaticamente a processare le issue QUEUED. Il sistema è puramente event-driven: `IssueQueueService` si registra come listener all'avvio ma non controlla mai se ci sono già issue in coda in attesa.

**Come si manifesta:** Se ci sono issue QUEUED quando il software viene chiuso, alla ripartenza restano in QUEUED ma nessuna viene avviata. La coda "si sveglia" solo se si aggiunge una nuova issue, che triggera `_on_issue_queued` → `_maybe_auto_start_first`.

**Root cause:** In `backend/app/main.py:306`, la riga `_ = IssueQueueService()` registra solo il listener EventService. Non c'è una scansione startup delle issue QUEUED per avviare la prima.

**Soluzione proposta:**
1. Aggiungere un metodo `async def startup_resume(self)` a `IssueQueueService` che:
   - Scansiona tutti i progetti per issue in stato `QUEUED`
   - Se il QueueEntry ha entry `PENDING` e nessuna issue è in esecuzione (REASONING), fa partire la prima in coda con `_dequeue_and_run`
2. Chiamare `startup_resume()` in `main.py` subito dopo `_ = IssueQueueService()` durante il lifespan startup

**File interessati:**
- `backend/app/services/issue_queue_service.py` — aggiungere metodo `startup_resume`
- `backend/app/main.py` — chiamare startup_resume dopo IssueQueueService()

**Priorità:** Alta — blocca il flusso di lavoro se la coda si ferma