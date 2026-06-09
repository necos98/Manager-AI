## Piano: Rimuovere flag `--worktree` dal provider Hermes

### Analisi

La modifica è semplice e mirata: rimuovere `--worktree` da due righe in `backend/app/providers/hermes_provider.py`.

### Task

1. **Rimuovere `--worktree` da `build_run_issue_command()`** — linea 26, rimuovere `--worktree` dal comando
2. **Rimuovere `--worktree` da `build_run_pipeline_command()`** — linea 32, rimuovere `--worktree` dal comando
3. **Verificare i test** — controllare se esistono test per HermesProvider e aggiornarli
4. **Aggiornare docstring** — rimuovere il riferimento a `--worktree` nella docstring della classe

### Verifica

- `build_run_issue_command()` → output senza `--worktree`
- `build_run_pipeline_command()` → output senza `--worktree`
- `build_ask_brainstorm_command()` e `build_manage_agent_command()` → invariati
- Test superati