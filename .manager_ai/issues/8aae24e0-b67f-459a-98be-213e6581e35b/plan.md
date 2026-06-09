# Piano di Implementazione — Test Flusso MCA - Hermes Orchestrator

## Fase 1: Creazione Agenti di Test
Creare 2 agent via `create_agent`:
- **WriterAgent**: scrive file `.manager_ai/test-orchestrator-writer.txt` con data e timestamp
- **CheckerAgent**: verifica che il file esista e legga il contenuto

## Fase 2: Creazione Pipeline Orchestrata
Creare pipeline con i 2 agent (WriterAgent → CheckerAgent) usando `create_pipeline`
Avviare la pipeline in modalità orchestrata con `run_pipeline(project_id, pipeline_id, issue_id, orchestrated=true)`

## Fase 3: Esecuzione Step 1 — WriterAgent
- `start_pipeline_step` per avviare WriterAgent
- Attendere che Claude Code completi la scrittura del file di verifica
- Chiamare `finished_pipeline_step` per segnalare completamento
- Chiamare `advance_pipeline` per passare allo step successivo

## Fase 4: Esecuzione Step 2 — CheckerAgent
- `start_pipeline_step` per avviare CheckerAgent
- Attendere che Claude Code verifichi il file
- Chiamare `finished_pipeline_step` per segnalare completamento
- Chiamare `advance_pipeline` per completare la pipeline

## Fase 5: Verifica e Completamento
- Verificare che la pipeline sia in stato COMPLETED
- Verificare i messaggi degli agent via `get_pipeline_messages`
- Scrivere recap finale e chiamare `complete_issue`
