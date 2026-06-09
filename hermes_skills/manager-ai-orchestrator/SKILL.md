---
name: manager-ai-orchestrator
description: "Orchestrate Manager AI projects via MCP — create issues, start pipeline runs, monitor status."
version: 2.1.0
author: Manager AI
platforms: [windows, linux, macos]
---

# Manager AI Orchestrator

You are connected to **Manager AI** via its MCP server (toolset `manager-ai`).
Your role: **create issues → start pipeline → monitor status**.

La pipeline gira **in automatico** da sola — Manager AI spawna gli agenti in
PTY, avanza gli step, e finalizza. Tu devi solo avviarla e monitorare.

## Prerequisites

```bash
hermes mcp add manager-ai-orchestrator --url http://localhost:8000/mcp-orchestrator/
```

Il `project_id` si trova in `manager.json` alla radice del repo.

## Workflow

### 1. Crea una issue (SOLO issue — niente specifica)

Quando l'utente ti chiede di creare una issue, fai **solo** questo:

```python
# Passo 1: Crea la issue con una descrizione chiara
issue = create_issue(
    project_id=...,
    description="Descrizione chiara e comprensibile di cosa va fatto",
    priority=3,
)
# → {id: "iss-xxx", status: "New"}

# Passo 2: Imposta un nome comprensibile
set_issue_name(
    project_id=...,
    issue_id=issue["id"],
    name="Nome breve e significativo",
)
```

**Fermati qui.** Non creare specifica, non avviare pipeline, non fare altro.
Solo la issue con un buon nome e una buona descrizione. Se l'utente vuole
fare altro, te lo chiederà esplicitamente.

> ⚠️ **REGOLA IMPORTANTE**: create_issue → set_issue_name → STOP.
> Non chiamare `create_issue_spec`, non avviare `run_pipeline`, non fare
> brainstorming. L'utente deciderà dopo cosa fare.

### 2. Configura agenti e pipeline (quando richiesto)

Se l'utente ti chiede esplicitamente di configurare agenti o pipeline:

```python
# Crea agenti
create_agent(name="SpecWriter", intent="Write specification")
create_agent(name="Developer", intent="Implement the feature")

# Crea pipeline con gli step
pipeline = create_pipeline(name="Feature Pipeline", steps=[
    {"agent_id": "<specwriter-id>", "order_index": 0},
    {"agent_id": "<developer-id>", "order_index": 1},
])
```

### 3. Avvia la pipeline (solo su richiesta esplicita)

Solo quando l'utente dice esplicitamente "avvia la pipeline" o "run":

```python
run = run_pipeline(project_id=..., pipeline_id=..., issue_id=...)
# → status: "RUNNING" — Manager AI fa tutto da solo
```

### 4. Monitora lo stato (quando richiesto)

```python
# Quando vuoi vedere come sta procedendo
status = get_pipeline_run_status(run_id=run["id"])
# → {status: "RUNNING", current_step_index: 0, steps: [...]}

active = get_active_pipeline_run(issue_id="iss-xxx")
# → {status: "RUNNING", ...} oppure None se finita
```

### 5. Memoria (dopo completamento)

```python
memory_create(project_id=..., title="Decisione", description="Cosa è stato deciso e perché")
```

## MCP tools principali

| Tool | Cosa fa |
|------|---------|
| `create_issue` | Crea una nuova issue (solo issue, niente spec) |
| `set_issue_name` | Imposta un nome comprensibile alla issue |
| `create_agent` | Crea un agente (per la pipeline) |
| `create_pipeline` | Crea una pipeline con step |
| `run_pipeline` | **Avvia la pipeline** (sempre auto-mode) |
| `get_pipeline_run_status` | Mostra stato corrente della pipeline |
| `get_active_pipeline_run` | Pipeline attiva per una issue |
| `get_active_agent` | Agente attualmente in esecuzione |
| `memory_create` | Salva una memoria |
| `memory_search` | Cerca memorie esistenti |
| `add_pipeline_event_rule` | Collega eventi pipeline ad azioni (es. auto-set issue status) |
| `get_project_context` | Contesto del progetto |
