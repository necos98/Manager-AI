# Agent Orchestration & Multi-Agent Chat System

## Overview

Trasforma Manager AI da sistema single-agent (unico Claude Code che esegue `/run-issue`) a sistema multi-agente orchestrato. Introduce agenti specializzati (Architect, Developer, Reviewer, QA) che lavorano in pipeline su ogni issue, con chat strutturata per comunicazione inter-agente.

Architettura a due livelli:
1. **Issue Orchestrator** (questo issue) — pipeline di agenti per issue
2. **Project Orchestrator** (futuro) — daemon che monitora, crea issue, spawna agenti project-level

## Core Architecture

### OrchestratorService

Servizio generico (non legato a sole issue). Gestisce esecuzione di pipeline di agenti indipendentemente dal trigger. Responsabilità:

- `start_pipeline(trigger_type, issue_id=None)` — avvia esecuzione pipeline
- `build_agent_prompt(agent, context, chat_history)` — costruisce prompt per Claude Code
- `run_agent_step(pipeline_run, agent)` — chiama ClaudeCodeExecutor
- `handle_step_completion(pipeline_run, result)` — transizione al prossimo agente
- `complete_pipeline(pipeline_run)` — finalizza

### Trigger Types (supportati da subito)

| Trigger | Descrizione |
|---------|-------------|
| `issue_accepted` | Issue viene accettata, avvia pipeline default |
| `manual` | Utente avvia pipeline manualmente da UI |
| `cron` | (futuro) schedulato |
| `project_event` | (futuro) trigger da Project Orchestrator |

## Data Models

### Agent (nuova tabella)

Definizione di ruolo agente per progetto.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Primary key |
| project_id | FK → projects | Progetto di appartenenza |
| name | String(255) | Nome ruolo: Architect, Developer, Reviewer, QA |
| role_key | String(100) | Chiave unica per ruolo: architect, developer, reviewer, qa |
| system_prompt | Text | Istruzioni complete per Claude Code (ruolo, responsabilità, output atteso) |
| enabled | Bool | Default true, disabilitabile per progetto |
| created_at | DateTime | |
| updated_at | DateTime | |

**Agenti default per ogni progetto:**
- Architect: scrive specifiche tecniche, piani implementativi
- Developer: implementa codice, esegue test
- Reviewer: code review, verifica qualità
- QA: test funzionali, verifica acceptance criteria

### Pipeline (nuova tabella)

Workflow definito come sequenza ordinata di agenti.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Primary key |
| project_id | FK → projects | |
| name | String(255) | Nome workflow |
| steps | JSON | Lista `[{agent_id, order}]` — ordine agenti |
| is_default | Bool | Pipeline di default per project |
| trigger_type | String | `issue_accepted` o `manual` o `cron` o `project_event` |
| created_at | DateTime | |
| updated_at | DateTime | |

### PipelineRun (nuova tabella)

Esecuzione concreta di una pipeline.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Primary key |
| pipeline_id | FK → pipelines | |
| issue_id | FK → issues, nullable | Issue associata (null per project-level) |
| trigger_type | String | Tipo di trigger |
| status | Enum | running, completed, failed, paused |
| started_at | DateTime | |
| completed_at | DateTime | |

### AgentStepRun (nuova tabella)

Singolo step di esecuzione agente all'interno di una PipelineRun.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Primary key |
| pipeline_run_id | FK → pipeline_runs | |
| agent_id | FK → agents | |
| agent_name | String | Denormalizzato per facilità query |
| status | Enum | pending, running, completed, failed |
| summary | Text, nullable | Riepilogo prodotto dall'agente |
| error | Text, nullable | Errore se failed |
| started_at | DateTime | |
| completed_at | DateTime | |

### AgentMessage (nuova tabella)

Messaggio nella chat inter-agente.

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| id | UUID | Primary key |
| issue_id | FK → issues | Issue (null per chat project-level futura) |
| agent_name | String | Nome agente che ha scritto |
| agent_role | String | Ruolo agente |
| content | Text | Contenuto messaggio |
| message_type | String | context, decision, question, answer, status |
| created_at | DateTime | |

## MCP Tools

### Agenti
- `list_agents(project_id)` → lista agenti con stato enabled
- `create_agent(project_id, name, role_key, system_prompt)` → crea nuovo
- `update_agent(agent_id, ...)` → modifica
- `delete_agent(agent_id)` → elimina

