# Arricchire notifiche Telegram con progetto, descrizione e recap

## Obiettivo

Arricchire le notifiche Telegram inviate da `NotificationService` via `hermes chat -q` includendo nome del progetto, descrizione e recap dell'issue, invece del messaggio minimale attuale "Issue {name} completata".

## Architettura

Il flusso è: **Tool MCP → EventService → NotificationService → Hermes CLI**.

1. **shared_tools.py**: Le funzioni `force_finish_issue`, `complete_issue` e `ask_user_question` emettono eventi via `_emit_event`. Devono includere `project_name`, `description`, `recap` e `issue_name` negli eventi.

2. **EventService**: Propaga l'evento a tutti i listener registrati (tra cui `NotificationService`).

3. **notification_service.py**: `NotificationService` ascolta `issue_status_changed` (quando `new_status == "Finished"`) e `question_asked`, costruisce un messaggio formattato con emoji e lo invia via `hermes chat -q --quiet`.

## Modifiche necessarie

### 1. `backend/app/mcp/shared_tools.py`

**`force_finish_issue`** — Aggiungere `project_name`, `description`, `recap` all'evento `issue_status_changed`:
- Eseguire `ProjectService(session).get_by_id(project_id)` per ottenere il nome del progetto
- Includere `project_name`, `issue.description`, `issue.recap` nell'evento

**`complete_issue`** — Stessa cosa:
- Eseguire `ProjectService(session).get_by_id(project_id)` per ottenere il nome del progetto
- Includere `project_name`, `issue.description`, `issue.recap` nell'evento

**`ask_user_question`** — Aggiungere `project_name` e `issue_name` all'evento `question_asked`:
- Spostare il lookup di `issue_name` e `project_name` PRIMA dell'emissione dell'evento (già fixato dal bug precedente)

### 2. `backend/app/services/notification_service.py`

**`_notify_issue_finished`** — Formattare messaggio ricco:
```
✅ Issue completata — Nome Progetto
📌 Nome dell'Issue
📝 Descrizione breve (primi 120 caratteri)
💬 Recap: riepilogo (primi 120 caratteri, se presente)
```

**`_notify_question_asked`** — Formattare messaggio ricco:
```
❓ Domanda in attesa — Nome Progetto
📌 Nome dell'Issue
💬 Testo della domanda (primi 200 caratteri)
```

### Considerazioni

- I campi `description` e `recap` sono opzionali — la notifica deve funzionare anche se assenti
- `hermes chat -q` è un subprocess one-shot — non serve `--max-turns`
- Gli errori di notifica non devono mai bloccare EventService (già gestito con try/except e log)
