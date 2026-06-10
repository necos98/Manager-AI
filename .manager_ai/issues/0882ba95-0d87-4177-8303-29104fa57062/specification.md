## Analisi del Problema

L'errore `'EventService' object has no attribute 'notify'` si verifica in `force_finish_issue_endpoint` (issues.py:159) perché il codice chiamava `event_service.notify(...)` ma `EventService` espone il metodo `emit()`, non `notify()`. `notify()` è un metodo di `BaseNotifier`/`WebSocketNotifier`, non del servizio centrale.

## Root Cause

`EventService` (in `event_service.py`) è un singleton che registra notificatori (`BaseNotifier` subclass). Il suo metodo è `emit()` che itera sui notificatori registrati e chiama `notifier.notify(event)` su ciascuno. Il router chiamava `event_service.notify()` direttamente, che non esiste.

## Fix Applicato (già in working tree)

1. **`backend/app/routers/issues.py`** — Aggiunta dispatch eventi `event_service.emit(...)` dopo `db.commit()` in:
   - `complete_issue()` — emette `issue_status_changed` con `new_status: FINISHED`
   - `force_finish_issue_endpoint()` — stessa emissione
   Con campi: `project_name`, `issue_name`, `description`, `recap`, `timestamp`

2. **`backend/app/mcp/shared_tools.py`** — Stessa correzione nei tool MCP:
   - `force_finish_issue()` — fix emissione eventi, aggiunti `project_name`, `description`, `recap`
   - `complete_issue()` — aggiunto `project_name`, `description`, `recap`
   - `ask_user_question()` — aggiunto `project_name` e `issue_name` al `question_asked` event, spostata emissione dopo la risoluzione dei campi

3. **`backend/app/providers/hermes_provider.py`** — Aggiunto `--max-turns 300` ai comandi hermes per pipeline/run-issue

4. **`backend/app/services/notification_service.py`** — Miglioramento messaggi Telegram: project name, description (120 char), recap (120 char) + log file dedicato

## Note

- `EventService` ha `emit()`, non `notify()` — questo è il pattern corretto
- `notify()` esiste solo su `BaseNotifier` / `WebSocketNotifier`, usato internamente da `EventService.emit()`
- La modifica è già presente nel working tree e va solo verificata e committata