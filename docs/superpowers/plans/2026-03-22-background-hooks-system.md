# Background Hooks System

## Summary

Sistema di hook in background che si agganciano alle transizioni di stato delle issue. Quando un evento del lifecycle accade (es. issue completata), il backend spawna processi Claude Code oneshot in background per eseguire operazioni automatiche.

## Decisioni di design

- **Dove vivono gli hook**: Nel backend Manager AI (centralizzato, non dipende dal client)
- **Esecuzione**: Claude Code CLI con accesso MCP (`claude -p "..." --allowedTools "mcp__ManagerAi__*"`)
- **Trigger supportati**: Solo transizioni di stato issue (completata, accettata, cancellata, declinata) — ma sistema modulare per espansione futura
- **Definizione hook**: Hardcoded in Python con decorator pattern
- **Notifiche**: Ogni hook emette eventi WebSocket (started/completed/failed) verso la UI

## Architettura

### Struttura file

```
backend/app/hooks/
├── __init__.py          # Esporta registry e decorator
├── registry.py          # HookRegistry + BaseHook + @hook decorator
├── executor.py          # ClaudeCodeExecutor — spawna Claude Code CLI
└── handlers/
    ├── __init__.py
    └── enrich_context.py  # Primo hook: arricchimento contesto progetto
```

### Componenti core

#### HookEvent (enum)

```python
class HookEvent(str, Enum):
    ISSUE_COMPLETED = "issue_completed"
    ISSUE_ACCEPTED = "issue_accepted"
    ISSUE_CANCELLED = "issue_cancelled"
    ISSUE_DECLINED = "issue_declined"
```

#### HookContext (dataclass)

```python
@dataclass
class HookContext:
    project_id: str
    issue_id: str
    event: HookEvent
    metadata: dict  # dati extra specifici per evento (es. recap per complete)
```

#### BaseHook (ABC)

```python
class BaseHook(ABC):
    name: str
    description: str

    @abstractmethod
    async def execute(self, context: HookContext) -> HookResult
```

#### HookRegistry (singleton)

```python
class HookRegistry:
    _hooks: dict[HookEvent, list[BaseHook]]

    def register(self, event: HookEvent, hook: BaseHook)
    async def fire(self, event: HookEvent, context: HookContext)
```

- `fire()` spawna ogni hook come task asyncio in background (non blocca la risposta MCP)
- Prima di eseguire ogni hook, emette evento WebSocket `hook_started`
- Al completamento: `hook_completed` o `hook_failed`

#### @hook decorator

```python
@hook(event=HookEvent.ISSUE_COMPLETED)
class EnrichProjectContext(BaseHook):
    ...
```

### ClaudeCodeExecutor

Componente riusabile per spawnare Claude Code CLI come processo async.

```python
class ClaudeCodeExecutor:
    async def run(
        self,
        prompt: str,
        project_path: str,
        env_vars: dict | None = None,
    ) -> ExecutorResult
```

- Costruisce: `claude -p "prompt..." --allowedTools "mcp__ManagerAi__*"`
- Inietta env vars (`MANAGER_AI_PROJECT_ID`, `MANAGER_AI_BASE_URL`)
- Spawna con `asyncio.create_subprocess_exec` nella project_path come cwd
- Cattura stdout/stderr
- Timeout configurabile (default: 5 minuti)
- Ritorna `ExecutorResult(success, output, error, duration)`

### Flusso di esecuzione

```
IssueService.complete_issue()
    → HookRegistry.fire(ISSUE_COMPLETED, context)
        → Per ogni hook registrato:
            → EventService.emit({type: "hook_started", hook_name, issue_id})
            → asyncio.create_task(hook.execute(context))
            → Al completamento: EventService.emit({type: "hook_completed", ...})
            → In caso di errore: EventService.emit({type: "hook_failed", ...})
```

## Primo Hook: EnrichProjectContext

### Trigger

`HookEvent.ISSUE_COMPLETED`

### Logica

