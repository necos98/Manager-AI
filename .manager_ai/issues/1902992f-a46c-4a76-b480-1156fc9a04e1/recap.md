## Recap: Agent Orchestration & Multi-Agent Chat System

All 11 tasks completed. 32/32 tests passing.

### What was built

**Backend (Python/FastAPI):**
- 4 new DB models: Agent, Pipeline, PipelineRun, AgentStepRun, AgentMessage
- Alembic migration for all new tables
- Pydantic schemas for all new models (create/update/response)
- CRUD MCP tools: list_agents, create_agent, update_agent, delete_agent, list_pipelines, create_pipeline, update_pipeline, delete_pipeline
- OrchestratorService: start_pipeline, _run_pipeline, _run_agent_step, build_prompt, complete_agent_step, get_pipeline_status, ensure_default_agents, ensure_default_pipeline
- Chat MCP tools: send_agent_message, get_agent_messages
- Execution MCP tools: start_pipeline, complete_agent_step, get_pipeline_status
- accept_issue integration: auto-starts default pipeline on issue acceptance (non-blocking on failure)
- WebSocket events: agent_step_started, agent_step_completed, agent_step_failed, agent_message_added, pipeline_completed

**Frontend (React/Vite):**
- AgentsTab: agent definitions table with CRUD (create/edit/delete modals, enabled toggle)
- PipelinesTab: pipeline list with drag-reorder steps, default toggle, CRUD operations
- AgentChat: scrollable chat panel on issue detail, WebSocket real-time updates, role-colored badges
- PipelineProgress: horizontal stepper with status colors (pending/running/completed/failed)
- API endpoints in api/agents.js, api/pipelines.js, api/agentMessages.js
- ProjectSettings updated with new tabs

**Default agents seeded per project:**
- Architect (role_key: architect) — system design and specs
- Developer (role_key: developer) — code implementation
- Reviewer (role_key: reviewer) — code review
- QA (role_key: qa) — testing and verification

**Tests (32 passing):**
- Model-level: agent creation, pipeline run creation, agent message send/read, step lifecycle, pipeline completion, step transitions
- MCP-level: agent CRUD (create/list/update/delete + not-found cases), pipeline CRUD (create default/non-default, list, update, delete)
- Execution: manual pipeline start (with/without default, bad issue), MCP start_pipeline, complete_agent_step (success + no running step), get_pipeline_status (success + not found)
- Integration: accept_issue auto-triggers pipeline with full verification of PipelineRun + AgentStepRuns