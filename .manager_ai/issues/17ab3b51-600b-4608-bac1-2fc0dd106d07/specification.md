# Pipeline Run Bug Fix — Specification

## Root Cause Analysis

Tre bug concorrenti impediscono l'esecuzione corretta della pipeline:

### Bug 1: `_run_step()` usa `create_subprocess_shell` con stringa interpolata (CRITICAL)
- **File**: `backend/app/services/pipeline_run_service.py`, metodo `_run_step()` (line 230-242)
- **Problema**: Il comando `claude -p` viene costruito come stringa shell con interpolazione diretta del system prompt e del task. La shell (cmd.exe su Windows) interpreta caratteri speciali (doppi apici, `$`, backtick) rompendo il comando.
- **Confronto**: `enrich_context.py` usa già `create_subprocess_exec` con lista di argomenti — pattern funzionante da seguire.
- **Impatto**: Claude Code non viene mai lanciato correttamente. Terminale vuoto.

### Bug 2: Nessun evento WebSocket per cambi di stato step
- **File**: `backend/app/services/pipeline_run_service.py`, metodo `_execute()`
- **Problema**: Quando uno step passa da PENDING a RUNNING, e quando un terminale viene creato, nessun evento WebSocket viene emesso. Il frontend dipende esclusivamente dal polling ogni 2 secondi.
- **Impatto**: L'UI non reagisce immediatamente. L'utente deve rientrare nella issue per vedere i cambiamenti.

### Bug 3: `terminal_command` vuoto per tutti gli step di default
- **File**: `backend/app/services/pipeline_service.py`, metodo `seed_defaults()`
- **Problema**: Tutti gli step della pipeline default hanno `terminal_command=""`. Claude viene invocato senza un task specifico.
- **Impatto**: Anche quando Claude parte, non sa cosa fare e risponde con "What would you like me to do?".

## Fix Plan

### Fix 1: Rifattorizzare `_run_step()` per usare `create_subprocess_exec`
- Allineare con il pattern in `enrich_context.py`:
  ```python
  cmd = ["claude", "-p", prompt]
  proc = await asyncio.create_subprocess_exec(*cmd, ...)
  ```
- Passare stdout e stderr separatamente (non merged) per catturare errori.
- Mantenere lo streaming output tramite `push_output()` come già implementato.
- Rimuovere l'interpolazione shell — nessuna stringa costruita a mano.

### Fix 2: Emettere eventi WebSocket durante esecuzione step
- In `_execute()`, dopo aver creato il terminale e impostato `step_run.status = RUNNING`, emettere evento `agent_step_started` con `{step_run_id, terminal_id, agent_name}`.
- Alla fine di ogni step, emettere `agent_step_completed` o `agent_step_failed`.
- Questo permette al frontend di connettere il `TerminalPanel` immediatamente.

### Fix 3: Aggiungere `terminal_command` significativi per agent di default
- Ogni agent type deve avere un comando specifico:
  - **CodebaseExplorer**: esplora la codebase per capire il contesto dell'issue
  - **BrainstormingAgent**: fai brainstorming sui requisiti
  - **SpecWriter**: scrivi una specifica per l'issue
  - **PlanWriter**: crea un piano di implementazione
  - **Developer**: implementa il codice seguendo il piano
  - **Reviewer**: fai code review delle modifiche

### Fix 4: Frontend — gestione eventi WebSocket per pipeline
- Aggiungere listener per eventi `agent_step_started` nel `PipelineProgress` component.
- Auto-connettersi al WebSocket del terminale appena l'evento arriva, senza aspettare il prossimo polling.

## File da Modificare
1. `backend/app/services/pipeline_run_service.py` — Fix 1, Fix 2
2. `backend/app/services/pipeline_service.py` — Fix 3
3. `backend/app/routers/pipeline_runs.py` — Fix 2 (WebSocket endpoint o event broker)
4. `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx` — Fix 4
5. `frontend/src/features/pipeline-runs/hooks.ts` — Fix 4 (opzionale)

## Testing
- Avviare una pipeline e verificare che il terminale appaia immediatamente
- Verificare che Claude Code venga lanciato e produca output visibile
- Verificare che gli step avanzino correttamente (PENDING → RUNNING → COMPLETED)
- Verificare che il pulsante "Run Pipeline" sia disabilitato durante l'esecuzione
