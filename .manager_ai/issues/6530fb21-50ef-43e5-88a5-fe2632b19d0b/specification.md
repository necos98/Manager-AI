# Specifica — Sistema notifiche Telegram su completamento issue

## Overview

Un cron job Hermes (senza consumo di token LLM) che controlla periodicamente tutti i progetti di Manager AI per issue appena passate a status FINISHED e invia una notifica Telegram formattata. Usa il pattern **no_agent=true watchdog**: uno script Python eseguito su schedule, che produce stdout solo quando ci sono nuove notifiche.

## Architettura

### Componenti

1. **Script Python watchdog** → `~/AppData/Local/hermes/scripts/issue_notifier.py`
2. **File di stato JSON** → `~/AppData/Local/hermes/scripts/notification_state.json`
3. **Cron job Hermes** → ogni 5 minuti, esegue lo script in modalità no_agent=true

### Flusso

1. Il cron job esegue lo script ogni 5 minuti
2. Lo script chiama `GET /api/projects` su localhost:8001 per tutti i progetti attivi (non-archiviati)
3. Per ogni progetto, chiama `GET /api/projects/{project_id}/issues?status=Finished`
4. Confronta le issue trovate con il file di stato (notified_issue_ids + last_check_timestamp)
5. Per ogni issue FINISHED non ancora notificata, produce un messaggio formattato in stdout
6. Aggiorna il file di stato
7. Se nessuna nuova issue, stdout è vuoto → nessuna notifica inviata, zero token spesi

### API Endpoint

**Lista progetti:** `GET http://localhost:8001/api/projects`
- Filtra `archived_at == null`

**Lista issue per status:** `GET http://localhost:8001/api/projects/{project_id}/issues?status=Finished`
- Response: array di IssueResponse con id, name, description, status, priority, tasks, recap, updated_at

### File di stato (notification_state.json)

```json
{
  "last_check": "2026-06-09T18:30:00",
  "notified_issues": {
    "project_id_1": ["issue_id_1", "issue_id_2"],
    "project_id_2": ["issue_id_3"]
  }
}
```

### Formato notifica Telegram

```
✅ Issue Completata — {project_name}

📌 {issue_name}
🆔 #{issue_id_short}
📋 {descrizione breve o recap}
🏷️ Status: FINISHED

🔗 {url_web_ui}
```

### Scheduling

- **Intervallo:** 5 minuti (via cron job Hermes schedule `every 5m`)
- **Esecuzione:** no_agent=true — nessun LLM coinvolto
- **Script path:** `~/AppData/Local/hermes/scripts/issue_notifier.py`

### Resilienza

- Se il server Manager AI non risponde su localhost:8001, logga errore su stderr e termina silenziosamente (nessuna notifica falsa)
- Connection timeout di 5 secondi
- File di stato protetto: se corrotto, ricrea da zero (perde solo lo storico notifiche, evitando falsi positivi)
- Se lo script fallisce, cron riprova al prossimo tick

## Criteri di accettazione

1. [ ] Una issue portata a FINISHED genera una notifica Telegram entro 5 minuti
2. [ ] La stessa issue non viene notificata due volte
3. [ ] Funziona su tutti i progetti attivi (non archiviati)
4. [ ] Se il backend non è raggiungibile, non invia notifiche false
5. [ ] Configurabile: intervallo modificabile, delivery target modificabile
6. [ ] Consumo token zero durante il polling (no_agent=true)
