## Recap: Rimuovere flag `--worktree` dal provider Hermes

Rimosso il flag `--worktree` dai comandi generati da `HermesProvider` in `backend/app/providers/hermes_provider.py`. Il flag creava worktree git orfani quando usato in modalità non-interattiva (`-q` con `--yolo`), perché Hermes non merge né pulisce i worktree al termine della sessione.

### Modifiche effettuate

1. **`build_run_issue_command()`** — rimosso `--worktree` dal comando `hermes chat --skills run-issue --yolo -q "Work on issue <id>"`
2. **`build_run_pipeline_command()`** — rimosso `--worktree` dal comando `hermes chat --skills run-pipeline --yolo -q "Execute pipeline step for issue <id>"`
3. **Docstring della classe** — aggiornata per non menzionare più `--worktree` come flag supportato

### Non modificato

- `build_ask_brainstorm_command()` — già senza `--worktree`, invariato
- `build_manage_agent_command()` — già senza `--worktree`, invariato
- `build_hook_command()` — già senza `--worktree`, invariato
- Nessun test da aggiornare (non esistono test per HermesProvider)

### Consistenza

Questa modifica è coerente con la memoria di progetto esistente che già vieta `--worktree` in `ClaudeCodeExecutor` per lo stesso motivo (worktree orfani con comandi non-interattivi). L'isolamento del worktree è già gestito a livello di sessione invece che di subprocesso.