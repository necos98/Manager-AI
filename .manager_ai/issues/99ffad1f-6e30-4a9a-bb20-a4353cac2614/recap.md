## Recap: Aggiungere flag --max-turns ai comandi Hermes provider

### Modifiche effettuate
File modificato: `backend/app/providers/hermes_provider.py`

1. **`build_run_issue_command`** (riga 29): aggiunto `--max-turns 300`
   - `"hermes chat --skills run-issue --yolo"` → `"hermes chat --skills run-issue --max-turns 300 --yolo"`

2. **`build_run_pipeline_command`** (riga 35): aggiunto `--max-turns 300`
   - `"hermes chat --skills run-pipeline --yolo"` → `"hermes chat --skills run-pipeline --max-turns 300 --yolo"`

### Non modificate
- `build_ask_brainstorm_commands` — comandi brevi, nessun bisogno di max-turns
- `build_manage_agent_commands` — comandi brevi, nessun bisogno di max-turns
- `build_hook_command` — one-shot (-q --quiet), nessun bisogno di max-turns
- `build_notification_command` — one-shot (-q --quiet), nessun bisogno di max-turns

### Verifica
- Lint passato ✅
- File letto e confermato: tutte e due le righe contengono `--max-turns 300` ✅
- Nessun altro metodo modificato ✅