## Recap: Agent output terminal — streaming live via xterm.js

Tutte le modifiche implementate come da piano. Di seguito i cambiamenti effettivi.

### Backend (Task 1-7, completati in sessioni precedenti)

- **TerminalService**: aggiunti `create_log()`, `push_output()`, `destroy_log()`, `_queues` dict, campo `mode`/`label` in `_to_response`. Cleanup in `kill()` e `mark_closed()`.
- **terminal_reader**: supporto log mode — loop su `asyncio.Queue.get()` con sentinella `None` per EOF.
- **ClaudeCodeExecutor.run_streaming()**: nuovo metodo che legge stdout linea-per-linea con `proc.stdout.readline()` e chiama callback async `on_output(text)` via `asyncio.run_coroutine_threadsafe`. Accumula stdout per ExecutorResult finale. Timeout con `_terminate_tree`.
- **AgentStepRun model**: colonna `terminal_id` nullable String(36). Migration Alembic creata.
- **AgentStepRunResponse schema**: campo `terminal_id: str | None`.
- **POST /api/terminals/log**: endpoint per creare terminal log, con schema `LogTerminalCreate`.
- **OrchestratorService._run_agent_step()**: crea log terminal prima di eseguire agente, usa `run_streaming()` con callback `push_output`, emette evento `agent_terminal_created`, distrugge log dopo esecuzione.

### Frontend (Task 8-11, task 8 completato in sessione precedente)

- **TerminalPanel readOnly** (Task 8): prop `readOnly` booleana. Quando true: niente `term.onData()`, niente pulsanti Files/Voice nella toolbar. Copy/Search/Download Log mantenuti.
- **API hook** (Task 9): `useCreateLogTerminal()` hook React Query.
- **IssueDetail Agent Terminal tab** (Task 10): nuovo tab "Agent Terminal" visibile quando `runningStep?.terminal_id` esiste. Contiene `TerminalPanel readOnly={true}`. Auto-selezione tab quando `terminal_id` appare. Campo `terminal_id` aggiunto a `PipelineStepRunData` nell'API client.
- **EventContext handler** (Task 11): `agent_terminal_created` aggiunto a eventi silent. Invalida query `["projects", projectId, "issues", issueId, "pipeline-runs"]` per far ricaricare gli step e rendere visibile il tab.

### Verifica

- TypeScript check: nessun errore di tipo.
- ESLint: errori pre-esistenti di configurazione parser (manca `@typescript-eslint/parser`), non introdotti da queste modifiche.
