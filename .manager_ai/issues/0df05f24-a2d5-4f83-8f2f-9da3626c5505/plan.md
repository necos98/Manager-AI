# Piano di implementazione: Notifiche Telegram arricchite

## Task 1: shared_tools.py — Aggiungere campo `project_name` a `force_finish_issue`
Eseguire `ProjectService(session).get_by_id(project_id)` e aggiungere `project_name`, `description`, `recap` all'evento `issue_status_changed`.

**Stato: ✅ FATTO**

## Task 2: shared_tools.py — Aggiungere campo `project_name` a `complete_issue`
Eseguire `ProjectService(session).get_by_id(project_id)` e aggiungere `project_name`, `description`, `recap` all'evento `issue_status_changed`.

**Stato: ✅ FATTO**

## Task 3: shared_tools.py — Aggiungere `project_name` e `issue_name` a `ask_user_question`
Spostare il calcolo di `issue_name` e `project_name` PRIMA dell'emissione di `question_asked` e includerli nell'evento.

**Stato: ✅ FATTO**

## Task 4: notification_service.py — Aggiornare `_notify_issue_finished`
Formattare messaggio con: progetto, issue, descrizione (120 char), recap (120 char, opzionale).

**Stato: ✅ FATTO**

## Task 5: notification_service.py — Aggiornare `_notify_question_asked`
Formattare messaggio con: progetto, issue, domanda (200 char).

**Stato: ✅ FATTO**

## Task 6: Verifica e test
- Verificare che i cambiamenti siano coerenti con il diff
- Eseguire i test esistenti per assicurarsi che nulla sia rotto

**Stato: Da fare**
