## Piano di Implementazione

Il codice è già stato modificato nel working tree. Questo piano copre verifica, test e commit.

### Task 1: Verifica sintassi e import
- `python -c "import ast; ast.parse(open('backend/app/routers/issues.py').read())"` — già verificato OK
- Verificare che i nuovi import (ProjectService, event_service) non causino circular import

### Task 2: Verifica backend in esecuzione
- Se il backend è attivo, riavviarlo o testare con un curl
- Controllare che gli endpoint `/complete` e `/force-finish` non diano errore

### Task 3: Verifica altri file modificati
- `shared_tools.py` — verificare sintassi e che gli MCP tool funzionino
- `hermes_provider.py` — verifica sintassi
- `notification_service.py` — verifica sintassi

### Task 4: Commit del fix
- git add dei file pertinenti e commit con messaggio descrittivo