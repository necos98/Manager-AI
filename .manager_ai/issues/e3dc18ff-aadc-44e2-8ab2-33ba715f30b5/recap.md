## Modifiche

1. **`backend/app/services/pipeline_run_service.py:_run_step`** — rimosse 8 righe di iniezione env vars (MANAGER_AI_AGENT_NAME, MANAGER_AI_AGENT_ROLE, MANAGER_AI_AGENT_INTENT, MANAGER_AI_ISSUE_ID) sia per Windows (`set`) che Linux/WSL (`export`). Il metodo ora scrive solo `claude --dangerously-skip-permissions "/run-pipeline {issue_id}"` + `exit`.

2. **`claude_resources/commands/run-pipeline.md`** — step 1 riscritto in prima persona. L'agente viene informato che È l'agente attivo e che `get_active_agent` restituisce la SUA identità. Enfatizzato che non ci sono altre fonti (no env vars).

3. **`backend/app/mcp/default_settings.json`** — descrizione `get_active_agent` riscritta in seconda persona ("Returns YOUR identity", "You ARE this agent"). Rimosso `terminal_command` da descrizioni `create_agent`, `list_agents`, `create_pipeline`, `list_pipelines`.

4. **Memorie aggiornate**: `fc31b9e8` (marcata REMOVED), `ee88c5a3` (rimosso canale env var), `eb307327` (retitolo "sole source" invece di "bridges").

## Decisioni

- **MANAGER_AI_ISSUE_ID rimosso insieme agli altri**: l'issue_id è già passato come `$ARGUMENTS` a `/run-pipeline`. Le hook scripts (notify-hook.py, tts-hook.py) leggono MANAGER_AI_ISSUE_ID ma girano nel contesto sessione, non nel PTY pipeline.
- **Nessun breaking change**: il comportamento API non cambia, solo l'ambiente del subprocess pipeline.
- **Test passano**: 8/8 test pipeline_run_service OK.