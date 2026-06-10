## Recap

**Problema**: `EventService` non ha un metodo `notify()` — il metodo corretto è `emit()`. L'errore si verificava in `force_finish_issue_endpoint` (issues.py:159) che veniva chiamato con `event_service.notify()`.

**Radice**: `EventService` (singleton, in `event_service.py`) ha `emit()`, che itera sui notificatori registrati e chiama `notifier.notify(event)` su ciascuno. Il router chiamava il metodo sbagliato.

**Fix** (commit `78be618`):
- **routers/issues.py**: Aggiunte emissioni eventi `issue_status_changed` dopo `db.commit()` in `complete_issue()` e `force_finish_issue_endpoint()` — mancavano del tutto
- **shared_tools.py**: Stessa correzione nei tool MCP `force_finish_issue()`, `complete_issue()`, più fix in `ask_user_question()` dove `issue_name` e `project_name` mancavano dall'evento `question_asked`
- **notification_service.py**: Messaggi Telegram arricchiti con project name, description (120 char), recap (120 char) + log file dedicato `backend/logs/notifications.log`
- **hermes_provider.py**: Aggiunto `--max-turns 300` per prevenire terminazione prematura degli agenti

**Verificato**: sintassi OK, import senza circular dependency, backend attivo su porta 8001 risponde correttamente.