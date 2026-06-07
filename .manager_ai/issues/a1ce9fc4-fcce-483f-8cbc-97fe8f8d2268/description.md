 6. mcp/server.py — 1438 righe, duplicazione massiccia

  - Serializzazione agent ripetuta 4 volte identica
  - Serializzazione pipeline ripetuta 6+ volte identica
  - issue.name or (issue.description or "")[:50] or "" ripetuto 15+ volte
  - Pattern async with async_session() → crea service → try/except AppError → commit → emit ripetuto in ogni tool
  - Fix: Estrarre decorator @mcp_tool_wrapper, funzioni _serialize_agent(), _serialize_pipeline(), _issue_display_name()