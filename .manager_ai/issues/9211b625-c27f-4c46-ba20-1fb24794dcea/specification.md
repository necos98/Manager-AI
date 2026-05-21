# Pipeline Visual Feedback

## Problem

Pipeline esegue ma utente non vede nulla. Click "Start Pipeline" → nessun feedback visivo. Sei bug si combinano per rendere l'esecuzione invisibile.

## Root Causes

1. **Eventi WebSocket `_emit()` senza `project_id`** — `orchestrator_service.py:437-460`. Payload ha `issue_id` ma non `project_id`. Frontend `EventProvider` (line 299) controlla `if (projectId && issueId)` prima di invalidare React Query → condizione falsa → nessun refresh dopo la mutation iniziale.

2. **`usePipelineRunsForIssue` senza polling** — `hooks.ts:120-126`. Niente `refetchInterval`. Anche con WebSocket fix, componente rimane stale senza cambio tab.

3. **PipelineProgress mostra solo summary, non step stepper** — `pipeline-progress.tsx:43-44` ha TODO esplicito. Mostra solo pallino colorato + status text.

4. **AgentChat ignora eventi step lifecycle** — `agent-chat.tsx:58`. Ascolta solo `agent_message_added`. Ignora `agent_step_started/completed/failed`.

5. **Nessun indicatore inline fuori dal tab Pipeline** — issue detail page. Stato pipeline visibile solo cliccando manualmente il tab.

6. **`send_agent_message` hardcoded identity** — `server.py:1096-1109`. `agent_name="agent"`, `agent_role="unknown"`. Anche `project_id` mancante nell'evento emesso.

## Solution

### Backend

**A. `_emit()` con `project_id`**
- Aggiungere parametro `project_id: str` a `_emit()`
- `_run_pipeline()`: caricare pipeline da `pipeline_run.pipeline_id` all'inizio, cachare `project_id`, passare a tutte le `_emit()`
- `_run_agent_step()`: già risolve `project` a line 300, passare `agent.project_id`
- 5 call site aggiornati: `agent_step_started`, `agent_step_completed`, `agent_step_failed`, `pipeline_completed`, `pipeline_paused`

**B. Identità agent in `send_agent_message`**
- `_run_agent_step()`: aggiungere `MANAGER_AI_AGENT_NAME` e `MANAGER_AI_AGENT_ROLE` agli env vars passati a `executor.run()`
- `server.py` `send_agent_message`: leggere `os.environ.get("MANAGER_AI_AGENT_NAME", "agent")` e `MANAGER_AI_AGENT_ROLE`
- Aggiungere `project_id` al payload evento (da `MANAGER_AI_PROJECT_ID` già settato)

### Frontend

**C. Polling su `usePipelineRunsForIssue`**
- `hooks.ts`: aggiungere `refetchInterval: 3000` quando l'ultimo run ha status "running"
- Usare anche `usePipelineRun(latestRun.id)` per avere dati step-level nel componente PipelineProgress

**D. Step stepper in PipelineProgress**
- Quando `latestRun` esiste, fetch full run con `usePipelineRun(latestRun.id)` (già ha `refetchInterval: 3000`)
- Renderizzare lista step con: nome agent, ruolo, dot colorato, icona status (pending/running/completed/failed), summary su hover
- Timeline verticale con linee colorate tra gli step
- Mantenere summary card per run precedenti

**E. AgentChat mostra eventi step lifecycle**
- Sottoscrivere a `agent_step_started`, `agent_step_completed`, `agent_step_failed`
- Renderizzare come messaggi di sistema: "SpecWriter started", "Architect completed — summary"
- Stile muted/italic per distinguerli dai messaggi agent

**F. Status badge inline su header issue**
- Sopra i tab, mostrare barra compatta stato pipeline quando run attivo o ultimo completato
- Testo: "Pipeline: Running (Step 2/5 — Architect)" o "Pipeline: Completed"
- Cliccabile → switcha a tab Pipeline
- Scompare se nessun run

**G. EventProvider: silent events per pipeline**
- Aggiungere `agent_step_started/completed/failed`, `pipeline_completed/paused` a `buildToastContent` come `silent: true`
- Con `project_id` negli eventi, il blocco `if (projectId && issueId)` a line 299 farà React Query invalidation automaticamente

## Data Flow (dopo fix)

```
Orchestrator._run_agent_step()
  → step.status = RUNNING
  → _emit("agent_step_started", pipeline_run, step, project_id=...)
    → event_service.emit({type, project_id, issue_id, step_id, agent_name, agent_role, ...})
      → WebSocket broadcast a tutti i client
        → EventProvider.onmessage
          → projectId && issueId → queryClient.invalidateQueries(["projects", projectId, "issues", issueId])
            → PipelineProgress refetch (usePipelineRunsForIssue + refetchInterval ogni 3s)
            → PipelineProgress refetch step data (usePipelineRun)
          → subscribers (AgentChat) → render system message "SpecWriter started"

Claude Code subprocess (SpecWriter)
  → send_agent_message(issue_id, content)
    → legge MANAGER_AI_AGENT_NAME, MANAGER_AI_AGENT_ROLE da env
    → AgentMessage salvato con nome/ruolo corretti
    → event_service.emit({type: "agent_message_added", project_id, issue_id, message})
      → WebSocket → AgentChat subscriber → render messaggio con nome/ruolo/colore corretti

Orchestrator (dopo complete_agent_step)
  → step.status = COMPLETED
  → _emit("agent_step_completed", pipeline_run, step, project_id=...)
    → stessi meccanismi di refresh
```

## File da Modificare

| File | Modifica |
|------|----------|
| `backend/app/services/orchestrator_service.py` | `_emit()` + project_id param, env vars agent identity, 5 call site |
| `backend/app/mcp/server.py` | `send_agent_message` legge env per identity, aggiunge project_id |
| `frontend/src/features/agents/hooks.ts` | `refetchInterval` su `usePipelineRunsForIssue` |
| `frontend/src/features/agents/components/pipeline-progress.tsx` | Step stepper con `usePipelineRun` |
| `frontend/src/features/agents/components/agent-chat.tsx` | Eventi step lifecycle |
| `frontend/src/features/issues/components/issue-detail.tsx` | Status badge inline |
| `frontend/src/shared/context/event-context.tsx` | Silent events per pipeline |

## Verification

1. Avviare backend + frontend
2. Aprire issue, tab Pipeline → "No pipeline runs yet"
3. Click "Start Pipeline" → tab Pipeline mostra step stepper con 5 step, primo step "running"
4. Agent Chat mostra "SpecWriter started" come system message
5. Step avanzano pending → running → completed in tempo reale
6. Header issue mostra barra: "Pipeline: Running (Step 1/5 — SpecWriter)"
7. Pipeline completa → stepper tutto verde, header "Pipeline: Completed"
8. Agent Chat mostra messaggi con nome e ruolo corretti (non "agent (unknown)")
