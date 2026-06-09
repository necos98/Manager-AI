# Implementato: `run_issue` sull'orchestrator

## Cosa è stato fatto

Aggiunto il tool MCP `run_issue` all'orchestrator server (`/mcp-orchestrator`).

## File creati/modificati

| File | Modifica |
|------|----------|
| `backend/app/services/run_issue_service.py` | **Nuovo** — logica: crea terminale, scrive comandi provider, emette eventi |
| `backend/app/mcp/shared_tools.py` | + funzione `run_issue()` che delega al service |
| `backend/app/mcp/orchestrator_server.py` | + import + tool `@orchestrator_mcp.tool()` |
| `hermes_skills/manager-ai-orchestrator/SKILL.md` | Aggiornata: rimosse limitation, aggiunto workflow `run_issue` |

## Architettura

```
Hermes (orchestrator AI)
  └─ run_issue(project_id, issue_id, provider_name?)
       └─ orchestrator_server.py (MCP tool)
            └─ shared_tools.run_issue()
                 └─ run_issue_service.run_issue()
                      ├─ Validates issue exists
                      ├─ terminal_service.create() → term_id
                      ├─ AgentProviderRegistry.get(provider).build_run_issue_commands(issue_id)
                      ├─ Writes commands to PTY
                      ├─ Emits WebSocket events (terminal_created, issue_run_started)
                      └─ Returns {term_id, status: "started"}
```

## Differenza da `run_pipeline`

| Aspetto | `run_pipeline` | `run_issue` |
|---------|---------------|-------------|
| Richiede pipeline+agenti | ✅ Sì | ❌ No |
| Multi-step orchestrato | ✅ Sì | ❌ No (single agent) |
| Crea record DB | PipelineRun + StepRun | Nessuno |
| Provider usato | Default config | Config o esplicito |
| Terminale | Creato per step | Creato subito |
| Ritorno | `{id, status, steps}` | `{term_id, status, provider}` |

## Provider supportati

I provider avevano già `build_run_issue_commands()` — nessuna modifica:

- **Claude**: `claude --dangerously-skip-permissions "/run-issue <id>"`
- **Hermes**: `hermes chat --skills run-issue --worktree --yolo` + messaggio
