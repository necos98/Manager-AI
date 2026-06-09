# Analisi Sovrapposizione Tool MCP — Worker vs Orchestrator

> **Data:** 2026-06-09
> **Scopo:** Identificare TUTTI i tool con nome identico tra `/mcp` (Worker) e `/mcp-orchestrator` (Orchestrator), e proporre la separazione definitiva per avere ZERO overlap.

---

## 1. Architettura Attuale

Entrambi gli MCP server condividono lo stesso database e backend FastAPI, ma espongono tool con **nome identico** su mount point diversi:

| Mount | Server file | Audience dichiarata |
|-------|-------------|-------------------|
| `/mcp` | `server.py` | Claude Code (worker / coding agent) |
| `/mcp-orchestrator` | `orchestrator_server.py` | Hermes (orchestrator / amministrazione) |

Entrambi importano le implementazioni da `shared_tools.py`, ma il worker (`server.py`) ha anche **implementazioni locali** (non da shared_tools) per diversi tool di agent/pipeline CRUD.

---

## 2. Censimento Completo dei Tool

### 2.1 Issue Tools

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `create_issue` | ❌ | ✅ | OK — orchestrator solo |
| `get_issue_details` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `get_issue_status` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `list_issues` | ❌ | ✅ (shared) | OK — orchestrator solo |
| `get_issue_statuses` | ❌ | ✅ (shared) | OK — orchestrator solo |
| `set_issue_name` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `delete_issue` | ❌ | ✅ (shared) | OK — orchestrator solo |
| `create_issue_spec` | ✅ (shared) | ❌ | OK — worker solo |
| `edit_issue_spec` | ✅ (shared) | ❌ | OK — worker solo |
| `create_issue_plan` | ✅ (shared) | ❌ | OK — worker solo |
| `edit_issue_plan` | ✅ (shared) | ❌ | OK — worker solo |
| `create_plan_tasks` | ✅ (shared) | ❌ | OK — worker solo |
| `replace_plan_tasks` | ✅ (shared) | ❌ | OK — worker solo |
| `get_plan_tasks` | ✅ (shared) | ❌ | OK — worker solo |
| `update_task_status` | ✅ (shared) | ❌ | OK — worker solo |
| `update_task_name` | ✅ (shared) | ❌ | OK — worker solo |
| `delete_task` | ✅ (shared) | ❌ | OK — worker solo |
| `complete_issue` | ✅ (shared) | ❌ | OK — worker solo |
| `accept_issue` | ✅ (shared) | ❌ | OK — worker solo |
| `cancel_issue` | ✅ (shared) | ❌ | OK — worker solo |
| `force_finish_issue` | ✅ (shared) | ❌ | OK — worker solo |
| `get_next_issue` | ✅ (shared) | ❌ | OK — worker solo |

> **3 issue tool overlap.** `get_issue_details`, `get_issue_status`, `set_issue_name` esistono in entrambi.

---

### 2.2 Project Context Tools

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `get_project_context` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `get_project_links` | ✅ (shared) | ❌ | OK — worker solo |
| `get_project_url` | ✅ (shared) | ❌ | OK — worker solo |
| `list_projects` | ❌ | ✅ (shared) | OK — orchestrator solo |
| `get_project` | ❌ | ✅ (shared) | OK — orchestrator solo |

> **1 overlap.** `get_project_context` in entrambi.

---

### 2.3 Agent Tools

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `create_agent` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `list_agents` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `get_agent` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `update_agent` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `delete_agent` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |

> **5 overlap.** Il worker NON dovrebbe avere agent CRUD — è un tool di amministrazione.
> Inoltre, il worker ha implementazioni LOCALI (da `AgentService`), non da `shared_tools`.

---

### 2.4 Pipeline Management Tools

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `create_pipeline` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `list_pipelines` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `get_pipeline` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `update_pipeline` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `delete_pipeline` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `add_step` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `remove_step` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `reorder_steps` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |

> **8 overlap.** Il worker NON dovrebbe gestire pipeline CRUD — è amministrazione pura.

---

### 2.5 Pipeline Event Rule Tools

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `add_pipeline_event_rule` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `remove_pipeline_event_rule` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `list_pipeline_event_rules` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `update_pipeline_event_rule` | ❌ | ✅ (shared) | OK — orchestrator solo |

