## Recap: Logging dedicato per NotificationService in notifications.log

Aggiunto sistema di logging su file dedicato per NotificationService.

### Cosa è stato fatto

1. **`_setup_notification_logger()`** — metodo statico che configura un logger Python dedicato (`NotificationFileLogger`) con `logging.FileHandler` in append mode su `backend/logs/notifications.log`. La directory viene creata se non esiste. Il logger ha `propagate = False` per evitare duplicazione sul root logger.

2. **Integrazione in `__init__`** — chiama `self._setup_notification_logger()` e salva il logger come `self._notification_logger`.

3. **`_notify_issue_finished()`** — dopo aver costruito il messaggio Hermes, scrive una riga nel log con event_type="issue_finished", issue_name, project_name e il messaggio troncato a 200 caratteri.

4. **`_notify_question_asked()`** — stesso pattern con event_type="question_asked".

### Formato log
```
[2026-06-09 20:00:00] NOTIFICA | issue_finished | Issue: Nome Issue | Progetto: Nome Progetto | Messaggio: Testo notifica...
```

### Test
Verificato con import test: 2 scritture in append mode confermate, formato corretto, encoding utf-8 ok.

### File modificato
- `backend/app/services/notification_service.py`