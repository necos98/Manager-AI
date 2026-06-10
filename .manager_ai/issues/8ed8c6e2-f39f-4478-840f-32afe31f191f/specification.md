## Specifica: Logging dedicato per NotificationService in notifications.log

### Obiettivo
Aggiungere un sistema di logging dedicato su file per NotificationService. Ogni notifica inviata (issue completata o domanda) deve essere registrata in `backend/logs/notifications.log` con timestamp, tipo evento, nome issue, nome progetto e messaggio inviato a Hermes.

### Formato log (una riga per notifica)
```
[2026-06-09 20:00:00] NOTIFICA | TipoEvento | Issue: Nome | Progetto: Nome | Messaggio: ...
```

### Approccio tecnico
Usare `logging.FileHandler` dedicato con un formatter custom:
- Creare una funzione `_setup_notification_logger()` in `notification_service.py` che configura un logger dedicato di nome `NotificationFileLogger` con un `FileHandler` in append mode puntato a `backend/logs/notifications.log`
- Il formatter produce il formato richiesto: `[%(asctime)s] NOTIFICA | %(event_type)s | Issue: %(issue_name)s | Progetto: %(project_name)s | Messaggio: %(message)s`
- Attivare il logger in fase `__init__` di NotificationService

### Dettagli implementativi
1. **Percorso log**: `backend/logs/notifications.log` — `backend/logs/` esiste già
2. **Append mode**: `FileHandler(mode='a')` — default, non sovrascrive a ogni riavvio
3. **Formato timestamp**: `%Y-%m-%d %H:%M:%S` (come da specifica)
4. **Campi per evento**:
   - `issue_finished`: event_type="issue_finished", issue_name, project_name, message (messaggio inviato a Hermes, troncato a 200 caratteri)
   - `question_asked`: event_type="question_asked", issue_name, project_name, message (messaggio inviato a Hermes, troncato a 200 caratteri)
5. **Rotazione**: non necessaria per ora — il file cresce linearmente. Il progetto ha già error logging con rotazione a 5 backup; eventuale rotazione futura per notifications.log può essere aggiunta separatamente
6. **Fallback**: se la directory `backend/logs/` non esiste, crearla automaticamente

### File da modificare
- `backend/app/services/notification_service.py` — unico file da modificare, aggiungere logging dedicato
