Il tool MCP `run_pipeline_step` ha un nome fuorviante: non "runna" nulla, fetcha solo il contesto dello step corrente. Lo step è già in stato RUNNING prima che l'agente parta (impostato dall'orchestrator in `_execute()`).

Il nome fa pensare a un'operazione di side-effect (avviare/eseguire uno step), ma in realtà è una lettura pura: restituisce `{run_id, step_run_id, agent_name, agent_intent, step_index, terminal_id}`.

Possibili nomi più accurati:
- `claim_pipeline_step` — l'agente "rivendica" lo step
- `get_step_context` — descrive esattamente ciò che fa
- `get_current_step` — variante più breve

Impatto: rinominare il tool richiede aggiornare:
- server.py (definizione tool)
- default_settings.json (descrizione)
- run-pipeline.md (step 5)
- run-pipeline.md in claude_resources/ (sync)