> **3 overlap.** Event rules sono amministrazione pura, non andrebbero nel worker.

---

### 2.6 Pipeline Run Tools

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `run_pipeline` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `get_pipeline_run_status` | ✅ (locale) | ✅ (shared) | **⚠ OVERLAP** |
| `get_active_agent` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `get_active_pipeline_run` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `send_agent_message` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `get_pipeline_messages` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `finished_pipeline_step` | ✅ (shared) | ✅ (shared) | **⚠ OVERLAP** |
| `pause_pipeline` | ❌ | ✅ (shared) | OK — orchestrator solo |
| `resume_pipeline` | ❌ | ✅ (shared) | OK — orchestrator solo |

> **7 overlap.** Alcuni di questi sono «di frontiera» — servono effettivamente a entrambi
> (`get_active_agent`, `finished_pipeline_step`, ecc.) ma hanno LO STESSO IDENTICO NOME
> su entrambi gli MCP.

---

### 2.7 Memory Tools

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `memory_create` | ✅ (shared) | ❌ | OK — worker solo |
| `memory_update` | ✅ (shared) | ❌ | OK — worker solo |
| `memory_delete` | ✅ (shared) | ❌ | OK — worker solo |
| `memory_link` | ✅ (shared) | ❌ | OK — worker solo |
| `memory_unlink` | ✅ (shared) | ❌ | OK — worker solo |
| `memory_search` | ❌ | ❌ non esiste! | **⚠ Mancante** (citato nella skill ma non implementato) |

> Memory tools sono correttamente solo nel worker. MA `memory_search` non esiste in alcun server.

---

### 2.8 Altri Tool

