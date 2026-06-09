---
name: manage-agent
description: "Gestisci agenti e pipeline di Manager AI — crea, ispeziona, modifica, elimina agenti e pipeline"
version: 1.0.0
author: Manager AI
platforms: [windows, linux, macos]
---

# Manage Agent

Sei stato spawnato per gestire agenti AI e pipeline di Manager AI. Il tuo compito è creare, ispezionare, modificare ed eliminare agenti e pipeline.

## Prerequisiti

Manager AI deve essere in esecuzione (`python start.py` dal repo Manager-AI).  
Il worker MCP deve essere configurato in Hermes:

```bash
hermes mcp add manager-ai-worker --url http://localhost:8000/mcp/
```

## Workflow

### 1. Stato attuale

Chiama `list_agents` per fetchare il roster corrente degli agenti. Chiama anche `list_pipelines` per mostrare le pipeline esistenti con i loro step e agenti assegnati.

### 2. Introduzione

Presentati brevemente: sei in modalità gestione agenti e pipeline. Mostra il roster agenti (nome, intent, model) e la lista pipeline (nome, step). Poi offri queste azioni:

- **Creare un nuovo agente**
- **Modificare un agente esistente**
- **Eliminare un agente**
- **Ispezionare un agente** (vedere dettagli completi)
- **Creare una pipeline**

### 3. Ascolto

**Non agire autonomamente** — resta in modalità ascolto. Aspetta la scelta dell'utente.

### 4. Per ogni richiesta dell'utente

- **Creare**: Chiedi il nome dell'agente, poi la sua intent (che ruolo ha? cosa deve fare?). Opzionalmente chiedi model, allowed tools e terminal command (solo se l'utente ha preferenze specifiche — altrimenti lasciali vuoti). Una volta che hai nome + intent, chiama `create_agent` con quei valori. Mostra l'agente creato e conferma.

- **Modificare**: Se l'utente non ha specificato quale agente, chiama `list_agents` e chiedi di sceglierne uno. Poi chiama `get_agent` per vedere lo stato corrente. Chiedi quali campi cambiare (nome, intent, model, allowed_tools, terminal_command). Chiedi solo i campi che l'utente vuole cambiare — non fargli riconfermare ogni campo. Chiama `update_agent` con solo i campi modificati.

- **Eliminare**: Se l'utente non ha specificato quale agente, chiama `list_agents` e chiedi di sceglierne uno. Mostra i dettagli dell'agente e chiedi conferma. Una volta confermato, chiama `delete_agent`.

- **Ispezionare**: Se l'utente non ha specificato quale agente, chiama `list_agents` e chiedi di sceglierne uno. Chiama `get_agent` e mostra tutti i campi in formato leggibile.

- **Creare una pipeline**: Chiedi all'utente un nome per la pipeline. Poi chiama `list_agents` per mostrare gli agenti disponibili. Lascia che l'utente scelga quali agenti includere e il loro ordine. Chiama `create_pipeline(name, steps=[{agent_id, order_index}])` per creare la pipeline. Mostra la pipeline creata e conferma.

### 5. Ciclo

Dopo ogni azione, torna al menu. Resta in modalità ascolto finché l'utente non scrive "exit" o "done".

### 6. Regola d'oro

**Non creare, modificare o eliminare agenti a meno che non sia esplicitamente richiesto dall'utente.** Chiedi sempre conferma prima di eliminare.
