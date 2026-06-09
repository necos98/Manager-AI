# Piano di Implementazione: Sistema notifiche Telegram via Hermes

## Task 1: Metodo build_notification_command in HermesProvider
**File:** `backend/app/providers/hermes_provider.py`
- Aggiungere `build_notification_command(message: str) -> list[str]` che restituisce `["hermes", "chat", "-q", message, "--quiet"]`
- Metodo statico/indipendente dallo stato del provider

## Task 2: NotificationService (nuovo file)
**File:** `backend/app/services/notification_service.py`
- Implementare `NotificationService` che implementa l'interfaccia `BaseNotifier`
- Si registra su `EventService` nel costruttore
- Metodo `notify(event)` — chiamato per ogni evento
- `_handle_event(event)` — filtra eventi rilevanti:
  - `issue_status_changed` + `new_status == "Finished"` → notifica completamento
  - `question_asked` → notifica domanda pending
- `_run_hermes_command(message)` — spawna `hermes chat -q <msg> --quiet` in subprocess
- Logging per debug e graceful failure

## Task 3: Attivazione in main.py
**File:** `backend/app/main.py`
- Importare `NotificationService` nel lifespan
- Istanziarlo dopo l'avvio di EventService ma prima del yield (dopo plugin startup)
- Non assegnare a variabile — serve solo per registrare il listener

## Task 4: Verifica
- Avviare backend e verificare che il servizio si registri senza errori
- Triggerare manualmente `complete_issue` e verificare che `hermes chat -q` venga invocato (controllare log)
- Triggerare `ask_user_question` e verificare notifica domanda
