La dashboard (`GET /api/dashboard`) chiama `issue_store.list_issues_full()` che carica TUTTI i markdown body (description, specification, plan, recap) per ogni issue attiva. La dashboard mostra solo nome, status, priorità — dati già presenti nell'index `issues.yaml`. `list_issues()` restituisce già tutto il necessario senza toccare i file markdown.

**Impatto:** Per N issue attive, 4N file read inutili. Su 50 issue sono 200 letture disco sprecate.

**File:** `backend/app/services/project_service.py:75-77` — `issue_store.list_issues_full(project.path)`

**Fix:** Sostituire con `list_issues()` che legge solo l'index. Per la dashboard non servono i campi description/spec/plan/recap.