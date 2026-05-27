## Implementation Plan

3 files to modify. All services already exist — just add MCP wrappers + descriptions + seed hook.

### Files
- **Modify:** `backend/app/mcp/default_settings.json` — add 8 description entries
- **Modify:** `backend/app/mcp/server.py` — add 8 MCP tool functions (~150 lines)
- **Modify:** `backend/app/services/project_service.py` — add 2 seed calls after flush

### Pattern
Every MCP tool follows existing pattern:
```python
@mcp.tool(description=_desc["tool.X.description"])
async def X(...) -> dict:
    async with async_session() as session:
        svc = SomeService(session)
        try:
            result = await svc.method(...)
            await session.commit()
            return {...}
        except AppError as e:
            return {"error": e.message}
```

### Tasks (7 total)

1. Add 8 tool descriptions to default_settings.json
2. Add create_agent + list_agents MCP tools
3. Add create_pipeline + list_pipelines MCP tools
4. Add run_pipeline MCP tool
5. Add get_pipeline_run_status MCP tool
6. Add send_agent_message + get_pipeline_messages MCP tools
7. Add seed_defaults calls to ProjectService.create()
