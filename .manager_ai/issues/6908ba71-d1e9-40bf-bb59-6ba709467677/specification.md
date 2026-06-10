# Specifica: UI Settings > Telegram con toggle e configurazione token/chat_id

## Contesto

Le notifiche Telegram funzionano già via Bot API diretta (TelegramService + TelegramNotifier), ma la configurazione (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) è hardcoded in `.env` e caricata via pydantic-settings → config.py al boot. L'utente non può modificarla dall'interfaccia web.

Il sistema di Settings esiste già: `Setting` model (key-value in SQLite), `SettingsService` (lettura/scrittura con fallback a `default_settings.json`), router REST a `/api/settings`, e UI Settings page con tabs dinamici. Il setting `telegram.notifications_enabled` (toggle on/off) non esiste ancora.

## Architettura

### Backend

**1. `default_settings.json`** — Aggiungere 3 nuove chiavi:
```json
"telegram.bot_token": ""
"telegram.chat_id": ""
"telegram.notifications_enabled": "false"
```

**2. `telegram_service.py`** — Modifiche:
- Aggiungere `_notifications_enabled: bool` (default: False)
- Aggiungere metodo `configure(*, bot_token: str = "", chat_id: str = "", enabled: bool = False)` per impostare valori da DB dinamicamente
- Modificare `is_configured()`: ora richiede anche `_notifications_enabled is True` (oltre a token e chat_id non vuoti)
- Mantenere fallback env: se `configure()` non è mai chiamato, i valori letti da `settings.telegram_bot_token` e `settings.telegram_chat_id` in `__init__` funzionano come prima (backward compat)

**3. `telegram_notifier.py`** — Modifiche:
- `__init__` accetta `bot_token`, `chat_id`, `notifications_enabled` opzionali
- Chiama `telegram_service.configure(...)` con questi valori se forniti
- Se non forniti, si comporta come prima (env)

**4. `main.py`** (lifespan) — Modifiche:
- Dopo `_ = TelegramNotifier()`, ottenere una sessione DB, leggere i 3 setting telegram dal DB (via SettingsService) e chiamare `telegram_service.configure(...)` con quei valori
- Se i valori DB sono vuoti, lascia i fallback env

**5. `routers/settings.py`** — Modifica:
- Nel `update_setting` endpoint, dopo l'update se la chiave inizia con `telegram.`, riconfigurare `telegram_service` leggendo tutti e 3 i valori dal DB. Questo garantisce che la modifica sia immediata senza restart.

**6. `getCategory()` per la UI** — Le chiavi `telegram.*` vanno categorizzate come `"Telegram"`.

### Frontend

**7. `settings.tsx`** — Modifiche:
- Aggiungere `"Telegram"` al `TABS` array
- Aggiungere `getCategory()` rule: se key inizia con `telegram.` → categoria `"Telegram"`
- Aggiungere tab `"Telegram"` → render `<TelegramSettingsPanel />`

**8. Nuovo componente `TelegramSettingsPanel`** — In un nuovo file o inline in `settings.tsx`:
- **Toggle "Notifiche Telegram attive"** — collegato a `telegram.notifications_enabled`. Stesso stile toggle usato in `PreferencesPanel` (toggle switch).
- **Campo testo "Bot Token"** — collegato a `telegram.bot_token`. Input type="password" o text con mascheramento visivo per mostrare/nascondere il token.
- **Campo testo "Chat ID"** — collegato a `telegram.chat_id`. Input text normale.
- **Status indicator** — mostra se Telegram è configurato correttamente:
  - 🔴 **Non configurato** — se bot_token è vuoto o chat_id è vuoto o notifiche disabilitate
  - 🟢 **Configurato** — se bot_token e chat_id sono presenti e notifiche abilitate
- Ogni campo salva automaticamente via `useUpdateSetting()` hook (come fa già `SettingField` per i toggle)

**9. Schema frontend** — Il bottone "Save" non è necessario per i campi telegram: si usa auto-save on change come per i toggle esistenti (onChange → updateSetting.mutate). Per il bot_token, si può usare un pattern di debounce per non salvare a ogni carattere, oppure un campo con bottone "Save" separato.

### Considerazioni

- **Secret in chiaro**: Il token del bot è un segreto. Attualmente viene salvato in chiaro nel DB (come tutti gli altri settings). In futuro si potrà crittografare con la Fernet key già presente. Per ora, come da issue, va in chiaro.
- **Nessuna migrazione DB necessaria**: `Setting` è key-value generico, le nuove chiavi vengono create al primo upsert.
- **Backward compatibilità**: Se le chiavi DB sono vuote, il sistema cade sui valori `.env` esistenti.
- **Notifiche disabilitate**: Se `notifications_enabled` è `false`, `telegram_service.is_configured()` torna `False`, e TelegramNotifier non invia nulla. NotificationService (Hermes CLI fallback) è già condizionale: se TelegramService non è configurato, usa Hermes. Quindi disabilitare Telegram dall'UI fa automaticamente ripartire il fallback Hermes.
