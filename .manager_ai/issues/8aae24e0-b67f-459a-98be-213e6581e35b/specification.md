# Test Flusso MCA - Hermes Orchestrator

## Obiettivo
Verificare il funzionamento completo del flusso Manager AI tramite Hermes Orchestrator MCP, testando:
1. Connessione e chiamate MCP orchestrator
2. Issue lifecycle completo (New → Reasoning → Planned → Accepted → Finished)
3. Pipeline orchestrata con controllo manuale degli step
4. Avanzamento step con `start_pipeline_step` / `advance_pipeline`
5. Completamento con `finished_pipeline_step` + recap

## Specifica del Test

### Fase 1: Issue Lifecycle via MCP
- Usare `get_issue_details`, `get_issue_status` per verificare lo stato iniziale
- Scrivere specifica, piano, task atomic via MCP tools
- Verificare transizioni di stato: New → Reasoning → Planned → Accepted

### Fase 2: Pipeline Orchestrata
- Creare 2 agent di test: **WriterAgent** (scrive un file di verifica) e **CheckerAgent** (verifica il file)
- Creare pipeline con questi 2 step in modalità orchestrata
- Eseguire `run_pipeline` con `orchestrated=true`
- Per ogni step: `start_pipeline_step` → attendere completamento Claude Code → `finished_pipeline_step` → `advance_pipeline`

### Fase 3: Completamento
- Dopo l'ultimo step, verificare che la pipeline sia completa
- Scrivere recap e completare la issue con `complete_issue`

## Criteri di Successo
- Ogni MCP tool dell'orchestrator risponde correttamente
- Le transizioni di stato rispettano la macchina a stati: NEW → REASONING → PLANNED → ACCEPTED → FINISHED
- La pipeline orchestrata avanza correttamente step per step
- Claude Code viene spawnato correttamente per ogni step
- I messaggi degli agent sono tracciabili via `get_pipeline_messages`
- Il recap finale è salvato e accessibile
