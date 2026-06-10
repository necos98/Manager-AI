## Specifica — Test notifiche Telegram

**Obiettivo:** Verificare che il sistema di notifiche Telegram (NotificationService) invii correttamente una notifica "Issue completata" quando un'issue viene completata.

**Cosa fare:**
1. Creare un semplice file `test-telegram-notifica.txt` nella root del progetto con contenuto di verifica
2. Completare l'issue con un recap che confermi la notifica

**Criterio di successo:** L'utente riceve una notifica Telegram con il messaggio di completamento dell'issue.

**Non-goals:** Modificare codice, configurare notifiche, fixare bug.