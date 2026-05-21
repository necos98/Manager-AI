# Piano di implementazione: Agent output terminal

> **Goal:** Streaming live dell'output degli agenti pipeline in un terminale xterm.js read-only.

**Architettura:** Log terminal come entry TerminalService senza PTY, alimentato da asyncio.Queue. ClaudeCodeExecutor.run_streaming() legge stdout linea-per-linea e chiama callback. OrchestratorService crea/distrugge log terminal attorno a ogni step. Frontend mostra TerminalPanel readOnly in nuovo tab "Agent Terminal".

**File toccati:**
- `backend/app/services/terminal_service.py` — create_log, push_output, destroy_log
- `backend/app/routers/terminals.py` — _terminal_reader log mode, POST /api/terminals/log
- `backend/app/hooks/executor.py` — run_streaming()
- `backend/app/models/pipeline.py` — AgentStepRun.terminal_id
- `backend/app/schemas/pipeline.py` — AgentStepRunResponse.terminal_id
- `backend/app/services/orchestrator_service.py` — _run_agent_step log integration
- `backend/app/schemas/terminal.py` — LogTerminalCreate schema
- `frontend/src/features/terminals/components/terminal-panel.tsx` — readOnly prop
- `frontend/src/features/terminals/hooks.ts` — useCreateLogTerminal
- `frontend/src/features/issues/components/issue-detail.tsx` — Agent Terminal tab
- `frontend/src/shared/context/event-context.tsx` — agent_terminal_created handler

---

## Task 1: TerminalService — create_log, push_output, destroy_log

**Files:** Modify `backend/app/services/terminal_service.py`

### Step 1: Aggiungere _queues dict e modificare create_log

Nel costruttore `__init__`:
```python
self._queues: dict[str, asyncio.Queue] = {}
```

Nuovo metodo `create_log`:
```python
async def create_log(
    self,
    project_id: str,
    issue_id: str,
    project_path: str,
    label: str = "",
    cols: int = 120,
    rows: int = 30,
) -> dict:
    import asyncio
    term_id = str(uuid.uuid4())
    entry = {
        "id": term_id,
        "issue_id": issue_id,
        "project_id": project_id,
        "project_path": project_path,
        "pty": None,
        "status": "active",
        "mode": "log",
        "label": label,
        "created_at": datetime.now(timezone.utc),
        "cols": cols,
        "rows": rows,
    }
    with self._lock:
        self._terminals[term_id] = entry
        self._buffers[term_id] = bytearray()
        self._queues[term_id] = asyncio.Queue()
    return self._to_response(entry)
```

### Step 2: push_output

```python
async def push_output(self, terminal_id: str, text: str) -> None:
    with self._lock:
        q = self._queues.get(terminal_id)
    if q is not None:
        await q.put(text)
```

### Step 3: destroy_log

```python
async def destroy_log(self, terminal_id: str) -> None:
    with self._lock:
        q = self._queues.get(terminal_id)
    if q is not None:
        await q.put(None)  # sentinel EOF
```

### Step 4: Aggiornare _to_response

```python
def _to_response(self, entry: dict) -> dict:
    return {
        "id": entry["id"],
        "issue_id": entry["issue_id"],
        "project_id": entry["project_id"],
        "project_path": entry["project_path"],
        "status": entry["status"],
        "mode": entry.get("mode", "pty"),
        "label": entry.get("label", ""),
        "created_at": entry["created_at"],
        "cols": entry["cols"],
        "rows": entry["rows"],
    }
```

### Step 5: Aggiornare kill e mark_closed per pulire _queues

In `kill()`: aggiungere `self._queues.pop(terminal_id, None)`.
In `mark_closed()`: aggiungere `self._queues.pop(terminal_id, None)`.

---

## Task 2: _terminal_reader — supporto log mode

**Files:** Modify `backend/app/routers/terminals.py`

### Step 1: Modificare _terminal_reader

