# Refactoring Plan — Manager AI Backend

Generated: 2026-06-07 18:59
Git commit: 745f495400805de1a3e63cb244f9f7a00e5ea3a4

## Fasi

### Fase 1: main.py → Modular Entry Point
- Crea `app/lifespan.py` con startup/shutdown handlers
- Crea `app/middleware_registry.py` per CORS + middleware custom
- Crea `app/router_registry.py` per registrazione router automatica
- Crea `app/mcp_setup.py` per mount MCP
- `main.py` diventa ~20 righe (solo orchestrazione)

### Fase 2: mcp/server.py → Separazione MCP Tools
- `mcp/tools/` moduli per dominio: `mcp/tools/tasks.py`, `mcp/tools/projects.py`, `mcp/tools/pipeline.py`
- `mcp/helpers.py` per boilerplate (session management, UUID validation, error handling)
- Server.py solo registrazione tools + FastMCP()

### Fase 3: services/ → Split in Servizi Focalizzati
- `pipeline_run_service.py` → `services/pipeline/` (orchestrator, executor, query, serializer)
- `issue_service.py` → `services/issue/` (crud, lifecycle, feedback, tags)

### Fase 4: routers/ → Clean Architecture
- `terminals.py` → estrarre logica WebSocket in `services/terminal_handler.py`
- `projects.py` → estrarre logica CRUD nei service esistenti
- `pipelines.py` → estrarre logica nei service esistenti

### Fase 5: Helper Condivisi
- `utils/` per decorators comuni, validazione UUID, response helpers

### Fase 6: Test
- Verifica tutti i test passano
- Aggiungi test per i nuovi moduli
