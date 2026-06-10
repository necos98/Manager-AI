# Piano di Implementazione

## Task 1: Aggiungere chiavi Telegram a default_settings.json
Aggiungere `telegram.bot_token`, `telegram.chat_id`, `telegram.notifications_enabled` con default vuoto/false.

## Task 2: Modificare TelegramService per supportare configurazione dinamica
- Aggiungere attributo `_notifications_enabled`
- Aggiungere metodo `configure(bot_token, chat_id, enabled)` per override dinamico
- Modificare `is_configured()` per includere `_notifications_enabled`

## Task 3: Modificare TelegramNotifier per ricevere config dal DB
- Aggiungere parametri opzionali `bot_token`, `chat_id`, `notifications_enabled` a `__init__`
- Chiamare `telegram_service.configure()` con questi valori

## Task 4: Aggiornare main.py (lifespan) per leggere config Telegram dal DB
- Dopo TelegramNotifier(), ottenere una sessione DB
- Leggere telegram.bot_token, telegram.chat_id, telegram.notifications_enabled via SettingsService
- Chiamare telegram_service.configure() con i valori letti

## Task 5: Aggiornare settings router per riconfigurare TelegramService in tempo reale
- In `update_setting` endpoint, dopo l'update se la chiave inizia con `telegram.`, rileggere tutti e 3 i valori dal DB e riconfigurare telegram_service

## Task 6: UI — Aggiungere tab Telegram in settings.tsx
- Aggiungere "Telegram" a TABS array
- Aggiungere regola getCategory() per chiavi `telegram.*`
- Creare componente TelegramSettingsPanel con toggle, input token/chat_id, status indicator
