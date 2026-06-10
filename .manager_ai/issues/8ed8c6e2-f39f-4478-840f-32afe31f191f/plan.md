## Piano di implementazione: Logging dedicato per NotificationService

### Task 1 — Aggiungere _setup_notification_logger() a NotificationService
Creare un metodo statico `_setup_notification_logger()` che:
- Ottiene il path assoluto di `backend/logs/` risolvendo rispetto al file corrente
- Crea la directory se non esiste (os.makedirs(exist_ok=True))
- Configura un logger Python dedicato con nome `NotificationFileLogger`
- Aggiunge un `logging.FileHandler(notifications_log_path, mode='a', encoding='utf-8')`
- Imposta un `logging.Formatter` con formato `[%(asctime)s] NOTIFICA | %(event_type)s | Issue: %(issue_name)s | Progetto: %(project_name)s | Messaggio: %(message)s` e datefmt `%Y-%m-%d %H:%M:%S`
- Log level INFO
- Restituisce il logger configurato

### Task 2 — Inizializzare il logger in __init__ e chiamarlo nei metodi notify
- In `__init__`, chiamare `self._setup_notification_logger()` e salvare il logger come `self._notification_logger`
- In `_notify_issue_finished()`, dopo aver costruito il message, chiamare `self._notification_logger.info(..., extra={...})` con event_type, issue_name, project_name, e il messaggio troncato a 200 caratteri
- In `_notify_question_asked()`, stesso pattern
