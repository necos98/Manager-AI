Aggiungere un sistema di logging dedicato per NotificationService.

Quando NotificationService invia una notifica (issue completata o domanda), scrivere un file di log con timestamp in backend/logs/notifications.log.

Formato del log (una riga per notifica):
[2026-06-09 20:00:00] NOTIFICA | TipoEvento | Issue: Nome | Progetto: Nome | Messaggio: ...

Il log deve includere:
- Timestamp
- Tipo di evento (issue_finished / question_asked)
- Nome dell'issue
- Nome del progetto
- Messaggio inviato a Hermes (troncato a 200 caratteri)

Il file notifications.log deve stare in backend/logs/. Append mode — non sovrascrivere a ogni avvio.

File da modificare:
backend/app/services/notification_service.py