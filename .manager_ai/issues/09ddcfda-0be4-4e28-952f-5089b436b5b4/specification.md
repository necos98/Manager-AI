# Specifica: Agent output terminal — streaming live via xterm.js

## Obiettivo
Mostrare l'output live degli agenti della pipeline in un terminale xterm.js read-only nella pagina dei dettagli issue, riutilizzando l'infrastruttura terminale esistente.

## Architettura

```
ClaudeCodeExecutor.run_streaming()
  → OrchestratorService._run_agent_step()
    → TerminalService.create_log() + push_output()
      → _terminal_reader (legge da queue)
        → WebSocket → TerminalPanel (readOnly=true)
```

Principio chiave: un log terminal è una entry di TerminalService senza PTY. Tutto il resto (reader, buffer, WebSocket, recording, frontend) funziona identico — solo la fonte dati cambia da PTY a `asyncio.Queue`.

---

## Backend

### 1. TerminalService — modalità log

Aggiungere a `TerminalService`:

- **`create_log(project_id, issue_id, project_path, label)`**: crea entry con `mode: "log"`, `asyncio.Queue()`, nessun PTY, nessuno spawn shell. Restituisce `TerminalResponse`.
- **`push_output(terminal_id, text)`**: `await self._queues[terminal_id].put(text)` — pusha testo nella coda del terminale.
- **`destroy_log(terminal_id)`**: pusha sentinella `None` nella coda, poi cleanup standard (save recording, mark_closed).
- Nuovo dict `_queues` analogo a `_buffers` per tracciare le code asyncio.
- **`_to_response`**: aggiungere campo `mode` ("pty" | "log") e `label` nella risposta.

### 2. _terminal_reader — supporto log mode

Modificare `_terminal_reader` in `routers/terminals.py`:

- Se il terminale ha `mode == "log"`: loop `await queue.get()` invece di PTY read bloccante.
- Se riceve `None` dalla coda: EOF — chiudi WebSocket, salva recording, mark_closed.
- Se `mode == "pty"`: comportamento esistente invariato.
- La coda è asyncio.Queue — leggi direttamente senza `run_in_executor`.

### 3. ClaudeCodeExecutor.run_streaming()

Nuovo metodo su `ClaudeCodeExecutor`:

```python
async def run_streaming(
    self,
    prompt: str,
    project_path: str,
    env_vars: dict | None = None,
    timeout: int = 300,
    tool_guidance: str = "",
    on_output: Callable[[str], Awaitable[None]] | None = None,
) -> ExecutorResult:
```

- Stesso spawn di `run()` (env vars, cmd, cwd, creationflags).
- Invece di `proc.communicate()`, legge stdout linea-per-linea in un thread con `proc.stdout.readline()`.
- Per ogni linea: chiama `await on_output(line)` se callback fornito.
- Accumula stdout per l'ExecutorResult finale.
- Timeout identico: `_terminate_tree` se scade.
- **Preservare** `MANAGER_AI_AGENT_NAME` e `MANAGER_AI_AGENT_ROLE` nelle env vars (memoria: identità agente).

### 4. OrchestratorService._run_agent_step() — integrazione

Modificare `_run_agent_step()`:

1. Prima di eseguire l'agente: `log_term = terminal_service.create_log(...)`.
2. Salvare `step.terminal_id = log_term["id"]` nel DB.
3. Emettere evento `agent_terminal_created` con payload: `project_id`, `issue_id`, `pipeline_run_id`, `step_id`, `terminal_id`, `agent_name`.
4. Usare `run_streaming()` con callback: `lambda text: terminal_service.push_output(log_term["id"], text)`.
5. Dopo l'esecuzione (successo o fallimento): `terminal_service.destroy_log(log_term["id"])`.

### 5. AgentStepRun model — terminal_id

Aggiungere colonna nullable `terminal_id` (Text, nullable=True) al modello `AgentStepRun`.
Creare migration Alembic.

### 6. AgentStepRunResponse schema

Aggiungere `terminal_id: str | None = None` allo schema Pydantic.
`get_pipeline_status` già serializza gli step — `terminal_id` arriva automaticamente.

### 7. Endpoint `POST /api/terminals/log`

Nuovo endpoint:

```
POST /api/terminals/log
Body: { project_id, issue_id, label }
Response: TerminalResponse (con mode="log")
```

- Chiama `terminal_service.create_log(...)`.
- Avvia `_ensure_reader` per il terminale creato.
- Il WebSocket endpoint esistente (`/{terminal_id}/ws`) funziona senza modifiche: fa replay del buffer, registra il WS, il reader pusha output dalla coda.

---

## Frontend

### 8. TerminalPanel — prop readOnly

Aggiungere prop `readOnly?: boolean` (default false).

Quando `readOnly=true`:
- **Niente** `term.onData()` — nessun tasto inviato al backend.
- **Niente** handler Ctrl+V paste.
- **Nascondere** pulsanti toolbar: Files, Voice (non servono in read-only).
- **Mantenere**: Copy, Search, Download Log.
- Resize funziona normalmente.

### 9. API client — createLogTerminal

Aggiungere funzione `createLogTerminal(projectId, issueId, label)` in `frontend/src/api/`.
Hook React Query: `useCreateLogTerminal()`.

### 10. IssueDetail — tab "Agent Terminal"

- Nuovo tab "Agent Terminal" nella lista tab.
- **Visibile solo** quando: `latestRun?.status === "running"` e `runningStep?.terminal_id` esiste.
- Contenuto: `<TerminalPanel readOnly={true} terminalId={runningStep.terminal_id} projectId={projectId} />`.
- Quando lo step finisce (terminale distrutto), il tab sparisce automaticamente perché `terminal_id` rimosso dallo step.

### 11. EventContext — evento agent_terminal_created

- Aggiungere `agent_terminal_created` alla lista eventi silent (nessun toast).
- Alla ricezione: invalidare query pipeline run per l'issue (così il frontend ricarica gli step e trova `terminal_id`).
- **L'evento DEVE includere `project_id`** nel payload (memoria: React Query invalidation richiede project_id).

---

## Testing

### Backend
- Unit test `TerminalService.create_log` + `push_output` + `destroy_log`.
- Unit test `_terminal_reader` in log mode con mock queue.
- Integration test `POST /api/terminals/log`.
- Unit test `ClaudeCodeExecutor.run_streaming` con mock subprocess.

### Frontend
- Verificare che `TerminalPanel readOnly={true}` non accetti input tastiera.
- Verificare che il tab "Agent Terminal" appaia/scompaia correttamente con il ciclo di vita dello step.