```python
async def _terminal_reader(terminal_id: str, service: TerminalService) -> None:
    loop = asyncio.get_running_loop()
    try:
        entry = service._terminals.get(terminal_id)
    except KeyError:
        return

    is_log = entry.get("mode") == "log" if entry else False

    try:
        if is_log:
            q = service._queues.get(terminal_id)
            if q is None:
                return
            while True:
                data = await q.get()
                if data is None:
                    # EOF sentinel
                    buf = service.get_buffered_output(terminal_id)
                    _save_recording(terminal_id, buf)
                    service.mark_closed(terminal_id)
                    ws = _terminal_ws.pop(terminal_id, None)
                    if ws:
                        try:
                            await ws.close(code=1000, reason="Terminal session ended")
                        except Exception:
                            pass
                    break
                service.append_output(terminal_id, data)
                ws = _terminal_ws.get(terminal_id)
                if ws:
                    try:
                        await ws.send_text(data)
                    except Exception:
                        _terminal_ws.pop(terminal_id, None)
        else:
            # Existing PTY logic
            pty = service.get_pty(terminal_id)
            while True:
                data = await loop.run_in_executor(
                    _pty_executor, lambda: pty.read(blocking=True)
                )
                if not data:
                    buf = service.get_buffered_output(terminal_id)
                    _save_recording(terminal_id, buf)
                    service.mark_closed(terminal_id)
                    ws = _terminal_ws.pop(terminal_id, None)
                    if ws:
                        try:
                            await ws.close(code=1000, reason="Terminal session ended")
                        except Exception:
                            pass
                    break
                service.append_output(terminal_id, data)
                ws = _terminal_ws.get(terminal_id)
                if ws:
                    try:
                        await ws.send_text(data)
                    except Exception:
                        _terminal_ws.pop(terminal_id, None)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.warning("Terminal reader error for %s", terminal_id, exc_info=True)
    finally:
        _terminal_readers.pop(terminal_id, None)
```

---

## Task 3: ClaudeCodeExecutor.run_streaming()

**Files:** Modify `backend/app/hooks/executor.py`

### Step 1: Aggiungere import

```python
from typing import Awaitable, Callable
```

### Step 2: Nuovo metodo run_streaming

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
    if tool_guidance:
        prompt = tool_guidance + "\n\n" + prompt

    env = os.environ.copy()
    env.setdefault("MANAGER_AI_PROJECT_ID", os.environ.get("MANAGER_AI_PROJECT_ID", ""))
    env.setdefault("MANAGER_AI_BASE_URL", os.environ.get("MANAGER_AI_BASE_URL", "http://localhost:8000"))
    if env_vars:
        env.update(env_vars)

    cmd = ["claude", "-p", "--allowedTools", "mcp__ManagerAi__*"]
    cwd = project_path or None
    prompt_bytes = prompt.encode()
    start = time.monotonic()

    def _run() -> tuple[int, bytes, bytes]:
        popen_kwargs: dict = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "cwd": cwd,
            "env": env,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd, **popen_kwargs)
        return proc  # Return proc for streaming

    # ... (streaming logic with line-by-line read + on_output callback, accumulate stdout, return ExecutorResult)
```

Il thread worker legge `proc.stdout.readline()` in loop, chiama callback via `asyncio.run_coroutine_threadsafe` per ogni linea, accumula per ExecutorResult finale. Gestisce timeout con `_terminate_tree`.

---

## Task 4: AgentStepRun model — terminal_id

**Files:** Modify `backend/app/models/pipeline.py`

### Step 1: Aggiungere colonna

```python
terminal_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, default=None)
```

### Step 2: Creare migration Alembic

```bash
cd backend && python -m alembic revision --autogenerate -m "add terminal_id to agent_step_runs"
python -m alembic upgrade head
```

---

## Task 5: AgentStepRunResponse schema — terminal_id

**Files:** Modify `backend/app/schemas/pipeline.py`

### Step 1: Aggiungere campo

```python
class AgentStepRunResponse(BaseModel):
    # ... existing fields ...
    terminal_id: str | None = None
```

---

## Task 6: POST /api/terminals/log endpoint

**Files:** Modify `backend/app/routers/terminals.py`, `backend/app/schemas/terminal.py`

### Step 1: Schema LogTerminalCreate

In `backend/app/schemas/terminal.py`:
```python
class LogTerminalCreate(BaseModel):
    project_id: str
    issue_id: str
    label: str = ""
