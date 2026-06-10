## Recap: Notifiche Telegram dirette via Bot API

### Cosa è stato fatto

Sostituito l'invio di notifiche Telegram via Hermes CLI (`hermes send -q ... --to telegram`) con chiamate dirette alle Telegram Bot API via httpx.

### File creati

1. **`backend/app/services/telegram_service.py`** — Singleton httpx client per Bot API
   - `send_message(text, chat_id=None)` → POST a `api.telegram.org/bot{token}/sendMessage`
   - Rate limiting a 20 msg/sec (limite Bot API)
   - Retry automatico (1 tentativo dopo 2s su errori di rete)
   - Timeout 15s, parse_mode=HTML
   - Logging strutturato con chat_id, message_id
   - Non propaga eccezioni

2. **`backend/app/services/telegram_notifier.py`** — Event listener
   - Estende `BaseNotifier`, registrato su `EventService`
   - Ascolta `issue_status_changed` (Finished) e `question_asked`
   - Stessa formattazione messaggi di NotificationService (✅📌📝💬 / ❓📌💬)
   - Silenzioso se Telegram non configurato

### File modificati

3. **`backend/app/config.py`** — Aggiunti `telegram_bot_token` e `telegram_chat_id` (da .env)
4. **`backend/app/services/notification_service.py`** — Salta Hermes CLI se Telegram configurato (evita duplicati)
5. **`backend/app/main.py`** — Registrato `TelegramNotifier()` nella startup
6. **`.env.example`** — Aggiunta sezione Telegram

### Comportamento

- **Se `.env` ha TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID**: notifiche dirette via Bot API, Hermes CLI non viene chiamato
- **Se non configurato**: tutto funziona come prima (Hermes CLI fallback), zero crash
- **Durante startup**: log informativi che indicano se Telegram è configurato o meno