3. mcp/server.py:163-178 — Hook ISSUE_COMPLETED chiamato DUE volte

  complete_issue MCP tool chiama issue_service.complete_issue() (che già chiama
  hook_registry.fire(HookEvent.ISSUE_COMPLETED)) e poi chiama di nuovo lo stesso hook. L'hook viene eseguito due volte.