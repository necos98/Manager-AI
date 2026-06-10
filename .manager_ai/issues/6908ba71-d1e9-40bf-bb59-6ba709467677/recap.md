✅ Issue completata: UI Settings > Telegram con toggle e configurazione token/chat_id

## Cosa è stato fatto

**Backend:**
1. `default_settings.json` — Aggiunte 3 chiavi: `telegram.bot_token`, `telegram.chat_id`, `telegram.notifications_enabled` (default vuoto/false)
2. `telegram_service.py` — Aggiunto `_notifications_enabled`, metodo `configure(bot_token, chat_id, enabled)` per configurazione dinamica da DB, `is_configured()` ora verifica anche `_notifications_enabled`
3. `telegram_notifier.py` — `__init__` accetta parametri opzionali `bot_token`, `chat_id`, `notifications_enabled` e chiama `telegram_service.configure()`
4. `main.py` (lifespan) — Dopo TelegramNotifier(), legge i 3 setting dal DB via SettingsService e configura telegram_service. Se fallisce, fallback env.
5. `routers/settings.py` — Aggiunta funzione `_reconfigure_telegram()` che rilegge i 3 valori dal DB e li applica. Chiamata automaticamente quando un setting `telegram.*` viene aggiornato via PUT, per effetto immediato senza restart.

**Frontend:**
6. `settings.tsx` — Aggiunto tab "Telegram" con:
   - Status indicator 🟢/🔴 (configurato/non configurato)
   - Toggle "Notifiche Telegram attive" (auto-save)
   - Campo Bot Token con tipo password + toggle mostra/nascondi + bottone Salva
   - Campo Chat ID con bottone Salva

**Backward compatibilità:** Se le chiavi DB sono vuote, TelegramService cade sui valori `.env` esistenti. Se `notifications_enabled=false`, `is_configured()` torna False e NotificationService (Hermes CLI fallback) riparte automaticamente.