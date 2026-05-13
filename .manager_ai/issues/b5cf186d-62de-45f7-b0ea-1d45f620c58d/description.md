Ogni metodo di `IssueService` chiama `_resolve_path(project_id)` che esegue `session.get(Project, project_id)` — una query SQL. In una singola request HTTP, più metodi possono chiamare `_resolve_path` con lo stesso `project_id` (es. `get_for_project` → `update_status` → `update_fields`).

**Impatto:** Query SQL duplicate nella stessa request. Basso overhead per SQLite in-process, ma è comunque lavoro sprecato.

**Fix:** Aggiungere un semplice dizionario nel request scope (o usare `contextvars`) per cachare `project_id → path` per la durata della request.

**File:** `backend/app/services/issue_service.py:47-49`