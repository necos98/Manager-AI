# Agent Pipeline System — Architecture

## Overview

Sistema di pipeline agenti personalizzabile per progetto. Ogni pipeline e una sequenza ordinata di step, dove ogni step esegue un agente Claude Code con un comando terminale specifico. L'output di ogni step viene streammato in tempo reale via log terminal. Gli agenti comunicano tra loro tramite una chat integrata (`PipelineMessage`).

**Principi:**
- Agenti e pipeline sono **per-project** (scope project_id)
- N pipeline per progetto, **1 esecuzione alla volta per issue**
- Esecuzione **sequenziale** (step 1 finito -> step 2 parte)
- Ogni step spawna un **subprocess** (non PTY interattivo)
- Output streammato via **log terminal** (asyncio.Queue)
- Frontend riceve aggiornamenti via **polling (2s)** + terminale WebSocket

---

## Data Model

Tutti i modelli in `backend/app/models/`. Migration: `04d6489a8fd4`.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│    Agent    │────→│ PipelineStep │←────│    Pipeline     │
│             │     │               │     │                 │
│ id          │     │ id           │     │ id              │
│ project_id  │     │ pipeline_id  │     │ project_id      │
│ name        │     │ agent_id     │     │ name            │
│ system_pr.  │     │ order_index  │     │ created_at      │
│ model       │     │ terminal_cmd │     └────────┬────────┘
│ allowed_tls │     └──────┬───────┘              │
└─────────────┘            │                      │
                           │              ┌───────┴────────┐
                           │              │  PipelineRun   │
                           │              │                │
                           │              │ id             │
                           │              │ pipeline_id    │
                           │              │ issue_id       │
                           │              │ status         │
                           │              │ current_step   │
                           │              └───────┬────────┘
                           │                      │
                    ┌──────┴──────┐      ┌────────┴─────────┐
                    │PipelineStepRun│      │ PipelineMessage  │
                    │               │      │                  │
                    │ id            │      │ id               │
                    │ pipeline_run  │      │ pipeline_run_id  │
                    │ pipeline_step │      │ sender_agent_n.  │
                    │ terminal_id   │      │ content          │
                    │ status        │      │ created_at       │
                    └───────────────┘      └──────────────────┘