```

### Step 2: Endpoint

```python
@router.post("/log", response_model=TerminalResponse, status_code=201)
async def create_log_terminal(
    data: LogTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        project_path = await get_project_path(data.project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    terminal = await service.create_log(
        project_id=data.project_id,
        issue_id=data.issue_id,
        project_path=project_path,
        label=data.label,
    )
    _ensure_reader(terminal["id"], service)
    return TerminalResponse(**terminal)
```

---

## Task 7: OrchestratorService._run_agent_step() — integrazione log

**Files:** Modify `backend/app/services/orchestrator_service.py`

### Step 1: Import terminal_service

```python
from app.services.terminal_service import terminal_service
```

### Step 2: Modificare _run_agent_step

Dopo `step.status = AgentStepStatus.RUNNING` e prima di chiamare executor:

```python
# Create log terminal for live output
project_path = project.path if project else ""
log_term = await terminal_service.create_log(
    project_id=resolved_project_id,
    issue_id=pipeline_run.issue_id or "",
    project_path=project_path,
    label=agent.name,
)
step.terminal_id = log_term["id"]
await self._commit()

await self._emit("agent_terminal_created", pipeline_run, step, project_id=resolved_project_id)

# Streaming callback
async def on_output(text: str) -> None:
    await terminal_service.push_output(log_term["id"], text)

result = await self.executor.run_streaming(
    prompt=prompt,
    project_path=project_path,
    env_vars={
        "MANAGER_AI_PROJECT_ID": agent.project_id,
        "MANAGER_AI_AGENT_NAME": agent.name,
        "MANAGER_AI_AGENT_ROLE": agent.role_key,
    },
    on_output=on_output,
)

# Destroy log terminal after step completes
await terminal_service.destroy_log(log_term["id"])
```

---

## Task 8: TerminalPanel readOnly prop

**Files:** Modify `frontend/src/features/terminals/components/terminal-panel.tsx`

### Step 1: Aggiungere prop

```tsx
interface TerminalPanelProps {
  terminalId: string;
  projectId: string;
  readOnly?: boolean;
  onSessionEnd?: () => void;
  onDownloadRecording?: () => void;
}
```

### Step 2: Quando readOnly=true

- Non registrare `term.onData()` (wrap in `if (!readOnly)`)
- Non mostrare pulsanti Files e Voice nella toolbar
- Mantenere Copy, Search, Download Log
- Mantenere resize

Toolbar condizionale:
```tsx
{!readOnly && (
  <>
    <Button ... onClick={() => setGalleryOpen(true)}>
      <Images className="size-3 mr-1" /> Files
    </Button>
    <Button ... onClick={() => setSpeechOpen(true)}>
      <Mic className="size-3 mr-1" /> Voice
    </Button>
  </>
)}
```

---

## Task 9: API client — createLogTerminal hook

**Files:** Modify `frontend/src/features/terminals/hooks.ts`

### Step 1: Aggiungere hook

Nell'hook file esistente (o nuovo file api se diverso):

```tsx
export function useCreateLogTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { projectId: string; issueId: string; label: string }) => {
      const res = await api.post("/api/terminals/log", data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["terminals"] });
    },
  });
}
```

---

## Task 10: IssueDetail — Agent Terminal tab

**Files:** Modify `frontend/src/features/issues/components/issue-detail.tsx`

### Step 1: Aggiungere tab alla lista

```tsx
const tabs = useMemo<TabDef[]>(() => [
  // ... existing tabs ...
  { value: "agent-terminal", label: "Agent Terminal", available: !!runningStep?.terminal_id },
], [/* ... existing deps ... */, runningStep?.terminal_id]);
```

### Step 2: Aggiungere TabsContent

```tsx
<TabsContent value="agent-terminal" className="mt-4">
  {runningStep?.terminal_id && (
    <div className="h-[500px] border border-zinc-700 rounded-md overflow-hidden">
      <TerminalPanel
        readOnly={true}
        terminalId={runningStep.terminal_id}
        projectId={projectId}
      />
    </div>
  )}
</TabsContent>
```

### Step 3: Auto-aprire tab quando terminal_id appare

Quando `runningStep?.terminal_id` diventa disponibile dopo l'evento `agent_terminal_created`, il tab appare automaticamente. Opzionalmente auto-selezionarlo:

```tsx
useEffect(() => {
  if (runningStep?.terminal_id) {
    setActiveTab("agent-terminal");
  }
}, [runningStep?.terminal_id]);
```

---

## Task 11: EventContext — agent_terminal_created

**Files:** Modify `frontend/src/shared/context/event-context.tsx`

### Step 1: Aggiungere a eventi silent

```tsx
case "agent_terminal_created":
  return { title: "", message: "", variant: "default", silent: true };
```

### Step 2: Aggiungere query invalidation

Nel blocco `ws.onmessage`, dopo gli altri `if (data.type === ...)`:

```tsx
if (data.type === "agent_terminal_created") {
  if (data.project_id && data.issue_id) {
    queryClient.invalidateQueries({
      queryKey: ["projects", data.project_id, "issues", data.issue_id, "pipeline-runs"],
    });
  }
}
```

---

## Ordine di esecuzione

1. Task 1: TerminalService log mode
2. Task 2: _terminal_reader log mode
3. Task 3: ClaudeCodeExecutor.run_streaming()
4. Task 4: AgentStepRun.terminal_id model + migration
5. Task 5: AgentStepRunResponse schema
6. Task 6: POST /api/terminals/log endpoint
7. Task 7: OrchestratorService integrazione
8. Task 8: TerminalPanel readOnly
9. Task 9: API hook createLogTerminal
10. Task 10: IssueDetail Agent Terminal tab
11. Task 11: EventContext handler
