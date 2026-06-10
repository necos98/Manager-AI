## Recap

Rimosso il fallback Hermes CLI da NotificationService. NotificationService ora è puramente un file logger — scrive eventi su notifications.log ma non spawna più subprocess Hermes.

### Modifiche effettuate

**`backend/app/services/notification_service.py`:**
- Rimossa intera funzione `_run_hermes_command()` (35 righe di subprocess handling)
- Rimossa import di `HermesProvider` e `asyncio`
- Rimosse chiamate `await self._run_hermes_command(hermes_message)` da `_notify_issue_finished` e `_notify_question_asked`
- Rimosso campo `command` dal formato del log e dagli `extra` dict
- Aggiornate docstring per riflettere il nuovo scopo (solo file logging)

**`backend/app/providers/hermes_provider.py`:**
- Rimosso metodo `build_notification_command()` — era usato solo da NotificationService

### Non modificato
- `main.py` — NotificationService resta registrato in main.py per il file logging
- `TelegramNotifier` / `TelegramService` — gestiscono già le notifiche reali quando Telegram è configurato

### Verifica
- Syntax check: OK su entrambi i file
- Import test: NotificationService importabile, HermesProvider non ha più build_notification_command