```

### Agent
| Field | Type | Note |
|---|---|---|
| id | UUID string | PK |
| project_id | FK -> projects | CASCADE delete |
| name | str(255) | Unique per project |
| system_prompt | Text | Prompt di sistema per Claude Code |
| model | str(50) nullable | es. `claude-sonnet-4-20250514` |
| allowed_tools | JSON nullable | Lista MCP tools accessibili |

### Pipeline
| Field | Type | Note |
|---|---|---|
| id | UUID string | PK |
| project_id | FK -> projects | CASCADE delete |
| name | str(255) | |

### PipelineStep
| Field | Type | Note |
|---|---|---|
| id | UUID string | PK |
| pipeline_id | FK -> pipelines | CASCADE delete |
| agent_id | FK -> agents | |
| order_index | int | Unique per pipeline |
| terminal_command | Text | Comando shell, supporta `$issue_id`, `$project_id`, `$project_path` |

### PipelineRun
| Field | Type | Note |
|---|---|---|
| id | UUID string | PK |
| pipeline_id | FK -> pipelines | |
| issue_id | str(255) | External issue ID |
| status | Enum | RUNNING / COMPLETED / FAILED |
| current_step_index | int | 0-based, avanza a ogni step completato |
| started_at | datetime | |
| finished_at | datetime | |

### PipelineStepRun
| Field | Type | Note |
|---|---|---|
| id | UUID string | PK |
| pipeline_run_id | FK -> pipeline_runs | CASCADE delete |
| pipeline_step_id | FK -> pipeline_steps | |
| terminal_id | FK -> terminal_commands | SET NULL su delete |
| status | Enum | PENDING -> RUNNING -> COMPLETED / FAILED |

### PipelineMessage
| Field | Type | Note |
|---|---|---|
| id | UUID string | PK |
| pipeline_run_id | FK -> pipeline_runs | CASCADE delete |
| sender_agent_name | str(255) | Nome dell'agente |
| content | Text | Messaggio |

---

## Services

### AgentService (`backend/app/services/agent_service.py`)
- CRUD standard (create, list_by_project, get_by_id, update, delete)
- `seed_defaults(project_id)` — crea 6 agenti predefiniti (idempotente)

### PipelineService (`backend/app/services/pipeline_service.py`)
- CRUD pipeline + step (create, list_by_project, get_by_id, update, delete)
- `seed_default(project_id)` — crea pipeline base 6-step

### PipelineRunService (`backend/app/services/pipeline_run_service.py`)
**Core orchestrator.** Metodi principali:

- `start(pipeline_id, issue_id, project_id, project_path)` — valida, crea run + step_runs, lancia `_execute()` in `asyncio.create_task()`, ritorna subito
- `_execute(run_id)` — loop sequenziale sugli step:
  1. Crea log terminal via `terminal_service.create_log()`
  2. Sostituisce variabili nel `terminal_command`
  3. Spawna `asyncio.create_subprocess_shell(cmd, cwd=project_path)`
  4. Task parallelo: legge stdout/stderr → `terminal_service.push_output()`
  5. Attende `proc.wait()` con timeout configurabile (default 30min)
  6. Exit code 0 = COMPLETED, != 0 = FAILED → break
  7. `terminal_service.destroy_log()`
- `get_status(run_id)` — stato run + step_runs con agent_name
- `add_message(run_id, sender_agent_name, content)` — chat agenti
- `get_messages(run_id)` — recupera messaggi
- `list_for_issue(issue_id)` — run attive/completate

### PipelineTaskManager (`backend/app/services/pipeline_task_manager.py`)
- Registry dizionario `{run_id: asyncio.Task}`
- `start_task(run_id, task)`, `cancel_task(run_id)`, `cleanup_task(run_id)`

### ArtifactService (`backend/app/services/artifact_service.py`)
- `save_artifact(project_path, issue_id, filename, content)` — scrive in `.manager_ai/issues/{id}/artifacts/{filename}`
- `read_artifact(project_path, issue_id, filename)` — legge contenuto
- `list_artifacts(project_path, issue_id)` — elenca file

---

## Orchestrator Flow

```
POST /api/projects/{id}/pipeline-runs  {pipeline_id, issue_id}
  │
  ├─ Check: nessuna run attiva per questa issue
  ├─ Crea PipelineRun (status=RUNNING, current_step_index=0)
  ├─ Crea PipelineStepRun per ogni step (status=PENDING)
  ├─ Avvia background task: asyncio.create_task(_execute(run_id))
  └─ Ritorna {run_id, status: "RUNNING", steps: [...]}
  
  
_execute(run_id) — background asyncio task:
  
  STEP 0: CodebaseExplorer
    ├─ step_run.status = RUNNING
    ├─ terminal = create_log(project_id, issue_id, label="CodebaseExplorer")
    ├─ cmd = "claude -p 'analyze codebase for issue $issue_id'"
    ├─ proc = create_subprocess_shell(cmd)
    ├─ stream: proc.stdout → push_output(terminal_id)
    ├─ exit_code = await proc.wait()  [timeout: 30min]
    ├─ exit_code == 0? step_run.status = COMPLETED : FAILED
    └─ destroy_log(terminal_id)
    
  STEP 1: BrainstormingAgent
    ├─ ... (stesso pattern)
    └─ Se l'agente chiama ask_user_question MCP tool,
       l'utente risponde da UI, le risposte vengono salvate
       dall'agente in artifacts/answers.md
    
  STEP 2: SpecWriter → scrive spec via create_issue_spec MCP tool
  
  STEP 3: PlanWriter → scrive plan via create_issue_plan + create_plan_tasks
  
  STEP 4: Developer → implementa modifiche codice
  
  STEP 5: Reviewer → review del codice
    
  ├─ Tutti step COMPLETED → run.status = COMPLETED
  └─ Un step FAILED → run.status = FAILED (stop sequenza)
```

---

## Agent Communication

### Chat (PipelineMessage)
Ogni agente puo scrivere messaggi nella chat della pipeline tramite MCP tool:

```
send_agent_message(run_id, sender_agent_name, content)
```

L'agente successivo, prima di iniziare, legge la chat:

```
get_pipeline_messages(run_id)
```

Esempio di flusso chat:
```
[CodebaseExplorer]: Found Python backend in backend/, React frontend in frontend/. 
                    3 services, 12 routes. Main deps: FastAPI, SQLAlchemy, React Query.