1. Recupera dati issue (recap) e progetto (contesto attuale) dal HookContext
2. Spawna Claude Code CLI con prompt specifico
3. Claude analizza il recap e decide se aggiornare il contesto
4. Se necessario, chiama `update_project_context` (nuovo tool MCP)

### Prompt

```
La issue "{issue_name}" è stata appena completata nel progetto "{project_name}".

Recap della issue:
{recap}

Contesto attuale del progetto:
{project_description}
{tech_stack}

Il tuo compito:
1. Analizza il recap della issue appena completata
2. Determina se ci sono informazioni rilevanti che dovrebbero essere aggiunte al contesto del progetto (descrizione, tech stack)
3. Se sì, aggiorna il contesto usando i tool MCP disponibili
4. Se non ci sono informazioni rilevanti da aggiungere, non fare nulla

Aggiorna SOLO se la issue ha introdotto cambiamenti strutturali significativi
(nuove tecnologie, nuovi pattern architetturali, nuove integrazioni).
Non aggiungere dettagli specifici di singole issue.
```

## Nuovo tool MCP richiesto

### `update_project_context`

Permette di aggiornare `description` e/o `tech_stack` del progetto. Necessario perché attualmente `get_project_context` è read-only.

```python
@mcp.tool()
async def update_project_context(
    project_id: str,
    description: str | None = None,
    tech_stack: str | None = None,
) -> dict
```

## Riepilogo componenti

| Componente | Responsabilità |
|---|---|
| `HookEvent` enum | Definisce gli eventi supportati |
| `HookContext` dataclass | Trasporta i dati dell'evento |
| `BaseHook` ABC | Contratto per ogni hook |
| `HookRegistry` singleton | Registra e dispatcha hook, emette notifiche WebSocket |
| `@hook` decorator | Registrazione automatica |
| `ClaudeCodeExecutor` | Spawna Claude Code CLI come processo async (riusabile) |
| `EnrichProjectContext` | Primo hook: arricchisce il contesto post-issue |
| `update_project_context` | Nuovo tool MCP per scrivere nel contesto |

---

## Piano di implementazione

**Nota architetturale**: Gli hook vengono invocati nel layer MCP (`server.py`) **dopo il commit**, non nel service layer (che usa solo `flush()`). Questo garantisce che i dati siano persistiti prima che l'hook li legga.

### File da creare/modificare

| Azione | File | Responsabilità |
|--------|------|----------------|
| Crea | `backend/app/hooks/__init__.py` | Esporta registry, decorator, executor |
| Crea | `backend/app/hooks/registry.py` | HookEvent, HookContext, HookResult, BaseHook, HookRegistry, @hook |
| Crea | `backend/app/hooks/executor.py` | ClaudeCodeExecutor, ExecutorResult |
| Crea | `backend/app/hooks/handlers/__init__.py` | Import handlers per autodiscovery |
| Crea | `backend/app/hooks/handlers/enrich_context.py` | EnrichProjectContext hook |
| Modifica | `backend/app/mcp/server.py` | Aggiungere `update_project_context` tool + fire hook dopo commit |
| Modifica | `backend/app/main.py` | Inizializzare HookRegistry nel lifespan |

### Task 1: Core del Hook System (`registry.py`)

**File:** Crea `backend/app/hooks/registry.py`

- [ ] **Step 1**: Definire `HookEvent` enum con i 4 eventi (ISSUE_COMPLETED, ISSUE_ACCEPTED, ISSUE_CANCELLED, ISSUE_DECLINED)
- [ ] **Step 2**: Definire `HookContext` dataclass (project_id, issue_id, event, metadata)
- [ ] **Step 3**: Definire `HookResult` dataclass (success, output, error)
- [ ] **Step 4**: Definire `BaseHook` ABC con attributi `name`, `description` e metodo astratto `execute(context) -> HookResult`
- [ ] **Step 5**: Implementare `HookRegistry` con:
  - `_hooks: dict[HookEvent, list[type[BaseHook]]]`
  - `register(event, hook_class)` — aggiunge alla lista
  - `fire(event, context)` — per ogni hook: emette `hook_started` via EventService, spawna `asyncio.create_task` con wrapper che emette `hook_completed`/`hook_failed`
