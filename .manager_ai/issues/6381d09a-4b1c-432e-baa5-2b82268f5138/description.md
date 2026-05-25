Migliorare la gestione degli errori negli step della pipeline e aggiungere logica di retry configurabile.

## Problema
- L'errore registrato è generico: "Claude process exited with non-zero code or terminal closed" — non dice cosa è successo davvero
- Stderr del subprocess viene perso
- Nessun meccanismo di retry: se DeepSeek sbaglia una tool call (probabile, tool calling "Limited-Good"), l'intera pipeline va in PAUSED
- DeepSeek V4-Pro ha tool calling meno affidabile di Claude nativo — i fallimenti vanno gestiti con retry, non con abort

## Cosa fare
1. Catturare stderr del subprocess e salvarlo in `AgentStepRun.error`
2. Aggiungere `retry_count` e `max_retries` a `AgentStepRun`
3. In `_run_pipeline()`, se uno step fallisce:
   - Se `retry_count < max_retries` → re-run dello step (con backoff esponenziale)
   - Se `retry_count >= max_retries` → PAUSED (comportamento attuale)
4. Aggiungere `max_retries` configurabile per agent role (default 1 retry)
5. Migliorare i log dell'orchestrator con dettaglio errore
6. Inviare evento WebSocket `agent_step_retry` quando un retry parte

## File interessati
- `backend/app/services/orchestrator_service.py` — `_run_pipeline()` e `_run_agent_step()`
- `backend/app/models/pipeline.py` — `AgentStepRun` (aggiungere `retry_count`, `max_retries`)

## Note
Il retry NON deve ripartire da zero: il summary MCP e i messaggi agent chat dello step fallito sono disponibili e possono essere passati al retry come contesto.