# Specifica: Rimozione Feature Agenti & Pipeline

## Obiettivo

Rimuovere completamente dalla codebase la feature degli agenti con pipeline, inclusi modelli, servizi, router, MCP tools, frontend, test e tabelle database.

## Cosa Rimuovere

### File da Eliminare Interamente (14)

**Backend (10):**
- `backend/app/models/agent.py` — modello SQLAlchemy `Agent`
- `backend/app/models/agent_message.py` — modello SQLAlchemy `AgentMessage`
- `backend/app/models/pipeline.py` — modelli `Pipeline`, `PipelineRun`, `AgentStepRun` + enum
- `backend/app/schemas/agent.py` — schemi Pydantic `AgentCreate`, `AgentUpdate`, `AgentResponse`
- `backend/app/schemas/agent_message.py` — schemi `AgentMessageCreate`, `AgentMessageResponse`
- `backend/app/schemas/pipeline.py` — schemi per pipeline, pipeline run, step run
- `backend/app/routers/agents.py` — router FastAPI CRUD agenti
- `backend/app/routers/pipelines.py` — router FastAPI CRUD pipeline
- `backend/app/services/orchestrator_service.py` — orchestratore esecuzione pipeline (565 righe)
- `backend/app/hooks/executor.py` — `ClaudeCodeExecutor`, usato solo dall'orchestratore

**Test (1):**
- `backend/tests/test_orchestrator.py` — 1203 righe di test su agenti e pipeline

**Frontend (6 — intera directory `features/agents/`):**
- `frontend/src/features/agents/api.ts` — API client e tipi TypeScript
- `frontend/src/features/agents/hooks.ts` — React Query hooks
- `frontend/src/features/agents/components/agents-section.tsx` — UI gestione agenti
- `frontend/src/features/agents/components/pipelines-section.tsx` — UI gestione pipeline
- `frontend/src/features/agents/components/pipeline-progress.tsx` — progresso pipeline
- `frontend/src/features/agents/components/agent-chat.tsx` — chat messaggi agenti

### File da Modificare Chirurgicamente (16)

**Backend (7):**
1. `backend/app/models/__init__.py` — rimuovere import ed export di Agent, AgentMessage, AgentStepRun, Pipeline, PipelineRun
2. `backend/app/main.py` — rimuovere import router agents/pipelines, registrazione router, cleanup zombie runs
3. `backend/app/routers/issues.py` — rimuovere endpoint `POST /{issue_id}/start-pipeline` e import OrchestratorService
4. `backend/app/routers/library.py` — rimuovere 4 endpoint agenti (GET `/agents`, GET `/agents/{name}`, POST `/agents`, PUT `/agents/{name}`)
5. `backend/app/services/skill_library_service.py` — rimuovere rami `agent` type, tenere solo `skill` type
6. `backend/app/mcp/server.py` — rimuovere ~12 MCP tools (list/create/update/delete agent, list/create/update/delete pipeline, send_agent_message, get_agent_messages, complete_agent_step, start_pipeline, get_pipeline_status)
7. `backend/app/mcp/default_settings.json` — rimuovere descrizioni MCP tools per agenti/pipeline

**Frontend (9):**
8. `frontend/src/features/issues/components/issue-detail.tsx` — rimuovere tab pipeline/agent/chat, badge stato pipeline, import components agenti
9. `frontend/src/features/issues/components/issue-actions.tsx` — rimuovere pulsante Start Pipeline e hook correlati
10. `frontend/src/features/projects/components/project-settings-dialog.tsx` — rimuovere import e rendering AgentsSection, PipelinesSection
11. `frontend/src/shared/context/event-context.tsx` — rimuovere handler eventi SSE agent_step_*, pipeline_*
12. `frontend/src/features/library/api.ts` — rimuovere funzioni API agenti
13. `frontend/src/features/library/hooks.ts` — rimuovere hook useAgents, useAgentDetail
14. `frontend/src/routes/library.tsx` — rimuovere riferimenti ad agenti
15. `frontend/src/features/projects/components/library-tab.tsx` — rimuovere fetch e rendering agenti
16. `frontend/src/features/agents/` — directory interamente rimossa (vedi sopra)

## Migrazione Database

Nuova migration Alembic per droppare 5 tabelle nell'ordine corretto FK:
1. `agent_step_runs`
2. `pipeline_runs`
3. `pipelines`
4. `agent_messages`
5. `agents`

Da eseguire dopo il revert delle due migration esistenti (`072a542ac08c` e `3ed109d6a415`) oppure creare una nuova migration che droppa direttamente le tabelle.

## Verifica

- `python -m pytest` passa (escluso test_orchestrator.py rimosso)
- `npm run build` frontend compila senza errori
- Nessun riferimento ad `agent`, `pipeline`, `orchestrator` rimane nel codice (al di fuori di nomi file o contesti non correlati)
- `python start.py` avvia correttamente