[BrainstormingAgent]: Asked user 5 questions about requirements. Answers saved in artifacts/answers.md.

[SpecWriter]: Read answers.md. Writing specification for REST API with 3 new endpoints...
```

### File Artifacts
Salvati in `.manager_ai/issues/{issue_id}/artifacts/`. L'agente brainstorming scrive `answers.md` qui. Gli agenti successivi leggono i file via MCP tool o filesystem.

---

## Default Agents

Creati automaticamente da `AgentService.seed_defaults()` per ogni nuovo progetto.

| Nome | System Prompt | Ruolo |
|---|---|---|
| CodebaseExplorer | Analyze codebase structure, files, dependencies, patterns. Read project files and understand architecture. | Esplorazione |
| BrainstormingAgent | Ask clarifying questions. Save answers to artifacts/answers.md. Ensure requirements are understood. | Requisiti |
| SpecWriter | Write technical specs in markdown. Use project context + brainstorming answers. | Specifiche |
| PlanWriter | Break specs into implementation plans with ordered tasks. Create actionable steps. | Pianificazione |
| Developer | Implement code according to the plan. Write tests, modify files, ensure quality. | Sviluppo |
| Reviewer | Review code for correctness, style, bugs. Provide constructive feedback. | Controllo qualita |

## Default Pipeline

Creata da `PipelineService.seed_default()`. 6 step in ordine:

| # | Agente | Comando |
|---|---|---|
| 0 | CodebaseExplorer | `claude -p "explore codebase structure for issue $issue_id in $project_path"` |
| 1 | BrainstormingAgent | `claude -p "brainstorm requirements for issue $issue_id, ask questions, save answers"` |
| 2 | SpecWriter | `claude -p "write technical specification for issue $issue_id"` |
| 3 | PlanWriter | `claude -p "write implementation plan and tasks for issue $issue_id"` |
| 4 | Developer | `claude -p "implement the plan for issue $issue_id"` |
| 5 | Reviewer | `claude -p "review all changes for issue $issue_id, check for bugs"` |

---

## REST API

Tutti gli endpoint hanno prefix `/api/projects/{project_id}`.

### Agents
| Method | Path | Descrizione |
|---|---|---|
| GET | `/agents` | Lista agenti del progetto |
| POST | `/agents` | Crea agente |
| GET | `/agents/{id}` | Dettaglio agente |
| PUT | `/agents/{id}` | Modifica agente |
| DELETE | `/agents/{id}` | Elimina agente |

### Pipelines
| Method | Path | Descrizione |
|---|---|---|
| GET | `/pipelines` | Lista pipeline (con step e agent_name) |
| POST | `/pipelines` | Crea pipeline con step |
| GET | `/pipelines/{id}` | Dettaglio pipeline |
| PUT | `/pipelines/{id}` | Modifica pipeline/step |
| DELETE | `/pipelines/{id}` | Elimina pipeline |

### Pipeline Runs
| Method | Path | Descrizione |
|---|---|---|
| POST | `/pipeline-runs` | Avvia pipeline `{pipeline_id, issue_id}` |
| GET | `/pipeline-runs?issue_id=X` | Lista run per issue |
| GET | `/pipeline-runs/{id}` | Stato run + step_runs |
| GET | `/pipeline-runs/{id}/messages` | Chat messaggi |
| POST | `/pipeline-runs/{id}/messages` | Invia messaggio `{sender_agent_name, content}` |

---

## MCP Tools

Esposti dal server MCP per essere chiamati dagli agenti Claude Code durante l'esecuzione.

| Tool | Parametri | Uso |
|---|---|---|
| `list_agents` | project_id | Scoprire agenti disponibili |
| `create_agent` | project_id, name, system_prompt, model?, allowed_tools? | Creare nuovo agente |
| `list_pipelines` | project_id | Scoprire pipeline disponibili |
| `create_pipeline` | project_id, name, steps[] | Creare nuova pipeline |
| `run_pipeline` | project_id, pipeline_id, issue_id | Avviare esecuzione |
| `get_pipeline_run_status` | project_id, run_id | Verificare stato run |
| `send_agent_message` | run_id, sender_agent_name, content | Scrivere nella chat |
| `get_pipeline_messages` | run_id | Leggere cronologia chat |

---

## Frontend Architecture

### Stack
- React Query per data fetching (pattern esistente)
- TerminalPanel (xterm.js) in readOnly per output step
- Polling 2s su run status mentre RUNNING
- shadcn/ui components per form, dialog, card

### Route
| Route | Componente | Descrizione |
|---|---|---|
| `/projects/{id}/agents` | AgentsTab | CRUD agenti |
| `/projects/{id}/pipelines` | PipelinesTab | CRUD pipeline + step builder |
| `/projects/{id}/issues/{id}` | IssueDetail (modificata) | + pulsante Run Pipeline + progress panel |

### Component Tree (Issue Detail con pipeline attiva)
```
IssueDetail
├── IssueHeader
│   └── PipelineRunButton          ← apre dialog selettore pipeline
├── ResizablePanelGroup
│   ├── IssueContent (left)
│   │   ├── Spec / Plan / Tasks
│   │   └── AgentChat               ← se run attiva, mostra messaggi
│   └── PipelineProgress (right)    ← se run attiva
│       ├── StepIndicator[]          ← PENDING / RUNNING / COMPLETED / FAILED
│       └── TerminalPanel (readOnly) ← output step corrente
```

### Data Flow
```
[Run Pipeline click]
  → useStartPipelineRun.mutate({pipeline_id, issue_id})
    → POST /api/pipeline-runs
      → PipelineRunService.start() crea run + avvia background task
      → Ritorna {run_id, status: "RUNNING"}
  → usePipelineRunStatus(run_id) con refetchInterval: 2000
    → GET /api/pipeline-runs/{run_id}
      → Mostra step status
  → usePipelineMessages(run_id) con refetchInterval: 5000
    → GET /api/pipeline-runs/{run_id}/messages
      → AgentChat popolata
  → TerminalPanel per step corrente
    → WebSocket /api/terminals/{terminal_id}/ws
      → Output in tempo reale
