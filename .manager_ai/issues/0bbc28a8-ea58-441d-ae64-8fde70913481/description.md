Creare un sistema di notifiche Telegram basato su eventi di Manager AI, senza server esterni o webhook.

**Meccanismo:**
Quando un evento triggera (issue completata, ask_user_question), il backend spawna un terminale Hermes con un comando `hermes chat -q` che notifica l'utente su Telegram.

**Eventi da coprire:**
- `issue.finished` → "L'issue X è stata completata"
- `ask_user_question` → "L'issue X ha bisogno di una risposta: [domanda]"

**Implementazione proposta:**
1. Aggiungere `build_notification_command(event_type, data)` in `HermesProvider` (usa `hermes chat -q "messaggio" --quiet`)
2. Creare un servizio `NotificationService` che:
   - Ascolta/riceve eventi (issue.finished, question.asked)
   - Costruisce il messaggio appropriato
   - Spawna un terminale temporaneo con il comando Hermes
3. Integrare nei punti giusti:
   - `complete_issue` / `force_finish_issue` → triggera notifica completamento
   - `ask_user_question` → triggera notifica domanda pending

**Dettagli tecnici:**
- Il terminale Hermes usa già `hermes chat -q` (comando rapido) quindi è lightweight
- Hermes ha il tool `send_message` che può notificare su Telegram
- Nessuna dipendenza esterna — tutto backend-side

**File interessati:**
- `backend/app/providers/hermes_provider.py` — nuovo metodo build_notification_command
- `backend/app/services/notification_service.py` — nuovo servizio
- `backend/app/routers/issues.py` — integrazione nei punti di completamento/domanda