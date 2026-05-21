# Pipeline Full-Lifecycle + Start Pipeline Button

## Overview

Estende il sistema agent orchestrator per coprire l'intero ciclo di vita di una issue. Oggi la pipeline copre solo la fase post-acceptance (Architect → Developer → Reviewer → QA). La fase di planning (spec + plan) è gestita fuori pipeline. Obiettivo: creare un unico flusso orchestrato che porta una issue da NEW a FINISHED con 5 agenti specializzati.

Inoltre, aggiunge un pulsante "Start Pipeline" nella UI per avviare manualmente la pipeline su qualsiasi issue, indipendentemente dallo stato.

## Problemi attuali

1. **Planning fuori pipeline**: spec e plan vengono scritti da Claude Code chiamato via `/run-issue`, non dagli agenti orchestrati
2. **Pipeline parte solo da ACCEPTED**: `start_pipeline` vincolato a `accept_issue`, nessun modo per avviare pipeline su issue NEW o REASONING
3. **Nessun pulsante manuale**: UI non espone "Start Pipeline", solo "Run Issue" (single-agent)
4. **Agente SpecWriter mancante**: i 4 agenti default coprono solo post-planning

## Soluzione

### Nuovo agente: SpecWriter

Quinto agente default con role_key `spec_writer`:

- **Nome**: SpecWriter
- **Role**: Analizza requisiti, scrive specifica tecnica e piano implementativo
- **Strumenti MCP da usare**: `create_issue_spec`, `edit_issue_spec`, `create_issue_plan`, `create_plan_tasks`, `send_agent_message`, `get_agent_messages`, `complete_agent_step`
- **System prompt**: istruzioni per analizzare la descrizione issue, produrre spec dettagliata, poi piano con task atomici

### Pipeline default aggiornata

Da 4 a 5 step:

```
SpecWriter → Architect → Developer → Reviewer → QA
```

Ogni agente chiama `complete_agent_step` quando finisce. L'Orchestrator gestisce le transizioni di stato issue:

| Step | Agente | Azione issue |
|------|--------|-------------|
| 0 | SpecWriter | `create_issue_spec` (NEW→REASONING), `create_issue_plan` (REASONING→PLANNED), `create_plan_tasks` |
| 1 | Architect | Analisi architetturale, `send_agent_message` per comunicare decisioni |
| 2 | Developer | Implementazione codice, aggiorna task via `update_task_status` |
| 3 | Reviewer | Code review, `send_agent_message` con findings |
| 4 | QA | Verifica finale, `complete_issue` con recap (PLANNED→FINISHED) |

### Avvio pipeline da qualsiasi stato

Modificare `start_pipeline` per accettare issue in qualsiasi stato (non solo ACCEPTED):

- **NEW**: pipeline parte da SpecWriter
- **REASONING**: pipeline parte da Architect (spec già scritta)
- **PLANNED**: pipeline parte da Developer (spec + plan già pronti, come oggi)
- **ACCEPTED**: pipeline parte da Developer (retrocompatibile)

Logica: prima di creare `AgentStepRun`, controllare stato issue e skippare gli step i cui output già esistono.

### Pulsante "Start Pipeline" in UI

Nella `IssueActions` component, aggiungere pulsante accanto a "Run Issue":

```
[Accept Plan] [Run Issue] [Start Pipeline] [Cancel Issue]
```

- Visibile per issue in stato NEW, REASONING, PLANNED, ACCEPTED
- Chiama MCP tool `start_pipeline` con `issue_id`
- Disabled se pipeline già in esecuzione (running)
- Icona: `GitBranch` o `Workflow` da lucide-react

### Modifiche backend

1. **OrchestratorService**:
   - `DEFAULT_AGENTS`: aggiungere SpecWriter
   - `DEFAULT_PIPELINE_STEPS`: aggiornare ordine con spec_writer
   - `start_pipeline()`: rimuovere vincolo stato issue, aggiungere logica skip step
   - `_build_prompt()`: includere contesto su stato corrente e step da skippare

2. **MCP server.py**:
   - `start_pipeline` tool: rimuovere check `issue.status == ACCEPTED`

3. **Routers**:
   - `ensure_default_agents`: aggiungere SpecWriter ai default
   - `ensure_default_pipeline`: aggiornare steps con 5 agenti

### Modifiche frontend

1. **IssueActions**: aggiungere pulsante "Start Pipeline"
2. **useStartPipeline** hook (se non esiste): chiamata API per avviare pipeline
3. **PipelineProgress**: mostrare stato anche per pipeline in corso su issue non-ACCEPTED

### Gestione stati e transizioni

```
NEW ──[Start Pipeline]──→ SpecWriter scrive spec ──→ REASONING
REASONING ──[Start Pipeline]──→ SpecWriter scrive plan ──→ PLANNED
PLANNED ──[Start Pipeline]──→ Architect → Developer → Reviewer → QA ──→ FINISHED
```

Se pipeline già partita per una issue, "Start Pipeline" è disabled (evita esecuzioni duplicate).

## Testing

- `test_spec_writer_agent_created`: verificare che ensure_default_agents crei 5 agenti
- `test_default_pipeline_5_steps`: verificare 5 step in ordine corretto
- `test_start_pipeline_from_new`: avviare pipeline su issue NEW, verificare step creati
- `test_start_pipeline_from_reasoning`: skippa SpecWriter se spec esiste
- `test_start_pipeline_from_planned`: skippa SpecWriter+Architect, parte da Developer
- `test_start_pipeline_duplicate_prevented`: seconda chiamata bloccata se pipeline già running
- `test_pipeline_full_flow_new_to_finished`: spec writer → architect → dev → review → qa → FINISHED
- Frontend: verificare pulsante visibile e funzionante