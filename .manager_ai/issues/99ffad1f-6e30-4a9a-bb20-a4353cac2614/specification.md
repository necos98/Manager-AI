## Specifica: Aggiungere flag --max-turns ai comandi Hermes provider

### Contesto
Hermes Agent ha un limite di default di 60 iterazioni (tool-calling turns) nel comando `chat`. Quando l'agente esegue task complesse (run-issue o run-pipeline), raggiunge questo limite e si ferma bruscamente senza completare il lavoro.

Il flag `--worktree` è già stato rimosso dal provider Hermes nell'issue f7f6747a-2f7c-4ef6-98f3-87c3c7372a55 (Finished). Il file attuale è già senza `--worktree`.

### Modifiche richieste

File: `backend/app/providers/hermes_provider.py`

1. **`build_run_issue_command`** (riga 24-28): Aggiungere `--max-turns 300`
   - Prima: `hermes chat --skills run-issue --yolo -q "Work on issue ..."`
   - Dopo: `hermes chat --skills run-issue --max-turns 300 --yolo -q "Work on issue ..."`

2. **`build_run_pipeline_command`** (riga 30-34): Aggiungere `--max-turns 300`
   - Prima: `hermes chat --skills run-pipeline --yolo -q "Execute pipeline step for issue ..."`
   - Dopo: `hermes chat --skills run-pipeline --max-turns 300 --yolo -q "Execute pipeline step for issue ..."`

### Non modificate
- `build_ask_brainstorm_command` — comandi brevi, non servono max-turns
- `build_manage_agent_command` — comandi brevi, non servono max-turns
- `build_hook_command` — one-shot (-q --quiet), non servono max-turns

### Valore scelto
`300` è un buon trade-off tra capacità di completare task complesse e protezione da loop infiniti.
