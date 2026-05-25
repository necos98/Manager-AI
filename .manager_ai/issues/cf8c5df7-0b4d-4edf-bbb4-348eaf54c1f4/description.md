Rimpiazzare il rilevamento di completamento step basato su marker stringa con exit code del subprocess e timeout configurabile.

## Problema
Attualmente il completamento di uno step viene rilevato cercando marker stringa (`__STEP_SUCCESS_xxx__` / `__STEP_FAILED_xxx__`) nel buffer del terminale. È fragile:
- Un echo accidentale del marker nel prompt rompe il detection
- Se DeepSeek fallisce una tool call, il marker non viene mai emesso e il loop pende per sempre
- Nessun timeout: una esecuzione bloccata = pipeline bloccata all'infinito

## Cosa fare
1. Rimuovere i marker stringa e il polling loop `while True: await asyncio.sleep(1)`
2. Usare l'exit code del subprocess per determinare successo/fallimento
3. Aggiungere timeout configurabile per step (default 15 minuti, override per agent role)
4. Aggiungere `AgentStepStatus.TIMED_OUT` come nuovo stato step
5. Su timeout: kill del subprocess + mark step come TIMED_OUT
6. Lo step si considera completato ANCHE se l'agente chiama `complete_agent_step` via MCP (lo stato su DB viene aggiornato asincronamente dal tool MCP, non dal polling)

## File interessati
- `backend/app/services/orchestrator_service.py` — `_run_agent_step()` (rimuovere righe 408-447, sostituire con logica exit code + timeout)
- `backend/app/models/pipeline.py` — aggiungere `TIMED_OUT` a `AgentStepStatus`
- `backend/app/models/pipeline.py` — aggiungere `timeout_seconds` a `Pipeline` o `Agent`

## Design notes
Il `complete_agent_step` MCP tool già aggiorna lo stato dello step a COMPLETED sul DB. L'orchestrator dovrebbe:
1. Avviare subprocess
2. Aspettare exit o timeout
3. Se exit code != 0 → FAILED
4. Se timeout → TIMED_OUT
5. Se exit code == 0 → COMPLETED (il MCP tool potrebbe aver già aggiornato, fare refresh prima di decidere)