# Rimozione env vars di identità agente dalla pipeline

## Problema

L'orchestrator della pipeline (`pipeline_run_service.py:_run_step`) inietta 4 env vars nel PTY prima di lanciare il comando dell'agente:

```
set MANAGER_AI_AGENT_NAME={agent_name}
set MANAGER_AI_AGENT_ROLE={agent_name}
set MANAGER_AI_AGENT_INTENT={intent}
set MANAGER_AI_ISSUE_ID={issue_id}
```

Contemporaneamente, `/run-pipeline.md` step 1 dice all'agente di chiamare `get_active_agent(issue_id)` per scoprire chi è. Il tool MCP restituisce `agent_name`, `agent_intent`, `run_id`, `step_index`, `terminal_id` dal DB.

**Due fonti di verità per la stessa informazione.** L'agente:
- Non capisce che `get_active_agent` restituisce la SUA identità (lo interpreta come query esterna)
- Va in loop ("re-call get_active_agent and also hit the REST API")
- Non sa quale fonte sia autorevole

## Soluzione

**Rimuovere TUTTE le env vars di identità agente.** Il comando lanciato dall'orchestrator diventa semplicemente:

```
claude --dangerously-skip-permissions "/run-pipeline {issue_id}"
```

Senza alcun `set MANAGER_AI_AGENT_*`. L'agente deve chiamare `get_active_agent(issue_id)` come primo passo, e quello è l'UNICO canale di identità.

### Cosa cambiare

1. **`pipeline_run_service.py:_run_step`** — rimuovere le 4 righe `pty.write(f"set MANAGER_AI_AGENT_...")` (Windows) e le 4 corrispondenti `pty.write(f"export MANAGER_AI_AGENT_...")` (Linux/WSL). Il comando diventa solo `claude ... "/run-pipeline {issue_id}"` + `exit`.

2. **`/run-pipeline.md`** — riscrivere step 1 in prima persona, chiaro che l'agente È l'agente attivo:
   - "You ARE the active agent in this pipeline."
   - "Call `get_active_agent` with the issue ID to get your identity."
   - "The returned `agent_intent` is YOUR primary instruction. Follow it."

3. **`default_settings.json`** — aggiornare descrizione di `get_active_agent` per enfatizzare self-discovery:
   - "Returns YOUR identity as the active pipeline agent. You ARE this agent."

4. **`default_settings.json`** — rimuovere riferimenti a `terminal_command` da `create_agent`, `list_agents`, `create_pipeline`, `list_pipelines` (colonna droppata con migration `ff1bd3e20a07`).

### Cosa NON cambiare

- `get_active_agent(issue_id)` tool MCP — già corretto, ritorna tutto ciò che serve
- `MANAGER_AI_ISSUE_ID` — l'issue_id è già passato come argomento a `/run-pipeline {issue_id}`. Se qualche altro tool lo usa come fallback, verificare prima di rimuovere.

### Impatto

- **Breaking change minimo**: nessuna API esposta cambia, solo comportamento interno orchestrator
- **Agente più determinato**: identità univoca, niente confusione
- **Più facile da testare**: meno variabili d'ambiente da mockare