- [ ] **Step 6**: Implementare `@hook(event)` decorator che registra la classe nel registry
- [ ] **Step 7**: Creare istanza singleton `hook_registry = HookRegistry()`

### Task 2: Claude Code Executor (`executor.py`)

**File:** Crea `backend/app/hooks/executor.py`

- [ ] **Step 1**: Definire `ExecutorResult` dataclass (success, output, error, duration)
- [ ] **Step 2**: Implementare `ClaudeCodeExecutor` con metodo `async run(prompt, project_path, env_vars, timeout)`:
  - Costruisce comando: `claude -p "prompt" --allowedTools "mcp__ManagerAi__*"`
  - Inietta env vars di default (`MANAGER_AI_PROJECT_ID`, `MANAGER_AI_BASE_URL`) + eventuali extra
  - Spawna con `asyncio.create_subprocess_exec`, cwd=project_path
  - Cattura stdout/stderr con timeout (default 300s)
  - Ritorna `ExecutorResult`

### Task 3: Package init (`__init__.py`)

**File:** Crea `backend/app/hooks/__init__.py`

- [ ] **Step 1**: Esportare `hook_registry`, `HookEvent`, `HookContext`, `BaseHook`, `hook` decorator, `ClaudeCodeExecutor`

### Task 4: Primo handler — EnrichProjectContext

**File:** Crea `backend/app/hooks/handlers/__init__.py` e `backend/app/hooks/handlers/enrich_context.py`

- [ ] **Step 1**: In `handlers/__init__.py`, importare `enrich_context` (trigger autodiscovery del decorator)
- [ ] **Step 2**: In `enrich_context.py`, implementare `EnrichProjectContext(BaseHook)`:
  - `name = "enrich_project_context"`
  - `description = "Arricchisce il contesto del progetto dopo il completamento di una issue"`
  - `execute()`: costruisce il prompt con dati dal context.metadata (issue_name, recap, project_name, description, tech_stack), chiama `ClaudeCodeExecutor.run()`
- [ ] **Step 3**: Decorare con `@hook(event=HookEvent.ISSUE_COMPLETED)`

### Task 5: Tool MCP `update_project_context`

**File:** Modifica `backend/app/mcp/server.py`

- [ ] **Step 1**: Aggiungere tool `update_project_context(project_id, description?, tech_stack?)`:
  - Apre sessione async
  - Carica il progetto
  - Aggiorna solo i campi forniti (non-None)
  - Commit e ritorna il contesto aggiornato

### Task 6: Integrare hook nelle transizioni MCP

**File:** Modifica `backend/app/mcp/server.py`

- [ ] **Step 1**: Importare `hook_registry`, `HookEvent`, `HookContext`
- [ ] **Step 2**: In `complete_issue()` — dopo `session.commit()`, costruire `HookContext` con metadata (recap, issue_name, project info) e chiamare `await hook_registry.fire(HookEvent.ISSUE_COMPLETED, context)`
- [ ] **Step 3**: In `accept_issue()` — idem con `HookEvent.ISSUE_ACCEPTED`
- [ ] **Step 4**: In `decline_issue()` — idem con `HookEvent.ISSUE_DECLINED`
- [ ] **Step 5**: In `cancel_issue()` — idem con `HookEvent.ISSUE_CANCELLED`

### Task 7: Inizializzazione nel lifespan

**File:** Modifica `backend/app/main.py`

- [ ] **Step 1**: Importare `backend/app/hooks/handlers` nel lifespan (triggera i decorator e registra gli hook)
- [ ] **Step 2**: Log delle hook registrate all'avvio

### Task 8: Test manuale end-to-end

- [ ] **Step 1**: Avviare il backend
- [ ] **Step 2**: Completare una issue via MCP
- [ ] **Step 3**: Verificare che la notifica WebSocket `hook_started` arrivi al frontend
- [ ] **Step 4**: Verificare che Claude Code venga spawnato e termini correttamente
- [ ] **Step 5**: Verificare che la notifica `hook_completed` arrivi
