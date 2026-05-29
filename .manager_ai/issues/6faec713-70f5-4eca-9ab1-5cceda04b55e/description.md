`get_active_agent` e `run_pipeline_step` ritornano campi quasi identici: entrambi restituiscono `run_id`, `agent_name`, `agent_intent`, `step_index`, `terminal_id`. L'unica differenza è che `run_pipeline_step` aggiunge `step_run_id`.

run-pipeline.md dice all'agente di leggere `agent_intent` due volte: allo step 1 (da `get_active_agent`) e allo step 5 (da `run_pipeline_step`). Questo crea confusione su quale sia la fonte canonica dell'intent.

Possibili soluzioni:
- Rimuovere `agent_intent` da `get_active_agent` e tenerlo solo in `run_pipeline_step` (single source of truth)
- Fondere i due tool in uno solo: `get_active_agent` ritorna TUTTO incluso `step_run_id`
- Tenere `get_active_agent` leggero (solo identity) e `run_pipeline_step` come unico posto dove si prende l'intent