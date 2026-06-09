## Specifica: Rimuovere flag `--worktree` dal provider Hermes

### Problema

Il provider Hermes (`backend/app/providers/hermes_provider.py`) lancia i comandi Hermes con il flag `--worktree` in due metodi:

- `build_run_issue_command()` — `hermes chat --skills run-issue --worktree --yolo ...`
- `build_run_pipeline_command()` — `hermes chat --skills run-pipeline --worktree --yolo ...`

Il flag `--worktree` fa sì che Hermes crei un git worktree isolato per la sessione. Tuttavia, quando Hermes termina (soprattutto in modalità non-interattiva con `-q`/`--yolo`), il worktree non viene mai mergiato o pulito. Le modifiche rimangono perse nel worktree e i worktree si accumulano indefinitamente.

Questa è la stessa problematica già documentata per `ClaudeCodeExecutor` nella memoria di progetto: il flag `--worktree` in combinazione con comandi non-interattivi crea worktree orfani perché non c'è un prompt di uscita che scateni il dialogo keep/remove.

### Soluzione

Rimuovere `--worktree` dai comandi di `build_run_issue_command()` e `build_run_pipeline_command()` in `HermesProvider`.

I comandi diventano:

- `hermes chat --skills run-issue --yolo -q "Work on issue <id>"`
- `hermes chat --skills run-pipeline --yolo -q "Execute pipeline step for issue <id>"`

### Impatto

- **Nessun impatto su altri provider** — la modifica è limitata a `HermesProvider`.
- **Nessun impatto su altri metodi** — `build_ask_brainstorm_command()`, `build_manage_agent_command()`, `build_hook_command()` già non usano `--worktree`.
- **Isolamento mantenuto** — l'isolamento del worktree è già gestito a livello di sessione (l'utente lancia `claude --worktree` e tutti i subprocessi ereditano il worktree padre), come documentato nella memoria esistente.
- **Nessuna modifica ai test** — se esistono test per HermesProvider, vanno aggiornati per riflettere i nuovi comandi senza `--worktree`.

### Criteri di accettazione

1. `build_run_issue_command()` restituisce un comando senza `--worktree`
2. `build_run_pipeline_command()` restituisce un comando senza `--worktree`
3. Tutti gli altri metodi rimangono invariati
4. I test (se presenti) passano con i comandi aggiornati