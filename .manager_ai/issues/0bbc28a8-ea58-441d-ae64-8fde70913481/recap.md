# Recap: Sistema notifiche Telegram via Hermes su eventi issue

## Cosa è stato implementato

### 1. `HermesProvider.build_notification_command()` (linee 63-70)
Metodo statico che costruisce il comando `hermes chat -q <messaggio> --quiet`, riutilizzabile da NotificationService.

### 2. `NotificationService` (nuovo file)
Servizio che implementa `BaseNotifier` e si registra su `EventService` all'inizializzazione. Ascolta:
- **`issue_status_changed` con `new_status == "Finished"`** → notifica "Issue {name} completata"
- **`question_asked`** → notifica "L'issue {name} ha bisogno di una risposta: {question}"

Spawna `hermes chat -q` in subprocess con graceful failure (logga warning se Hermes CLI non trovato o fallisce).

### 3. Attivazione in `main.py` (linea 337)
`_ = NotificationService()` nel lifespan, dopo plugin startup ma prima del yield.

### 4. Bug fix: `issue_name` nell'evento `question_asked`
L'evento `question_asked` in `shared_tools.py` non includeva `issue_name`, causando default a "Untitled" nelle notifiche. Spostato il calcolo di `issue_name` prima dell'emissione dell'evento.

## Verifica
- ✅ Log di startup: "NotificationService registered on EventService"
- ✅ Import e instanziazione OK
- ✅ 6/6 `issue_status_changed` eventi hanno `issue_name`
- ✅ 1/1 `question_asked` evento ha `issue_name`
- ✅ 218 test passati (0 nuove regressioni)
- ✅ Notifica via `hermes chat -q <msg> --quiet` funzionante