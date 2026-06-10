Aggiungere una sezione "Telegram" nella pagina Settings dell'interfaccia web di Manager AI, dove l'utente può configurare:

1. **TELEGRAM_BOT_TOKEN** — campo di testo per il token del bot Telegram
2. **TELEGRAM_CHAT_ID** — campo di testo per il chat ID di default
3. **Toggle "Notifiche Telegram attive"** — per attivare/disattivare l'invio delle notifiche

Dettagli tecnici:
- I valori vanno salvati nel DB settings (tabella `Setting`) invece che in `.env`, così l'utente li modifica dall'interfaccia
- Aggiungere le chiavi `telegram.bot_token`, `telegram.chat_id`, `telegram.notifications_enabled` a `backend/app/mcp/default_settings.json` con default vuoti
- Modificare `TelegramService` (telegram_service.py) per leggere i valori dal DB (via SettingsService) a ogni invio, non dalla config statica
- Aggiungere la tab "Telegram" al file `frontend/src/routes/settings.tsx` con i campi configurabili
- La tab deve mostrare un toggle per attivare/disattivare le notifiche, i campi bot_token e chat_id, e uno status indicator che mostra se Telegram è configurato correttamente

Nota: il token del bot è un segreto — al momento verrà salvato in chiaro nel DB (come tutti gli altri settings). In futuro si potrà crittografare usando la Fernet key già presente.