```

---

## Sicurezza & Edge Cases

- **Race condition**: lock per-issue (in-memory) per evitare doppio start
- **Timeout step**: 30 minuti configurabile, scattato = step FAILED
- **Server restart**: task in memoria persi, run rimangono RUNNING → cleanup startup li marca FAILED
- **Cancellazione**: `DELETE /api/pipeline-runs/{id}` kill subprocess + cleanup
- **Buffer output**: `terminal_max_buffer_bytes` limita memoria (già esistente)

---

## File Summary

```
backend/app/
├── models/
│   ├── agent.py              (esistente, nessuna modifica)
│   ├── pipeline.py            (esistente, nessuna modifica)
│   └── pipeline_run.py        (esistente, nessuna modifica)
├── services/
│   ├── agent_service.py       (NUOVO)
│   ├── pipeline_service.py    (NUOVO)
│   ├── pipeline_run_service.py (NUOVO)
│   ├── pipeline_task_manager.py (NUOVO)
│   └── artifact_service.py    (NUOVO)
├── schemas/
│   ├── agent.py               (NUOVO)
│   ├── pipeline.py            (NUOVO)
│   └── pipeline_run.py        (NUOVO)
├── routers/
│   ├── agents.py              (NUOVO)
│   ├── pipelines.py           (NUOVO)
│   └── pipeline_runs.py       (NUOVO)
├── mcp/
│   ├── server.py              (MODIFICA: +8 tools)
│   └── default_settings.json  (MODIFICA: +8 descrizioni)
└── main.py                    (MODIFICA: +3 router)

frontend/src/
├── shared/types/index.ts      (MODIFICA: +tipi Agent/Pipeline)
├── features/pipelines/
│   ├── api.ts                 (NUOVO)
│   ├── hooks.ts               (NUOVO)
│   └── components/
│       ├── agents-tab.tsx     (NUOVO)
│       ├── pipelines-tab.tsx  (NUOVO)
│       ├── pipeline-run-button.tsx (NUOVO)
│       ├── pipeline-progress.tsx   (NUOVO)
│       └── agent-chat.tsx     (NUOVO)
└── routes/projects/$projectId/
    ├── agents.tsx             (NUOVO)
    ├── pipelines.tsx          (NUOVO)
    └── issues/$issueId.tsx    (MODIFICA: integrazione pipeline)

.manager_ai/issues/{id}/
└── artifacts/
    └── answers.md             (creato da BrainstormingAgent)
```
