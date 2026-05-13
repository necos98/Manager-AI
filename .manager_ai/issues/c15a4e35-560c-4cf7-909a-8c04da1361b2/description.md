Quando l'utente naviga a un progetto, le issue vengono caricate una alla volta (`load_issue` chiamato per ogni issue da `list_issues_full`). Non c'è un meccanismo di pre-caricamento batch.

**Proposta:** Aggiungere `prewarm_project_cache(project_path)` che:
1. Legge `issues.yaml` index
2. Per ogni issue nell'index, legge `issue.yaml` in un colpo (batch glob + read) o parallelamente
3. Popola la cache per tutte le issue del progetto in una volta sola

Questo ridurrebbe la latenza percepita al primo accesso perché tutte le letture disco avvengono in un unico batch invece che in letture sparse durante la navigazione.

**File:** `backend/app/storage/issue_store.py` — nuova funzione `prewarm_cache(project_path)`