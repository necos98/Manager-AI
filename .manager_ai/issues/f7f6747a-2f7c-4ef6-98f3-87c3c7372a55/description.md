Il provider Hermes in `backend/app/providers/hermes_provider.py` lancia i comandi con il flag `--worktree`:

- `run-issue`: `hermes chat --skills run-issue --worktree --yolo`
- `run-pipeline`: `hermes chat --skills run-pipeline --worktree --yolo`

Questo flag crea un git worktree isolato, ma Hermes non merge mai il lavoro completato nel branch principale. Le modifiche rimangono perse nel worktree. La soluzione è rimuovere `--worktree` dai comandi di run-issue e run-pipeline.