# Specifica: Notifiche Telegram dirette via Bot API (senza Hermes CLI)

## Problema

L'attuale sistema di notifiche Telegram (`NotificationService`) spawna un subprocesso `hermes send -q <msg> --to telegram` per inviare notifiche. Questo approccio ha diversi problemi:

1. **Bassa affidabilità**: Hermes CLI può fallire silenziosamente, non essere sul PATH, o scadere (timeout 30s)
2. **Nessun controllo diretto**: non possiamo verificare lo stato dell'invio, gestire errori, o implementare retry
3. **Dipendenza esterna**: il provider Hermes deve essere configurato e funzionante
4. **Debug difficile**: i log contengono solo il comando, non la risposta dell'API Telegram
5. **Latenza**: spawnare un subprocesso Python ha overhead significativo per ogni notifica

## Soluzione

Sostituire l'invio via Hermes CLI con chiamate dirette alle Telegram Bot API via **httpx** (già presente come dipendenza di FastAPI).

### 1. Configurazione (Settings)

Aggiungere a `Settings` in `backend/app/config.py`:

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | `None` | Token del bot Telegram (da @BotFather) |
| `TELEGRAM_CHAT_ID` | `None` | Chat ID di default per le notifiche |

Caricate da `.env`. Se non configurate, le notifiche Telegram sono disabilitate (si può mantenere il fallback opzionale su Hermes CLI).

### 2. Nuovo servizio: `TelegramService`

Creare `backend/app/services/telegram_service.py`:

- Usa **httpx.AsyncClient** per chiamare `https://api.telegram.org/bot{token}/sendMessage`
- Metodo `send_message(text: str, chat_id: str | None = None)`:
  - Usa `chat_id` se fornito, altrimenti il default da Settings
  - parse_mode: HTML (per formattazione)
  - Timeout 15s (le notifiche devono essere veloci)
  - Logging strutturato: evento inviato, ID messaggio, chat_id
  - **Non propagare eccezioni** — EventService non deve bloccarsi
- Metodo `is_configured() -> bool`: ritorna True se token e chat_id sono impostati
- Rate limiting: max 20 messaggi/sec (limite Bot API), usa asyncio.sleep se necessario

### 3. Nuovo notifier: `TelegramNotifier`

Creare `backend/app/services/telegram_notifier.py`:

- Estende `BaseNotifier` (stessa interfaccia di NotificationService)
- Si registra su EventService nel costruttore
- `notify(event)`: ascolta eventi come `NotificationService` esistente:
  - `issue_status_changed` con `new_status=Finished`
  - `question_asked`
  - Altri eventi futuri (estendibile)
- Formatta messaggi nello stesso stile dell'attuale (`✅ Issue completata`, `❓ Domanda in attesa`, etc.)
- **Se Telegram non è configurato**: non fa nulla (silenzioso, non crasha)

### 4. Modifiche a `NotificationService` esistente

Lasciare `NotificationService` come fallback opzionale:
- Se `TelegramService.is_configured()` è True, `NotificationService` salta l'invio (per evitare duplicati)
- Se è False, NotificationService funziona come prima (Hermes CLI)
- Questo garantisce backward compatibility

### 5. Registrazione in startup

In `backend/app/main.py`:
```python
from app.services.telegram_notifier import TelegramNotifier
_ = TelegramNotifier()  # register as event listener
```

### 6. Installazione dipendenze

Non sono necessarie nuove dipendenze — httpx è già incluso in FastAPI/uvicorn.

## Criteri di accettazione

1. Le notifiche Telegram arrivano direttamente via Bot API, senza spawnare Hermes CLI
2. Se TELEGRAM_BOT_TOKEN non è configurato, non ci sono crash — le notifiche Hermes CLI continuano a funzionare
3. I messaggi sono formattati nello stesso modo di prima (✅ project, 📌 issue, 📝 descrizione, 💬 recap)
4. Il logging è strutturato e tracciabile: evento, chat_id, message_id, success/failure
5. Timeout rapido (15s) con retry automatico (1 tentativo extra dopo 2s)
