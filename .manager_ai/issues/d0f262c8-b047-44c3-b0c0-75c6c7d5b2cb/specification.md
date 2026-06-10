# Specifica: Rimuovere fallback Hermes CLI da NotificationService

## Problema
NotificationService attualmente spawna un subprocess `hermes send` quando Telegram non è configurato, come fallback per inviare notifiche. Questo è indesiderato perché:
- Spawna un processo Hermes anche quando l'utente non vuole notifiche Telegram
- Crea dipendenza da Hermes CLI per funzionalità non essenziali
- Può causare warning/spam nei log quando Hermes CLI non è installata o non configurata

## Soluzione
NotificationService deve diventare **puramente un file logger** — scrive su `notifications.log` ma non spawna mai Hermes CLI.

## Modifiche necessarie

### 1. `backend/app/services/notification_service.py`
- **Rimuovere** il metodo `_run_hermes_command()` (righe 168-204) — non deve più spawnare subprocess
- **Rimuovere** le chiamate `await self._run_hermes_command(...)` da `_notify_issue_finished` (riga 131) e `_notify_question_asked` (riga 166)
- **Rimuovere** l'import di `HermesProvider` (riga 15) — non più necessario
- **Mantenere** il logging su file (`_notification_logger.info()`) — resta l'unica funzione
- **Semplificare** il formato del log: rimuovere il campo `command` dal dict `extra` dato che non c'è più un comando Hermes da eseguire
- **Aggiornare** la docstring della classe per riflettere il nuovo scopo (solo file logging, nessun subprocess)
- **Mantenere** `_handle_event()` con i filtri event_type e il check `telegram_service.is_configured()` — serve ancora per decidere se loggare

### 2. `backend/app/providers/hermes_provider.py`
- **Rimuovere** il metodo `build_notification_command()` (righe 63-71) — è usato solo da NotificationService che non lo chiamerà più

### 3. `backend/app/main.py`
- **Nessuna modifica** — NotificationService va tenuto in main.py perché fa ancora file logging. La riga 338 `_ = NotificationService()` resta.

## Non modificare
- `TelegramNotifier` e `TelegramService` — già gestiscono correttamente le notifiche quando configurati
- Il logging su file `notifications.log` — va preservato
- Altri metodi di `HermesProvider` (`build_run_issue_commands`, `build_hook_command`, ecc.) — usati altrove
