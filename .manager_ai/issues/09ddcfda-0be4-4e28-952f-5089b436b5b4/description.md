## Problema
Quando un agente viene eseguito nella pipeline, l'utente non può vedere cosa sta facendo in tempo reale. L'output di `claude` viene catturato solo alla fine (`proc.communicate()` in `ClaudeCodeExecutor`). L'utente vede solo:
- Cambi di stato degli step (running/completed/failed)
- Messaggi intenzionali via `send_agent_message`
- Summary finale da `complete_agent_step`

## Soluzione
Mostrare l'output dell'agente in un terminale live (xterm.js) nella pagina dei dettagli issue, riutilizzando l'infrastruttura terminale esistente.

### Backend
1. **TerminalService** — aggiungere modalità "log": `create_log(project_id, issue_id, project_path, label)` che crea un terminal senza spawnare PTY, usando `asyncio.Queue` come fonte dati. Aggiungere `push_output(terminal_id, text)` per pushare testo nella coda.

2. **ClaudeCodeExecutor** — aggiungere `run_streaming()` che legge stdout linea-per-linea e chiama un callback `on_output(text)` async.

3. **`/api/terminals/log`** — nuovo endpoint POST per creare terminal log. Modificare `_terminal_reader` per supportare terminali log-mode (legge da queue invece che da PTY). Modificare WebSocket endpoint per log terminal (read-only, nessun write verso PTY).

4. **OrchestratorService._run_agent_step()** — creare terminal log per ogni step, usare `run_streaming()` con callback che chiama `terminal_service.push_output()`. Emettere evento `agent_terminal_created`.

5. **AgentStepRun** model — aggiungere colonna `terminal_id` (nullable).

### Frontend
6. **TerminalPanel** — aggiungere prop `readOnly`. Quando true: niente `term.onData()`, niente paste, niente input vocale.

7. **API + hooks** — `createLogTerminal()`, `useCreateLogTerminal()`.

8. **IssueDetail** — nuovo tab "Agent Terminal" che mostra `TerminalPanel readOnly={true}` quando c'è un pipeline attivo con `terminal_id`.

9. **EventContext** — gestire evento `agent_terminal_created`.