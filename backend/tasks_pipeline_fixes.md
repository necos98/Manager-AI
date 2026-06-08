# Pipeline Bug Fixes — Piano d'Intervento

## Fix #4 — 🔴 CRITICO: fire_pipeline_event DOPO commit (eventi persi)

**Problema:** In `_finalize_run` e `advance_step`, `fire_pipeline_event` viene chiamata DOPO `safe_commit`. Se l'event engine fallisce (eccezione), il pipeline state è già stato committato → issue resta in stato sbagliato senza che nessuno se ne accorga.

**Soluzione:** Spostare `fire_pipeline_event` PRIMA di `safe_commit` in entrambi i punti, e rimuovere la `safe_commit` interna dall'action handler `set_issue_status` (lascia che il chiamante gestisca il commit).

**File da modificare:**
- [ ] `_execution.py:_finalize_run` — sposta `fire` prima di `safe_commit`
- [ ] `_lifecycle.py:advance_step` — sposta `fire` prima di `safe_commit`
- [ ] `_events_engine.py:_action_set_issue_status` — rimuovi `safe_commit()`, lascia flush

---

## Fix #1 — 🟡 MissingGreenlet con selectinload

**Problema:** `_queries.get_run_with_session` usa `selectinload` a 3 livelli. In produzione il problema è MINORE perché ogni MCP call ha una fresh session. MA se una pipeline auto-mode chiama `get_run_with_session` su una sessione già committata (via `_rejection.py:reject_step` chiamato dopo `finished_pipeline_step` via MCP), può capitare.

**Soluzione:** Sostituire `selectinload` con `joinedload` per i 2 livelli interni (`PipelineStep → Agent`), e usare `contains_eager` per il livello base. Su SQLite `joinedload` non fa JOIN multipli problematica perché la pipeline ha pochi step.

**File da modificare:**
- [ ] `_queries.py` — cambia `_STEP_RUNS_LOAD` da `selectinload` a `joinedload`

---

## Fix #2 — 🟡 safe_commit maschera errori

**Problema:** `safe_commit` cattura TUTTE le eccezioni e fa rollback + retry, inclusi IntegrityError e OperationalError. Se un evento engine action fallisce con un errore serio, viene silenziosamente ingoiato.

**Soluzione:** Loggare SEMPRE l'eccezione originale, e non ritentare su IntegrityError.

**File da modificare:**
- [ ] `_safe_session.py` — in safe_commit, logga eccezione originale, non ritentare su IntegrityError

---

## Fix #5 — 🟡 Race condition su issue.status

**Problema:** `set_issue_status` modifica `issue.status` nel DB senza lock. In scenario concorrente (es. pipeline che finisce mentre un MCP setta manualmente lo status), si possono sovrascrivere.

**Soluzione:** Non fix completo (richiederebbe lock distribuito), ma almeno documentare l'issue e aggiungere un `try/except` nell'action handler che logga il conflitto.

**File da modificare:**
- [ ] `_events_engine.py:_action_set_issue_status` — aggiungi try/except con warning log

---

## Fix #3 — 🟢 WebSocket in test

**Problema:** `event_service` è singleton module-level. Se un test lascia WebSocket aperti, test successivi crashano.

**Soluzione:** Mockare `event_service.emit` nei test che non testano WebSocket, usando fixture autouse in conftest.

**File da modificare:**
- [ ] Conftest — mocka `event_service.emit` come no-op nei test
