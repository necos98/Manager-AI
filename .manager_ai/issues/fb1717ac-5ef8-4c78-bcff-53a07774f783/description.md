Aggiungere un sistema di notifiche Telegram via Hermes nella sezione Settings, con toggle per abilitare/disabilitare l'invio di notifiche su eventi.

**Requisiti:**
1. Nella sezione Settings → Hermes, aggiungere un toggle **"Notifiche Telegram"** (abilitato/disabilitato)
2. Solo se l'utente abilita il toggle, Hermes invia notifiche su Telegram quando:
   - Una issue viene completata (`issue.finished`)
   - L'agente chiama `ask_user_question` e ha bisogno di una risposta
3. Prima di inviare la notifica, il backend deve verificare:
   - Che Hermes sia installato nella macchina dell'utente (`shutil.which("hermes")`)
   - Che il gateway Telegram di Hermes sia configurato
   - Se Hermes non è presente o non configurato, loggare un warning e skippare la notifica senza crashare
4. Il toggle va salvato come impostazione persistente nel backend

**Proposta implementativa:**
- Aggiungere un setting `notifications.telegram_enabled` (default: false)
- Creare un componente UI toggle nella sezione Settings → Hermes
- Creare `check_hermes_available()` nel servizio di notifica
- Integrare i trigger nei punti `complete_issue` / `force_finish_issue` / `ask_user_question`
- Mostrare stato visivo nella UI (es. "🟢 Hermes rilevato" / "🔴 Hermes non trovato")

**File interessati:**
- `backend/app/services/notification_service.py` — nuovo servizio con check Hermes
- `backend/app/providers/hermes_provider.py` — eventuale metodo di verifica disponibilità
- `frontend/src/routes/settings.tsx` — aggiungere toggle nella sezione Hermes
- `frontend/src/features/settings/` — hook e API per il nuovo setting