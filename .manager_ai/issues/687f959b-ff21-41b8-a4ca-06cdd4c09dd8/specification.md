## Problema

`get_dashboard_data()` in `project_service.py` chiama `issue_store.list_issues_full()` che per ogni issue attiva carica tutti i file markdown (description, specification, plan, recap). La dashboard mostra solo nome, status, priorità — dati già presenti nell'index `issues.yaml`.

Per N issue attive: 4N file read inutili. Con 50 issue attive: 200 letture disco sprecate per ogni richiesta dashboard.

## Fix

Sostituire `issue_store.list_issues_full(project.path)` con `issue_store.list_issues(project.path)` a `backend/app/services/project_service.py:77`.

`list_issues()` legge solo `issues.yaml` e restituisce `IssueRecord` con tutti i campi necessari alla dashboard (id, name, status, priority, created_at). I campi description/specification/plan/recap sono vuoti — ma la dashboard non li usa.

Nessun cambio di comportamento. Nessun cambio API. Nessun test da modificare.

## Rischio

Nessuno. `get_issue_counts()` (linea 94) usa già `list_issues()` e funziona correttamente.