### Pipeline
- `list_pipelines(project_id)` → lista pipeline
- `create_pipeline(project_id, name, steps, is_default, trigger_type)` → crea
- `update_pipeline(pipeline_id, ...)` → modifica
- `delete_pipeline(pipeline_id)` → elimina

### Esecuzione
- `start_pipeline(issue_id)` → avvia manualmente pipeline per issue
- `complete_agent_step(pipeline_run_id, summary)` → agente segnala completamento
- `get_pipeline_status(pipeline_run_id)` → stato corrente pipeline

### Chat
- `send_agent_message(issue_id, content, message_type)` → scrive messaggio
- `get_agent_messages(issue_id)` → legge tutti i messaggi

### Modifiche a tool esistenti
- `accept_issue` → dopo accettazione, auto-triggera pipeline default con trigger_type=issue_accepted

## Agent Lifecycle

```
1. Pipeline triggered (issue_accepted o manual)
2. Orchestrator crea PipelineRun + AgentStepRun per ogni step (status=pending)
3. Per ogni step in ordine:
   a. step status → running
   b. Build prompt: agent.system_prompt + issue context (spec/plan/tasks) + chat history
   c. ClaudeCodeExecutor.run(prompt, project_path, env_vars)
   d. Agente (Claude Code) lavora, usa MCP tools per:
      - Leggere/scrivere chat (send_agent_message, get_agent_messages)
      - Aggiornare task (update_task_status)
      - Completare step (complete_agent_step)
   e. step status → completed (o failed)
   f. Se failed e retry disponibile → riprova step
   g. Altrimenti → pipeline in pausa, notifica utente
4. Tutti step completati → pipeline status = completed
5. Emette evento pipeline_completed
```

## Event Types (WebSocket)

- `agent_step_started` — `{issue_id, pipeline_run_id, step_index, agent_name, agent_role}`
- `agent_step_completed` — `{issue_id, pipeline_run_id, step_index, agent_name, summary}`
- `agent_step_failed` — `{issue_id, pipeline_run_id, step_index, agent_name, error}`
- `agent_message_added` — `{issue_id, message: AgentMessage}`
- `pipeline_completed` — `{issue_id, pipeline_run_id, total_steps, duration}`

## Frontend

### Agent Definitions (Project Settings > Agents tab)
- Tabella agenti: nome, ruolo, enabled toggle, pulsante edit
- Editor system_prompt: textarea markdown
- Aggiungi/rimuovi agenti

### Pipeline Editor (Project Settings > Pipelines tab)
- Lista pipeline, una marked default
- Drag-and-drop ordinamento step
- Crea nuova pipeline: nome → aggiungi agenti in ordine → save

### Agent Chat Panel (Issue Detail, sidebar destra)
- Messaggi scrollabili con badge agente colorato
- Colori ruolo: Architect=#7c3aed, Developer=#2563eb, Reviewer=#059669, QA=#ea580c
- WebSocket aggiorna in tempo reale

### Pipeline Progress (Issue Detail, top bar)
- Stepper orizzontale: cerchi per ogni step
- Stati: pending (grigio), running (spinning blu), completed (check verde), failed (X rossa)
- Nome agente corrente sotto step attivo

### Manual Overrides
- Bottone "Start Pipeline" su issue
- Bottone "Retry Step" su step fallito
- Bottone "Skip Step" per step non critici

## Error Handling

- Agent timeout (300s default) → step failed, si puo retryare
- Agent non-zero exit → error loggato in AgentMessage type=status, pipeline paused
- Pipeline paused → notifica utente via WebSocket + notification UI
- Manual retry/restart disponibile da UI

## Future: Project Orchestrator

Stessa infrastruttura (OrchestratorService, Pipeline, PipelineRun, AgentStepRun) riutilizzata per:
- Daemon che monitora progetto a intervalli
- Pipeline con trigger_type = `cron` o `project_event`
- Agent che eseguono code audit, health check, dependency scan
- Puo creare issue automaticamente (create_issue → accept_issue → trigger Issue Orchestrator)
- AgentMessage con issue_id = null per chat project-level

## Migrations Required

Nuove tabelle: agents, pipelines, pipeline_runs, agent_step_runs, agent_messages

## Implementation Order

1. Modelli DB + migration
2. OrchestratorService base
3. MCP tools (agents + pipelines CRUD)
4. MCP tools (chat + esecuzione)
5. Integrazione accept_issue → auto-start pipeline
6. WebSocket events
7. Frontend: Agent Definitions + Pipeline Editor
8. Frontend: Agent Chat Panel + Pipeline Progress
9. Testing E2E
