Creare un sistema di notifiche Telegram automatiche via Hermes quando un'issue viene completata (portata in status FINISHED) su Manager AI.

Il sistema deve:

1. **Polling periodico**: Un cron job Hermes che ogni 5-10 minuti controlla se ci sono nuove issue passate a FINISHED. Deve tenere traccia dell'ultimo check per non notificare due volte la stessa issue.

2. **Contenuto notifica**: Per ogni issue completata, inviare un messaggio Telegram via Hermes (send_message) contenente:
   - Nome del progetto
   - Nome e ID dell'issue
   - Descrizione breve
   - Recap (se presente) o numero di task completati
   - Link/URI all'issue nella web UI di Manager AI

3. **Scoping**: Funzionare su TUTTI i progetti, non solo su Manager AI stesso. Il cron job deve scorrere tutti i progetti attivi e controllare le issue completate in ciascuno.

4. **Stato tracking**: Salvare un timestamp o un segnalibro dell'ultimo check (via file JSON o memoria semplice) per evitare notifiche duplicate.

5. **Configurabile**: Parametri modificabili: interval (default 5 min), progetti da includere/escludere, formato del messaggio.

6. **Implementazione**: Script Python che:
   - Carica progetti e issue via REST API su localhost:8001
   - Confronta con un file di stato (ultimo check timestamp + già-notificati)
   - Invia notifiche Telegram via send_message di Hermes
   - Può essere eseguito come cron job Hermes (no_agent=false) o come script periodico

Requisiti:
- Usa l'API HTTP di Manager AI (localhost:8001) per listare progetti e issue
- Tracking via file JSON in ~/AppData/Local/hermes/scripts/notification_state.json
- Resiliente: se l'API non risponde, logga errore e riprova al prossimo tick
- Messaggio Telegram in italiano, chiaro e ben formattato

Esempio di notifica:
```
✅ Issue Completata — Manager AI

📌 Miglioramenti autenticazione JWT
🆔 #42
📋 Implementata validazione token scaduti + refresh token rotation
🏷️ Status: FINISHED (3/3 task completati)
```