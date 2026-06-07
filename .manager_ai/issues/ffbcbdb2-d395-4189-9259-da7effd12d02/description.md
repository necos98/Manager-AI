11. mcp/server.py — find_task O(n) ripetuto 3 volte

  update_task_status (linea 436-442), update_task_name (492-498), delete_task (523-529) — stesso scan progetti
  copy-paste.
  Fix: Estrarre _find_task_issue(task_id) come utility.