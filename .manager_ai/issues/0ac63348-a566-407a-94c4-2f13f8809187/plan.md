# Piano di Implementazione: Notifiche Telegram dirette via Bot API

## Task 1: Aggiungere configurazione Telegram a Settings
**File**: `backend/app/config.py`
- Aggiungere `TELEGRAM_BOT_TOKEN: str | None = None`  
- Aggiungere `TELEGRAM_CHAT_ID: str | None = None`
- Caricate automaticamente da `.env` via pydantic-settings

## Task 2: Creare TelegramService (httpx client per Bot API)
**Nuovo file**: `backend/app/services/telegram_service.py`
- Classe `TelegramService` singleton con `httpx.AsyncClient`
- Metodo `send_message(text, chat_id=None)`: POST a `sendMessage` con parse_mode="HTML"
- Metodo `is_configured()`: True se token e chat_id sono impostati
- Retry automatico (1 tentativo extra dopo 2s su errore di rete)
- Timeout 15s
- Logging strutturato con chat_id, message_id, success/failure
- Rate limiting a 20 msg/sec (asyncio.sleep se necessario)
- Non propaga eccezioni (EventService non deve bloccarsi)

## Task 3: Creare TelegramNotifier (event listener)
**Nuovo file**: `backend/app/services/telegram_notifier.py`
- Estende `BaseNotifier`, si registra su EventService nel `__init__`
- `notify(event)`: ascolta `issue_status_changed` (Finished) e `question_asked`
- Formatta messaggi nello stesso stile dell'attuale NotificationService
- Se Telegram non è configurato, non fa nulla

## Task 4: Modificare NotificationService per evitare duplicati
**File**: `backend/app/services/notification_service.py`
- Importare `TelegramService`
- In `_handle_event`: se `TelegramService.is_configured()` è True, saltare l'invio Hermes CLI
- Se non configurato, comportamento invariato (fallback Hermes CLI)

## Task 5: Registrare TelegramNotifier in startup
**File**: `backend/app/main.py`
- Aggiungere `from app.services.telegram_notifier import TelegramNotifier`
- Aggiungere `_ = TelegramNotifier()` nella startup (dopo NotificationService)
