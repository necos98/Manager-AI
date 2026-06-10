Notifiche Telegram arricchite con nome progetto, nome issue, descrizione (120 char) e recap (120 char). Modifiche:
- **shared_tools.py**: `force_finish_issue`, `complete_issue` e `ask_user_question` ora emettono eventi con `project_name`, `description`, `recap` e `issue_name`
- **notification_service.py**: `_notify_issue_finished` formatta messaggio con emoji ✅📌📝💬; `_notify_question_asked` formatta con emoji ❓📌💬
Il codice era già stato implementato, task segnati come completati.