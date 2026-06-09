# Pipeline Flow — Analisi Logica Completa

## Manager AI Pipeline System

> Data: 18 Giugno 2026
> Progetto: Manager AI
> Versione analisi: Backend services/pipeline_run/ + models + providers
>
> Ultimo aggiornamento: Fix evento PRIMA del commit in FAILURE branch,
>   cancel_run con WS emit + event engine, nuovo MCP tool cancel_pipeline.

---

## 1. Cos'è una Pipeline

Una **pipeline** in Manager AI è una sequenza ordinata di **step**, ognuno dei quali
associa un **agente** (un ruolo AI) a un **intent** (cosa deve fare quell'agente).

La pipeline automatizza il flusso di lavoro multi-agente: crea una issue, la pipeline
spawna gli agenti uno dopo l'altro, ognuno completa il suo compito e passa il testimone
al successivo, fino al completamento.

```
┌─────────────────────────────────────────────────────────┐
│                    PIPELINE                               │
│                                                           │
│  Step 0        Step 1        Step 2        Step 3         │
│ ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐       │
│ │Agent A │──▶│Agent B │──▶│Agent C │──▶│Agent D │──▶ DONE│
│ │Intent  │   │Intent  │   │Intent  │   │Intent  │       │
│ │  ...   │   │  ...   │   │  ...   │   │  ...   │       │
│ └────────┘   └────────┘   └────────┘   └────────┘       │
│                                                           │
│  Rifiuto (rejected) ◀─────── ritorno allo step N          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Modello Dati — Entità e Relazioni

### 2.1 Agente (`Agent`)

```python
Agent:
  id: str           # UUID primario
  name: str         # Nome leggibile: "SpecWriter", "Developer"
  model: str|null   # Modello LLM opzionale
  allowed_tools: list|null  # Tool MCP consentiti
  intent: str       # Istruzione primaria: cosa deve fare l'agente
```

### 2.2 Pipeline (`Pipeline`)

```python
Pipeline:
  id: str           # UUID primario
  name: str         # Nome: "Default Pipeline", "Feature Pipeline"
  # Relazioni:
  steps: []         # PipelineStep — step ordinati
  runs: []          # PipelineRun — esecuzioni passate/presenti
  event_rules: []   # PipelineEventRule — regole di eventi automatici
```

### 2.3 Step di Pipeline (`PipelineStep`)

```python
PipelineStep:
  id: str           # UUID primario
  pipeline_id: str  # FK → Pipeline
  agent_id: str     # FK → Agent (quale agente esegue questo step)
  order_index: int  # Ordine nella pipeline (0, 1, 2, ...)
```

### 2.4 Esecuzione di Pipeline (`PipelineRun`)

```python
PipelineRun:
  id: str                   # UUID primario
  pipeline_id: str          # FK → Pipeline
  issue_id: str             # Issue associata (non FK — stringa)
  status: RUNNING | WAITING_FOR_STEP | PAUSED | COMPLETED | FAILED
  current_step_index: int   # Indice dello step corrente
  rejection_count: int      # Conteggio rifiuti (massimo 3)
  started_at: datetime      # Inizio esecuzione
  finished_at: datetime     # Fine esecuzione
```

### 2.5 Esecuzione di Step (`PipelineStepRun`)

```python
PipelineStepRun:
  id: str                   # UUID primario
  pipeline_run_id: str      # FK → PipelineRun
  pipeline_step_id: str     # FK → PipelineStep
  terminal_id: str|null     # PTY terminal associato (se attivo)
  status: PENDING | RUNNING | COMPLETED | FAILED | REJECTED
  started_at: datetime
  finished_at: datetime
```

### 2.6 Messaggio di Pipeline (`PipelineMessage`)

```python
PipelineMessage:
  id: str                   # UUID primario
  pipeline_run_id: str      # FK → PipelineRun
  sender_agent_name: str    # Nome agente mittente
  content: text             # Contenuto dell'handoff
  created_at: datetime
```

### 2.7 Regola Evento (`PipelineEventRule`)

```python
PipelineEventRule:
  id: str
  pipeline_id: str          # FK → Pipeline
  event_type: str           # step_completed | step_rejected | step_failed | pipeline_completed
  source_step_id: str       # FK → PipelineStep (da quale step)
  target_step_id: str       # FK → PipelineStep (per quale step)
  action_type: str          # set_issue_status | emit_event
  action_params: dict|null  # Parametri specifici dell'azione
  enabled: bool
```

### 2.8 Log di Pipeline (`PipelineLog`)

```python
PipelineLog:
  id: int                   # Auto-increment
  uuid: str                 # UUID univoco
  pipeline_run_id: int
  step_run_id: int|null
  level: str                # INFO, WARN, ERROR
  source: str               # Modulo sorgente
  message: text
  details: text             # JSON con dettagli
  created_at: datetime
```

---

## 3. Flusso di Esecuzione — Passo per Passo

### 3.1 Avvio — `run_pipeline` → `start()`

```
UTENTE/ORCHESTRATOR        MCP (orchestrator)         BACKEND
      │                          │                       │
      │  run_pipeline()          │                       │
      │─────────────────────────▶│                       │
      │                          │  PipelineRunService   │
      │                          │  .start()             │
      │                          │──────────────────────▶│
      │                          │                       │
      │                          │  [1] Guard:           │
      │                          │  controlla che non    │
      │                          │  esista già un RUN    │
      │                          │  attivo per issue     │
      │                          │                       │
      │                          │  [2] Carica Pipeline  │
      │                          │  con steps + agenti   │
      │                          │                       │
      │                          │  [3] Crea PipelineRun │
      │                          │  → status=RUNNING     │
      │                          │  → current_step=0     │
      │                          │                       │
      │                          │  [4] Per ogni step:   │
      │                          │  crea PipelineStepRun │
      │                          │  → status=PENDING     │
      │                          │                       │
      │                          │  [5] asyncio          │
      │                          │  .create_task(        │
      │                          │    _execution.execute │
      │                          │  )                    │
      │                          │  registra in          │
      │                          │  PipelineTaskManager  │
      │                          │                       │
      │                          │  [6] commit DB        │
      │                          │  → RUN persiste       │
      │                          │                       │
      │  ◀──── run details ──────│                       │
```

**Punti chiave:**
- L'esecuzione è un **task asincrono** (`asyncio.create_task`) lanciato in background
- `PipelineTaskManager` tiene traccia dei task attivi per cleanup/cancellazione
- Il commit avviene **dopo** aver creato il task, ma `_wait_for_run` lo aspetta

### 3.2 Loop Principale — `_execution.execute()`

```
  execute(run_id, project_id, project_path, session)
       │
       ▼
  _wait_for_run(run_id, session)
       │
       │  Attende fino a 5s che il commit del chiamante
       │  completi, poi carica Pipeline con steps ordinati
       │
       ▼
  while current_step_index < len(steps) AND status != FAILED:
       │
       │  ┌──────────────────────────────────────────────┐
       ├──│ _setup_step_environment(step, run, ...)       │
       │  └──────────────────────────────────────────────┘
       │   1. Trova PipelineStepRun per questo step
       │   2. Setta status=RUNNING, started_at=now()
       │   3. Carica Project (per shell, wsl_distro)
       │   4. Crea PTY terminal → terminal_service.create()
       │   5. Associa terminal_id allo step_run
       │   6. Se WSL → emette cd nel PTY
       │   7. Emette eventi WebSocket: step_started, terminal_created
       │
       │  ┌──────────────────────────────────────────────┐
       ├──│ _run_step(term_id, agent_name, intent, ...)   │
       │  └──────────────────────────────────────────────┘
       │   1. Ottiene il PTY e crea TerminalSession
       │   2. Risolve provider (da SettingsService "agent_provider")
       │   3. provider.build_run_pipeline_commands(issue_id)
       │   4. Per ogni comando: pty.write(cmd + "\r\n")
       │   5. Registra asyncio.Event per completamento
       │   6. asyncio.wait( [pty_death, completion_event] )
       │   7. Se PTY muore prima di completion → FAILED
       │   8. Se completion_event → SUCCESS
       │
       │  ┌──────────────────────────────────────────────┐
       ├──│ _handle_step_completion(run, step_run, ...)   │
       │  └──────────────────────────────────────────────┘
       │   SUCCESS →
       │     step_run.status = COMPLETED
       │     current_step_index += 1
       │     step_run.finished_at = now()  — nel caller dopo il ritorno
       │     emit step_completed (WS)
       │     fire_pipeline_event("step_completed")
       │     → continue (next step)
       │
       │   FAILURE →
       │     step_run.status = FAILED
       │     run.status = FAILED
       │     step_run.finished_at = now()
       │     fire_pipeline_event("step_failed")  — PRIMA del commit
       │     emit step_failed (WS)
       │     → break (pipeline termina)
       │
       ▼
  _finalize_run(run, session, ...)
       │
       │  Se run non è già FAILED → status = COMPLETED
       │  run.finished_at = now()
       │  fire_pipeline_event("pipeline_completed")  — PRIMA del commit
       │  commit  — unico commit atomico: stato pipeline + modifiche event engine
       │  emit pipeline_completed (WS)
```

### 3.3 Meccanismo di Completamento — `_completion.py`

Il cuore della sincronizzazione tra il processo esterno (agente spawnato nel PTY)
e il loop di esecuzione backend:

```
  BACKEND _execute loop          AGENTE NEL PTY
         │                             │
         │  pty.write(cmd + "\r\n")    │
         │────────────────────────────▶│
         │                             │  (agente lavora...)
         │                             │
         │  asyncio.Event.wait()       │
         │  (bloccato in attesa)       │
         │                             │
         │                             │  finished_pipeline_step()
         │                             │  via MCP tool
         │                             │────────────────────▶ MCP SERVER
         │                                                 │
         │                    set_step_completed(run, idx) │
         │◀────────────────────────────────────────────────│
         │  event.set() → wait si sblocca                 │
         │                                                 │
         │  asyncio.wait() → SUCCESS                       │
```

**Struttura dati chiave** — un dizionario globale:
```python
_completion_events: dict[tuple[str, int], asyncio.Event]
#                      (run_id, step_index) -> Event
```

Ogni step registra un `asyncio.Event` prima di scrivere comandi nel PTY.
L'agente remoto, quando finisce, chiama `finished_pipeline_step` via MCP,
che setta l'evento. Il loop si sblocca e avanza.

### 3.4 Rifiuto / Reiezione — `_rejection.py`

Quando un agente chiama `finished_pipeline_step(rejected=True, ...)`:

```
  [1] Trova il PipelineStepRun corrente (status=RUNNING)
  [2] Lo marca come REJECTED
  [3] Risolve target_step_index:
        - Se fornito dall'agente: lo usa direttamente
        - Se non fornito: cerca PipelineEventRule per questo step
          con event_type="step_rejected" → usa target_step_id della regola
  [4] Crea un NUOVO PipelineStepRun per lo step target → status=RUNNING
  [5] Aggiorna current_step_index = target_step_index
  [6] Incrementa rejection_count
  [7] Se rejection_count >= 3 → run.status = FAILED
  [8] Salva PipelineMessage di notifica
  [9] Emette evento WS: pipeline_step_rejected
  [10] Fire evento event engine: "step_rejected"
  [11] Commit DB
  [12] Segnala _completion per far sbloccare _execute loop → riparte
```

**Logica di regressione:**
- L'agente corrente viene interrotto
- La pipeline torna indietro allo step target
- Tutti gli step successivi al target vengono rieseguiti (la pipeline si resetta da lì)
- Il rejection_count tiene traccia per evitare loop infiniti (max 3)

---

## 4. Provider System — Come Vengono Spawnati gli Agenti

### 4.1 Architettura

```
  AgentProvider (ABC)
       │
       ├── ClaudeProvider("claude")
       │     build_run_pipeline_commands()
       │       → ["claude -dsp \"/run-pipeline iss-xxx\""]
       │
       └── HermesProvider("hermes")
             build_run_pipeline_commands()
               → ["hermes chat --skills run-pipeline --worktree --yolo",
                  "Execute pipeline step for issue iss-xxx"]
```

### 4.2 Flusso di Spawn (in `_run_step`)

```
  [1] Legge "agent_provider" da SettingsService
  [2] AgentProviderRegistry.get(provider_name)
  [3] commands = provider.build_run_pipeline_commands(issue_id)
  [4] Per ogni comando in commands:
        pty.write(command + "\r\n")
```

**Claude:** 1 comando — usa slash command `/run-pipeline`
**Hermes:** 2 comandi — avvia `hermes chat` con skill `run-pipeline`, poi invia messaggio iniziale

---

## 5. Event Engine — Azioni Automatiche

### 5.1 Tipi di Evento

| Event Type | Quando si attiva |
|---|---|
| `step_completed` | Uno step pipeline termina con successo |
| `step_rejected` | Uno step pipeline viene rifiutato |
| `step_failed` | Uno step pipeline fallisce |
| `pipeline_completed` | L'intera pipeline termina (successo o fallimento) |

### 5.2 Azioni Registrate

| Action | Parametri | Cosa fa |
|---|---|---|
| `set_issue_status` | `{status: "FINISHED"}` | Cambia stato della issue |
| `emit_event` | `{event_type: "...", ...}` | Emette un WebSocket event custom |

### 5.3 Registro Azioni

Il sistema è **estendibile** — si aggiungono nuove action decorando funzioni:

```python
@register_action("nome_azione")
async def my_action(context, params, session):
    ...
```

### 5.4 Flusso di Attivazione

```
  _handle_step_completion() / reject_step() / _finalize_run()
       │
       fire_pipeline_event(type, source_step_id, context)
       │
       ▼
  _events_engine.fire_event(pipeline_id, event_type, ...)
       │
       ▼
  Query DB: PipelineEventRule dove
    pipeline_id == X AND
    event_type == Y AND
    enabled == True
    [Se source_step_id != None: matcha anche source_step_id == Z]
       │
       ▼
  Per ogni regola trovata:
    handler = ACTION_REGISTRY[rule.action_type]
    await handler(context, rule.action_params, session)
       │
       ├── set_issue_status → modifica status issue
       └── emit_event → invia WebSocket event
```

**Sequenza critica** (dal memory):
> `fire_pipeline_event` DEVE avvenire PRIMA di `safe_commit`.
> Se l'action handler fallisce dopo il commit, lo stato della pipeline
> è committato ma la issue non ha cambiato status → inconsistenza.

**Nota su `source_step_id`:** Nel modello `PipelineEventRule`, `source_step_id` è
`NOT NULL` (non possono esistere regole wildcard). Quando `fire_event` viene
chiamato con `source_step_id=None` (evento `pipeline_completed`), la condizione
sulla colonna viene **omessa** dalla query — matchano TUTTE le regole per
quell'event_type, indipendentemente dal loro `source_step_id`.

---

## 6. WebSocket Events Emessi

| Evento | Quando | Payload |
|---|---|---|
| `agent_step_started` | Step inizia | project_id, issue_id, agent_name, step_run_id, terminal_id |
| `terminal_created` | PTY creato | terminal_id, issue_id, project_id |
| `agent_step_completed` | Step completato | project_id, issue_id, agent_name, step_run_id |
| `agent_step_failed` | Step fallito | project_id, issue_id, agent_name, step_run_id |
| `pipeline_step_rejected` | Step rifiutato | project_id, issue_id, run_id, step_run_id, agent_name, reason, target_step_index, rejection_count |
| `pipeline_step_advanced` | Pipeline avanza | run_id, issue_id, from_step, to_step, status |
| `pipeline_completed` | Pipeline finita | project_id, issue_id, run_id, status |
| `pipeline_paused` | Pipeline in pausa | run_id, issue_id |
| `pipeline_resumed` | Pipeline ripresa | run_id, issue_id |

---

## 7. Ciclo di Vita Completo di un PipelineRun

```
                        RUN_PIPELINE chiamato
                              │
                              ▼
                          RUNNING
                      current_step = 0
                              │
                              ▼
                 ┌─────────────────────┐
                 │ SETUP STEP N        │
                 │ PTY creato          │
                 │ step_run = RUNNING  │
                 └────────┬────────────┘
                          │
                          ▼
                 ┌─────────────────────┐
                 │ _run_step(term)     │
                 │ attende completion  │◀──────────────────┐
                 └────────┬────────────┘                   │
                          │                                │
                    ┌─────┴─────┐                         │
                    │           │                          │
                 COMPLETED   REJECTED ─── torna a step M ──┘
                    │           │
                    │      rejection_count >= 3
                    │           │
                    │           ▼
                    │        FAILED
                    │
               current_step+1
                    │
              ┌─────┴─────┐
              │           │
         altri step    fine step
              │           │
              ▼           ▼
           RUNNING     COMPLETED

PAUSED ◀─── da RUNNING/WAITING_FOR_STEP
    │
    └──▶ RESUME → WAITING_FOR_STEP (poi riprende)

CANCEL da RUNNING → FAILED + cleanup terminale + cancel task
                   + fire_pipeline_event("pipeline_completed") + WS emit
```

---

## 8. Gestione Errori e Cancellazione

### 8.1 Errore durante step

Catturato dal `try/except` in `execute()` — ma anche il branch FAILURE
esplicito di `_handle_step_completion` segue lo stesso ordine:

```
  1. step_run.status = FAILED
  2. run.status = FAILED
  3. step_run.finished_at = now()
  4. Fire event engine "step_failed"    ← PRIMA del commit
  5. Emit step_failed WS
  6. Cleanup terminale
  7. _finalize_run → setta COMPLETED/FAILED + commit finale atomico
```

### 8.2 Cancellazione (pause/cancel)

```
  pause_run → uccide terminale attivo → cancella task → PAUSED
              (nessun event engine — solo WS emit)

  cancel_run → uccide terminale attivo → cancella task → FAILED
               + fire_pipeline_event("pipeline_completed")  ← PRIMA del flush
               + WS emit pipeline_completed

  CancelledError → risale senza loggare → task manager fa cleanup
```

**Novità (Fix 18 Giu 2026):** `cancel_run` ora emette sia l'evento
`pipeline_completed` all'event engine (triggerando regole come
`set_issue_status`) sia il WebSocket event `pipeline_completed`.
Prima la cancellazione era silenziosa per frontend ed event rules.

### 8.3 Rescue Session

Le operazioni DB nella pipeline usano `safe_commit()` / `safe_flush()`:
- Tentano commit → se fallisce, rollbackano e riprovano
- `IntegrityError` e `OperationalError` NON vengono recuperati (rilanciati)

---

## 9. Architettura a Micro-Moduli

La pipeline è implementata come **facade** con moduli specializzati:

```
pipeline_run/
  __init__.py          # Export pubblico: PipelineRunService + set_step_completed + fire_pipeline_event
  service.py           # Facade: delega a tutti i sub-moduli
  _lifecycle.py        # start(), pause_run(), resume_run(), cancel_run()
  _execution.py        # execute() — loop principale auto-mode
  _completion.py       # asyncio.Event signaling per step completion
  _events.py           # WebSocket emissions + event engine wrapper
  _events_engine.py    # Event rules engine (fire_event, ACTION_REGISTRY)
  _messages.py         # CRUD pipeline messages (handoff agent→agent)
  _queries.py          # Read queries per pipeline runs
  _rejection.py        # Step rejection + regression logic
  _responses.py        # Serializzatori (dict builders)
  _safe_session.py     # Safe commit/flush helpers
  _terminal.py         # Terminal cleanup (deduplicato)
```

---

## 10. MCP Interface — Strumenti Orchestrator

Gli strumenti MCP esposti sul server orchestrator (`/mcp-orchestrator`):

| Tool | Descrizione |
|---|---|
| `run_pipeline` | Avvia pipeline → `PipelineRunService.start()` |
| `get_pipeline_run_status` | Stato corrente di un run |
| `get_active_agent` | Agente attualmente in esecuzione per una issue |
| `get_active_pipeline_run` | Run attivo per una issue |
| `send_agent_message` | Invia messaggio di handoff alla pipeline |
| `get_pipeline_messages` | Legge messaggi di handoff |
| `finished_pipeline_step` | Segnala completamento/rifiuto step |
| `pause_pipeline` | Mette in pausa |
| `resume_pipeline` | Riprende |
| `cancel_pipeline` | Annulla definitivamente (FAILED + eventi) |
| `add_pipeline_event_rule` | Aggiunge regola evento |
| `remove_pipeline_event_rule` | Rimuove regola evento |
| `list_pipeline_event_rules_tool` | Elenca regole |
| `update_pipeline_event_rule_tool` | Aggiorna regola |

---

## 11. Diagramma Riassuntivo — Flusso Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (Hermes via MCP)                    │
│                                                                     │
│  create_issue() → run_pipeline() → monitor → DONE                   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + asyncio)                       │
│                                                                      │
│  PipelineRunService.start()                                          │
│    ├── Crea PipelineRun (RUNNING)                                    │
│    ├── Crea PipelineStepRun (PENDING) per ogni step                  │
│    └── asyncio.create_task(execute())                                │
│                                                                      │
│  execute() loop:                                                     │
│    while steps left AND not FAILED:                                  │
│      ├── _setup_step_environment() → PTY + RUNNING                   │
│      ├── _run_step() → scrive comandi nel PTY + attende              │
│      ├── _handle_step_completion()                                   │
│      │   ├── SUCCESS → step COMPLETED, index++                       │
│      │   ├── REJECTED → torna indietro, rejection_count++            │
│      │   └── FAILED  → pipeline FAILED, break                        │
│      └── _finalize_run() → COMPLETED o FAILED                        │
│                                                                      │
│  Event Engine:                                                       │
│    in _handle_step_completion → fire_pipeline_event()                │
│      ├── step_completed  → set_issue_status("PLANNED")              │
│      ├── step_rejected   → (custom rules)                           │
│      ├── step_failed     → (custom rules)                           │
│      └── pipeline_completed → set_issue_status("FINISHED")          │
│                                                                      │
│  WebSocket: every state change → realtime event to frontend          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  PTY / TERMINALE (agente spawnato)                    │
│                                                                      │
│  Provider genera comandi:                                            │
│    Claude:  claude -dsp "/run-pipeline iss-xxx"                     │
│    Hermes:  hermes chat --skills run-pipeline --yolo                 │
│             Execute pipeline step for issue iss-xxx                  │
│                                                                      │
│  Agente:                                                             │
│    1. get_active_agent(issue_id) → scopre identità                   │
│    2. get_active_pipeline_run → contesto pipeline                    │
│    3. get_issue_details → dettagli issue                             │
│    4. get_pipeline_messages → handoff precedenti                     │
│    5. Esegue intent (spec/plan/implement/review)                     │
│    6. finished_pipeline_step(summary) → MCP -> set_completion_event  │
│    7. Esce (PTY muore)                                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 12. Glossario

| Termine | Definizione |
|---|---|
| **Pipeline** | Sequenza ordinata di step, ognuno con un agente |
| **Step** | Singolo passo nella pipeline (agente + intent) |
| **PipelineRun** | Una singola esecuzione di una pipeline |
| **PipelineStepRun** | Esecuzione di un singolo step in un run |
| **Agent** | Ruolo AI con nome e intent (SpecWriter, Developer, etc.) |
| **Intent** | Istruzione primaria per l'agente su cosa fare |
| **Handoff** | Messaggio di passaggio tra agenti (via PipelineMessage) |
| **Rejection** | Rifiuto del lavoro di uno step precedente, con regressione |
| **Event Rule** | Regola automatica che reagisce a eventi pipeline |
| **PTY** | Pseudo-terminale dove l'agente CLI viene spawnato |
| **Provider** | Sistema di generazione comandi (Claude Code, Hermes) |
| **Completion Event** | `asyncio.Event` che sincronizza loop backend con agente remoto |
| **Regression** | Tornare indietro nella pipeline a uno step precedente dopo rejection |

---

## Appendice A: Schema DB delle Pipeline

```
pipelines
  id (PK)
  name
  created_at
  updated_at

pipeline_steps
  id (PK)
  pipeline_id (FK → pipelines.id)
  agent_id (FK → agents.id)
  order_index
  UQ(pipeline_id, order_index)

pipeline_event_rules
  id (PK)
  pipeline_id (FK → pipelines.id)
  event_type
  source_step_id (FK → pipeline_steps.id)
  target_step_id (FK → pipeline_steps.id)
  action_type
  action_params (JSON)
  enabled
  UQ(pipeline_id, event_type, source_step_id)

pipeline_runs
  id (PK)
  pipeline_id (FK → pipelines.id)
  issue_id (string — non FK)
  status (ENUM)
  current_step_index
  rejection_count
  started_at
  finished_at
  created_at

pipeline_step_runs
  id (PK)
  pipeline_run_id (FK → pipeline_runs.id)
  pipeline_step_id (FK → pipeline_steps.id)
  terminal_id (nullable)
  status (ENUM)
  started_at
  finished_at

pipeline_messages
  id (PK)
  pipeline_run_id (FK → pipeline_runs.id)
  sender_agent_name
  content (TEXT)
  created_at

pipeline_logs
  id (PK auto)
  uuid (UQ)
  pipeline_run_id (FK → pipeline_runs.id)
  step_run_id (FK → pipeline_step_runs.id, nullable)
  level
  source
  message
  details (JSON text)
  created_at
```
