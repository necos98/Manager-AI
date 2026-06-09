# Specifica: Sistema notifiche Telegram via Hermes su eventi issue

## 1. Obiettivo

Notificare l'utente su Telegram quando eventi importanti accadono in Manager AI, senza server esterni o webhook — utilizzando `hermes chat -q` (comando rapido) per inviare messaggi via Telegram.

## 2. Meccanismo Generale

Un `NotificationService` ascolta gli eventi emessi dal sistema (via `EventService`) e, per eventi selezionati, spawna un sottoprocesso che esegue:

```bash
hermes chat -q "Messaggio di notifica" --quiet
```

Questo comando Hermes è lightweight, non-interattivo, e ha accesso al tool `send_message` per notificare su Telegram.

## 3. Eventi da Coprire

### 3.1 `issue.finished` (issue completata)
- **Quando:** dopo che `complete_issue` o `force_finish_issue` completano con successo
- **Messaggio:** "L'issue '{issue_name}' è stata completata nel progetto {project_name}"
- **Implementazione:** hook nell'evento `issue_status_changed` → `new_status == "Finished"`

### 3.2 `ask_user_question` (domanda pending)
- **Quando:** una nuova domanda viene posta dall'AI (evento `question_asked`)
- **Messaggio:** "L'issue '{issue_name}' ha bisogno di una risposta: {question}"
- **Implementazione:** hook nell'evento `question_asked` (già emesso da `ask_user_question` in shared_tools.py)

## 4. Architettura

```
EventService.emit(event)
       │
       ▼
NotificationService._on_event(event)
       │
       ├─ 1. Check if event type is relevant
       ├─ 2. Build notification message
       ├─ 3. Build hermes chat -q command
       └─ 4. Run in subprocess (asyncio.create_subprocess_exec)
```

### 4.1 NotificationService (nuovo servizio)

`backend/app/services/notification_service.py`

```python
class NotificationService:
    """Ascolta eventi e spawna notifiche Telegram via Hermes CLI."""

    def __init__(self):
        # Register as EventService listener
        event_service.register(self)

    async def notify(self, event: dict):
        # Called by EventService for every event
        await self._handle_event(event)

    async def _handle_event(self, event: dict):
        event_type = event.get("type", "")
        if event_type == "issue_status_changed" and event.get("new_status") == "Finished":
            await self._notify_issue_finished(event)
        elif event_type == "question_asked":
            await self._notify_question_asked(event)

    async def _run_hermes_command(self, message: str):
        """Spawna 'hermes chat -q <message> --quiet' in subprocess."""
        proc = await asyncio.create_subprocess_exec(
            "hermes", "chat", "-q", message, "--quiet",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
```

### 4.2 Integrazione in HermesProvider

`backend/app/providers/hermes_provider.py`

Aggiungere un metodo statico `build_notification_command(message: str) -> list[str]` che restituisce `["hermes", "chat", "-q", message, "--quiet"]`.

### 4.3 Attivazione all'avvio

In `main.py` `lifespan()`, istanziare `NotificationService()` per registrarlo come listener degli eventi.

## 5. File Modificati

### Nuovi file:
1. **`backend/app/services/notification_service.py`** — NotificationService (listener EventService)

### File esistenti da modificare:
2. **`backend/app/providers/hermes_provider.py`** — aggiungere `build_notification_command()`
3. **`backend/app/main.py`** — import e istanziazione NotificationService nel lifespan

## 6. Considerazioni

- **Requisito:** Hermes deve essere installato e configurabile da `PATH` nel backend (come avviene già per via del terminal/provider Hermes)
- **Spawn immediato:** nessuna coda di attesa — la notifica parte in background via `asyncio.create_task()`
- **Graceful failure:** se `hermes chat -q` fallisce, si logga l'errore ma non si blocca il flusso principale
- **EventService singleton:** NotificationService si registra come notifier in `EventService` (usa lo stesso pattern di `WebSocketNotifier`)
- **Deduplicazione:** l'evento `question_asked` in shared_tools.py emette già sia `question_asked` che `notification` — NotificationService reagisce solo a `question_asked` per evitare duplicati
- **Utente Hermes configurato:** assumiamo che Hermes abbia un canale Telegram configurato (via `send_message`)

## 7. Non Incluso in Questa Issue

- Altre tipologie di evento (pipeline step, errore, ecc.)
- Configurazione UI per attivare/disattivare notifiche
- Formattazione avanzata (markdown, immagini)
- Rate limiting
