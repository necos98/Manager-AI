## Root Cause

Tre bug impedivano l'esecuzione della pipeline:

1. **`_run_step()` usava `create_subprocess_shell`** con stringa interpolata. Caratteri speciali nel system prompt rompevano il comando shell. Claude non veniva mai lanciato.

2. **Nessun evento WebSocket** veniva emesso durante l'esecuzione degli step. Il frontend usava solo polling (2s), quindi il terminale non appariva immediatamente.

3. **`terminal_command` vuoto** per tutti gli agent di default. Claude riceveva un task vuoto.

## Changes Made

### 1. `backend/app/services/pipeline_run_service.py`
- Sostituito `create_subprocess_shell` con `create_subprocess_exec` (allineato con pattern `enrich_context.py`)
- Prompt passato come argomento diretto (`["claude", "-p", prompt]`), non interpolato in stringa shell
- Aggiunto `drain_stderr()` per loggare errori stderr separatamente
- Aggiunti eventi WebSocket: `agent_step_started`, `agent_step_completed`, `agent_step_failed`, `pipeline_completed`

### 2. `backend/app/services/agent_service.py`
- Aggiunto `terminal_command` a tutti i `DEFAULT_AGENTS`

### 3. `backend/app/services/pipeline_service.py`
- `seed_defaults()` ora legge `terminal_command` da `DEFAULT_AGENTS` e lo imposta sui `PipelineStep`

### 4. `frontend/src/features/pipeline-runs/components/PipelineProgress.tsx`
- Aggiunta subscription agli eventi `agent_step_started` per selezionare immediatamente lo step running
- Il terminale si connette subito senza aspettare il polling
