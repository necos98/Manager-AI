Rimpiazzare l'uso di PTY terminal in `OrchestratorService._run_agent_step()` con un subprocess diretto.

## Problema
Attualmente ogni step della pipeline crea un PTY terminale (`terminal_service.create()`) per lanciare `claude -p`. Il PTY è pensato per sessioni interattive, non per esecuzione one-shot di un comando. Aggiunge overhead inutile e complessità.

## Cosa fare
- Rimuovere `terminal_service.create()` da `_run_agent_step()`
- Usare `asyncio.create_subprocess_exec` per lanciare `claude -p`
- Mantenere lo streaming dell'output verso il frontend usando il pattern "log terminal" già esistente (`terminal_service.create_log()` + `asyncio.Queue`)
- Il log terminal va creato prima di spawnare il subprocess, e l'output stdout/stderr del subprocess va pushato nella coda via `terminal_service.push_output()`

## File interessati
- `backend/app/services/orchestrator_service.py` — metodo `_run_agent_step()` (righe 331-473)
- `backend/app/services/terminal_service.py` — già supporta log mode, verificare compatibilità

## Pattern di riferimento
Memory `996bfe7f`: log terminal con `asyncio.Queue`, reader loop, sentinel `None` per EOF. `ClaudeCodeExecutor.run_streaming()` in `backend/app/hooks/executor.py` fa già bridge thread-async per stdout subprocess.