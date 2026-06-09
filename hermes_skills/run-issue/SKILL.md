---
name: run-issue
description: "Esegui una issue di Manager AI — analizza, specifica, pianifica, implementa e completa"
version: 1.1.0
author: Manager AI
platforms: [windows, linux, macos]
---

# Run Issue

Sei stato spawnato per lavorare su una issue di Manager AI. La tua istruzione è contenuta nel messaggio dell'utente (la `-q` query) — di solito un ID issue.

## Prerequisiti

Manager AI deve essere in esecuzione (`python start.py` dal repo Manager-AI).  
Il worker MCP deve essere configurato in Hermes:

```bash
hermes mcp add manager-ai-worker --url http://localhost:8000/mcp/
```

## Workflow

### 1. Leggi i dettagli della issue

Usa `worker_get_issue_details` con l'ID issue fornito. Il `project_id` si trova in `manager.json` nella root del progetto.

### 2. Memoria — lettura obbligatoria

Cerca ricordi pertinenti nel filesystem:

```bash
grep -ri "<3-5 keywords dalla descrizione issue>" .manager_ai/memories/
```

Se ci sono risultati, leggi i file `.manager_ai/memories/<id>.md` rilevanti e incorporali nella specifica/piano/implementazione. Salta solo per issue banali (fix di typo, rename).

### 3. Project links — verifica obbligatoria

Chiama `get_project_links` per scoprire progetti collegati. Se il progetto corrente è collegato ad altri, considera l'impatto cross-progetto prima di scrivere specifica/piano.

### 4. Segui il lifecycle della issue

In base allo **status corrente** della issue, continua la pipeline:

- **New**: Analizza la issue, **imposta un nome se mancante** via `worker_set_issue_name`. Se il task è specificamente di **analisi/design/specifica** (come da istruzioni utente), allora fai brainstorming e crea la specifica via `create_issue_spec`. Altrimenti **fermati** — l'utente o un altro agente gestirà la specifica in un secondo momento.

- **Reasoning**: Rivedi la specifica. Crea il piano di implementazione via `create_issue_plan` con task atomici (`create_plan_tasks`). **Non creare file `.md` locali** per il piano — usa sempre gli MCP tool.

- **Planned**: Rivedi il piano. Se è ok, auto-accetta: chiama `accept_issue` per portare la issue in Accepted, poi procedi direttamente all'implementazione. **Non chiedere approvazione all'utente** — la fase di brainstorming è già servita come gate di approvazione.

- **Accepted**: Prendi il prossimo task pending, implementalo e aggiorna gli status dei task man mano. **Inizia immediatamente senza chiedere.** Prendi decisioni autonome durante l'implementazione: se trovi un vero blocco (qualcosa che non puoi risolvere da contesto, codice o memoria), solo allora usa `ask_user_question`. **Non chiedere conferme, approvazioni o "devo continuare?"** — continua e basta. Quando tutti i task sono completi, chiama `complete_issue` immediatamente e procedi al memory write senza chiedere.

### 5. Contesto del progetto

Prima di iniziare l'implementazione, chiama `worker_get_project_context` per capire il codebase.

### 6. Esecuzione dei task

Lavora attraverso i task sequenzialmente, aggiornando ogni status a "In Progress" quando inizi e "Completed" quando finisci.

### 7. Completamento e memoria — scrittura obbligatoria

Quando tutti i task sono completati, scrivi un recap e chiama `complete_issue`. Poi:

**Memory write (obbligatorio).** Dal recap, estrai fatti durevoli:
- Decisioni architetturali con ragionamento
- Constraints non enforceati dal codice
- Preferenze dell'utente emerse
- Gotcha non ovvi scoperti

Per ogni fatto, cerca prima con `grep -ri "<keyword>" .manager_ai/memories/` per vedere se esiste già un memory; poi chiama `memory_update` se trovato, o `memory_create` per uno nuovo.

**Non salvare:**
- Task state transiente
- Riassunti di spec/plan (già nel record issue)
- Info già in `CLAUDE.md` o `AGENTS.md`
