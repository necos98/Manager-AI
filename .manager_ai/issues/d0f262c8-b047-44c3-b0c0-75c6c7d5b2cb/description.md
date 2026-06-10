Rimuovere il fallback su Hermes CLI in NotificationService

Attualmente in `backend/app/services/notification_service.py`:
- Se TelegramNotifier NON è configurato (nessun token/chat_id), NotificationService prova comunque a inviare notifiche via `hermes send` come fallback
- Questo significa che anche quando l'utente non ha configurato Telegram, il sistema tenta di inviare notifiche spawnando un subprocess Hermes

Cosa deve cambiare:
1. Se Telegram non è configurato → nessuna notifica, silenzio totale
2. Se Telegram è configurato → TelegramNotifier gestisce tutto (già funziona)
3. NotificationService deve essere rimosso o reso inerte (senza più chiamate a Hermes CLI)

File interessati:
- `backend/app/services/notification_service.py` — da modificare/rimuovere il `_run_hermes_command()` e relativo log
- `backend/app/providers/hermes_provider.py` — `build_notification_command()` può essere rimosso se non più usato altrove
- `backend/app/main.py` — riga 338: `_ = NotificationService()` da rimuovere se il servizio viene eliminato

Attenzione:
- `TelegramNotifier` fa già tutto il lavoro quando configurato
- Documentazione del servizio (docstring) parla di "Hermes CLI fallback"
- Non rompere il logging su file (notification.log) — da valutare se tenere solo il log

Note dal codice attuale:
- `notification_service.py` riga 84-86: `if telegram_service.is_configured(): return` — già esiste un check che disabilita NotificationService quando Telegram è configurato
- Manca: quando Telegram NON è configurato, NotificationService fa comunque `hermes send` — questo è il fallback da eliminare