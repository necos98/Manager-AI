Aggiungere il flag `--max-turns` ai comandi Hermes in `backend/app/providers/hermes_provider.py`.

**Problema:** Hermes ha un limite di 60 iterazioni (tool-calling turns) per default nel comando `chat`. Quando l'agente ha molte task da fare, si ferma improvvisamente dicendo di aver raggiunto il numero massimo di iterazioni.

**Soluzione:** Aggiungere `--max-turns 300` (o valore adeguato) ai comandi di run-issue e run-pipeline in HermesProvider.

**File:** `backend/app/providers/hermes_provider.py`
- Riga 29: `hermes chat --skills run-issue --worktree --yolo` → `hermes chat --skills run-issue --max-turns 300 --yolo`
- Riga 35: `hermes chat --skills run-pipeline --worktree --yolo` → `hermes chat --skills run-pipeline --max-turns 300 --yolo`

Nota: anche il flag `--worktree` è già stato segnalato come problematico in un'altra issue (da rimuovere). Se non è stato ancora fixato, approfittare per rimuoverlo contestualmente.