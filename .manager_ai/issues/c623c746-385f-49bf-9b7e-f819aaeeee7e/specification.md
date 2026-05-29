## Problem

La pagina Agents mostra la lista degli agenti con solo operazioni CRUD base (Create, Edit, Delete). Manca completamente la funzionalità di "avviare" un agente — sia come tool MCP che come bottone UI per spawnare un terminale dedicato.

### Root cause analysis

1. **MCP tools mancanti**: `server.py` espone solo `create_agent` e `list_agents`. I tool `get_agent`, `update_agent`, `delete_agent` non esistono, anche se referenziati dal comando `/manage-agent` e dalle descrizioni in `default_settings.json`.

2. **`create_agent` non accetta `intent`**: Il modello `Agent` ha il campo `intent`, ma né `AgentService.create()` né il tool MCP `create_agent` lo accettano. Il comando `/manage-agent` chiede l'intent ma non può passarlo.

3. **UI senza "Start Agent"**: La `AgentsTab` non ha un bottone per avviare un terminale interattivo con un agente specifico. L'utente non può lanciare una conversazione direttamente con un agente dalla lista.

## Requirements

### 1. Ripristino tool MCP

- Aggiungere `get_agent(agent_id)` — restituisce dettaglio singolo agente
- Aggiungere `update_agent(agent_id, ...)` — aggiorna campi specificati (name, intent, model, allowed_tools)
- Aggiungere `delete_agent(agent_id)` — cancella agente (già presente nel frontend API ma non come MCP tool)
- Fix `create_agent`: aggiungere parametro `system_prompt` che viene salvato come `intent` sul model
- Fix `AgentService.create()`: accettare e salvare il campo `intent`
- Aggiornare `default_settings.json`: mantenere descrizioni per `get_agent`, `update_agent`, `delete_agent`; sistemare descrizione `create_agent`

### 2. UI "Start Agent" — spawn terminale

- Aggiungere bottone "Start" (icona Play) su ogni riga agente nella `AgentsTab`
- Al click: chiamare API backend per creare un terminale che esegue `claude` con l'agente selezionato
- Il terminale deve passare all'agente l'`intent` dell'agent come system prompt
- Aprire il terminale in una nuova tab/finestra o in un pannello dedicato

### 3. Backend endpoint

- `POST /api/agents/{agent_id}/start` — crea un terminale PTY che lancia `claude` (o il comando configurato) con il system prompt dell'agente
- Il terminale viene restituito come `{ terminal_id, agent_name }` e il frontend lo apre nel TerminalPanel esistente

## Success criteria

- `/manage-agent` funziona correttamente: può creare, ispezionare, modificare, cancellare agenti
- Ogni agente nella lista ha un bottone "Start" visibile
- Cliccando "Start" si apre un terminale con `claude` inizializzato con l'intent dell'agente
- I tool MCP `create_agent`, `get_agent`, `update_agent`, `delete_agent`, `list_agents` sono tutti funzionanti