| Tool | Worker (`/mcp`) | Orchestrator (`/mcp-orchestrator`) | **Stato** |
|------|:-----:|:---------:|:---------:|
| `list_project_files` | ✅ (shared) | ❌ | OK — worker solo |
| `read_project_file` | ✅ (shared) | ❌ | OK — worker solo |
| `send_notification` | ✅ (shared) | ❌ | OK — worker solo |
| `ask_user_question` | ✅ (shared) | ❌ | OK — worker solo |
| `list_plugins` | ✅ (x2! locale+shared) | ❌ | **⚠ Duplicato interno** |
| `get_plugin_config` | ✅ (shared) | ❌ | OK — worker solo |
| `enable_plugin` | ✅ (locale) | ❌ | OK — worker solo (dubbio: dovrebbe stare nell'orchestrator?) |
| `disable_plugin` | ✅ (locale) | ❌ | OK — worker solo (dubbio) |

> `list_plugins` è registrato DUE VOLTE nel worker (linea 238 e linea 682 di `server.py`).
> FastMCP potrebbe scartare il secondo o generare errori.

---

## 3. Riepilogo Sovrapposizioni

| Categoria | Overlap | Descrizione |
|-----------|---------|-------------|
| Issue tools | 3 | `get_issue_details`, `get_issue_status`, `set_issue_name` |
| Project context | 1 | `get_project_context` |
| Agent CRUD | 5 | `create_agent`, `list_agents`, `get_agent`, `update_agent`, `delete_agent` |
| Pipeline CRUD | 8 | `create_pipeline`, `list_pipelines`, `get_pipeline`, `update_pipeline`, `delete_pipeline`, `add_step`, `remove_step`, `reorder_steps` |
| Pipeline event rules | 3 | `add_pipeline_event_rule`, `remove_pipeline_event_rule`, `list_pipeline_event_rules` |
| Pipeline run | 7 | `run_pipeline`, `get_pipeline_run_status`, `get_active_agent`, `get_active_pipeline_run`, `send_agent_message`, `get_pipeline_messages`, `finished_pipeline_step` |
| **TOTALE** | **27** tool con nome identico in entrambi gli MCP! |

---

## 4. Analisi del Problema

### 4.1 Perché Hermes si confonde

Se Hermes ha entrambi gli MCP installati:

```bash
hermes mcp add manager-ai-orchestrator --url http://localhost:8000/mcp-orchestrator/
hermes mcp add manager-ai-worker --url http://localhost:8000/mcp/
```

...quando l'agente chiede di chiamare `get_issue_details`, il tool provider di Hermes
vede **due tool con lo stesso nome** da due MCP diversi. L'LLM non ha modo di distinguerli
se non per descrizione, ma la confusione è inevitabile.

### 4.2 Bug Interni nel Worker

1. `list_plugins` è registrato **due volte** in `server.py` (linea 238 e 682) — la seconda
   potrebbe fallare o causare comportamenti imprevedibili.
2. `enable_plugin` / `disable_plugin` nel worker: non sono tool da worker.
   L'orchestrator dovrebbe gestire l'abilitazione plugin.
3. Implementazioni LOCALI (non shared_tools) di agent/pipeline CRUD nel worker:
   duplicano logica già presente in `shared_tools.py` (violazione DRY).

### 4.3 Tool Mancante

`memory_search` è citato nelle skill orchestator (`manager-ai-orchestrator/SKILL.md`)
ma NON esiste in alcun server MCP.

---

## 5. Strategia di Risoluzione — ZERO Overlap

### Principio Guida

> **Un tool name esiste in UNO E UN SOLO MCP server.**

### Due Opzioni Architetturali

#### Opzione A (consigliata) — Separazione netta

Rimuovere TUTTI i tool di amministrazione dal worker MCP. Il worker MCP espone SOLO
tool per: issue spec/plan/task, memoria, file, notifiche, domande, e step pipeline.
L'orchestrator MCP espone TUTTO il resto.

#### Opzione B — Prefisso worker_

Rinominare i tool del worker con prefisso `worker_` dove c'è overlap
(es. `worker_get_issue_details`). L'orchestrator mantiene i nomi «nudi».

**Raccomandazione: Opzione A.** È più pulita e rispetta il principio di least privilege.

---

## 6. Piano d'Azione Dettagliato (Opzione A)

### 6.1 Cosa Rimuovere dal Worker (`server.py`)

Rimuovere questi tool dal worker MCP (sono di pura amministrazione):

```
# Agent CRUD (5)
create_agent, list_agents, get_agent, update_agent, delete_agent

# Pipeline CRUD (8)
create_pipeline, list_pipelines, get_pipeline, update_pipeline,
delete_pipeline, add_step, remove_step, reorder_steps

# Pipeline Event Rules (3)
add_pipeline_event_rule, remove_pipeline_event_rule, list_pipeline_event_rules

# Pipeline Run — avvio e stato (2)
run_pipeline, get_pipeline_run_status

# Plugin enable/disable (2)
enable_plugin, disable_plugin

# list_plugins — rimuovere il duplicato interno (lasciare una sola istanza)
```

**Totale: 20 tool da rimuovere dal worker.**

### 6.2 Tool «di Frontiera» — Decisione

I tool che servono a ENTRAMBI sono:

| Tool | Serve al worker per... | Serve all'orchestrator per... | Decisione |
|------|----------------------|------------------------------|-----------|
| `get_issue_details` | Leggere l'issue da lavorare | Leggere dettaglio issue prima di creare pipeline | **Mantieni in entrambi** (rinomina worker) |
| `get_issue_status` | Controllare stato issue | Monitorare stato issue | **Mantieni in entrambi** |
| `set_issue_name` | Impostare nome durante spec | Impostare nome in creazione | **Mantieni in entrambi** |
| `get_project_context` | Leggere contesto progetto | Leggere contesto per orchestrazione | **Mantieni in entrambi** |
| `get_active_agent` | Scoprire la propria identità | Vedere quale agente sta girando | **Mantieni in entrambi** |
| `get_active_pipeline_run` | Leggere stato esecuzione | Monitorare pipeline | **Mantieni in entrambi** |
| `send_agent_message` | Inviare messaggi ad altri agent | Potrebbe inviare messaggi | **Mantieni in entrambi** |
| `get_pipeline_messages` | Leggere handoff precedenti | Monitorare comunicazione | **Mantieni in entrambi** |
| `finished_pipeline_step` | Segnalare completamento | — l'orchestrator non completa step | **SOLO worker** → rimuovi da orchestrator |

**Per i tool «di frontiera», usare il prefisso `worker_` nel worker:**

| Nome worker (prefissato) | Nome orchestrator (invariato) |
|--------------------------|------------------------------|
| `worker_get_issue_details` | `get_issue_details` |
| `worker_get_issue_status` | `get_issue_status` |
| `worker_set_issue_name` | `set_issue_name` |
| `worker_get_project_context` | `get_project_context` |
| `worker_get_active_agent` | `get_active_agent` |
| `worker_get_active_pipeline_run` | `get_active_pipeline_run` |
| `worker_send_agent_message` | `send_agent_message` |
| `worker_get_pipeline_messages` | `get_pipeline_messages` |
| — | ~~`finished_pipeline_step`~~ → rimuovere da orchestrator |

### 6.3 Cosa Aggiungere all'Orchestrator

| Tool | Note |
|------|------|
| `memory_search` | Citato nelle skill ma mancante — implementare in shared_tools e registrare in orchestrator_server.py |

### 6.4 Cosa Corregere nel Worker

| Problema | Azione |
|----------|--------|
| `list_plugins` registrato 2x | Rimuovere la definizione locale (linea 238-270), tenere solo quella da shared_tools (linea 682) |
| Plugin enable/disable nel worker | Spostare enable_plugin/disable_plugin nell'orchestrator |
| Implementazioni locali agent/pipeline CRUD | Rimuovere (non servono più) |

### 6.5 Schema Finale Dopo la Pulizia

```
Worker MCP (/mcp) — ~28 tool, tutti con prefisso worker_ dove overlap:

  [issue - spec/plan/task/lifecycle]
  - worker_get_issue_details, worker_get_issue_status, worker_set_issue_name
  - create_issue_spec, edit_issue_spec, create_issue_plan, edit_issue_plan
  - create_plan_tasks, replace_plan_tasks, get_plan_tasks
  - update_task_status, update_task_name, delete_task
  - complete_issue, accept_issue, cancel_issue, force_finish_issue
  - get_next_issue

  [project context]
  - worker_get_project_context, get_project_links, get_project_url

  [pipeline run - step execution]
  - get_active_agent → worker_get_active_agent
  - get_active_pipeline_run → worker_get_active_pipeline_run
  - send_agent_message → worker_send_agent_message
  - get_pipeline_messages → worker_get_pipeline_messages
  - finished_pipeline_step

  [memory]
  - memory_create, memory_update, memory_delete, memory_link, memory_unlink

  [file]
  - list_project_files, read_project_file

  [notifications / questions]
  - send_notification, ask_user_question

  [plugins - read only]
  - list_plugins, get_plugin_config

Orchestrator MCP (/mcp-orchestrator) — ~47 tool, nomi classici:

  [issue - CRUD + dettaglio]
  - create_issue, get_issue_details, get_issue_status, list_issues
  - get_issue_statuses, set_issue_name, delete_issue

  [project context]
  - get_project_context, list_projects, get_project

  [agent CRUD]
  - create_agent, list_agents, get_agent, update_agent, delete_agent

  [pipeline CRUD]
  - create_pipeline, list_pipelines, get_pipeline, update_pipeline, delete_pipeline
  - add_step, remove_step, reorder_steps

  [pipeline event rules]
  - add_pipeline_event_rule, remove_pipeline_event_rule
  - list_pipeline_event_rules, update_pipeline_event_rule

  [pipeline run - lifecycle]
  - run_pipeline, get_pipeline_run_status
  - get_active_agent, get_active_pipeline_run
  - send_agent_message, get_pipeline_messages
  - pause_pipeline, resume_pipeline

  [plugins]
  - enable_plugin, disable_plugin

  [memory search]
  - memory_search (DA IMPLEMENTARE)
```

---

## 7. Note Finali

1. **Hermes dovrebbe connettersi SOLO a `/mcp-orchestrator`**, ma il codice in
   `backend/app/routers/system.py:install_hermes_mcp()` suggerisce di installare
   ENTRAMBI. Dopo questa pulizia, installare entrambi diventa SICURO perché non
   ci saranno più nomi duplicati.

2. **Le skill Hermes** (`hermes_skills/manager-ai-orchestrator/SKILL.md`) referenziano
   `memory_search` che non esiste — va implementato.

3. **La skill worker** (`manager-ai-issue-worker`) usa tool con nomi «nudi» come
   `get_active_agent`, `get_issue_details` ecc. — dopo la rinomina, va aggiornata
   per usare `worker_get_active_agent`, `worker_get_issue_details`, ecc.

4. **L'architettura dual-mcp** è corretta — il problema non è l'architettura ma
   l'esecuzione: il worker MCP include tool che non dovrebbe avere, e i tool condivisi
   hanno lo stesso nome causando conflitto.
