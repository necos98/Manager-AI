# Piano di implementazione — Sistema notifiche Telegram su completamento issue

## Task 1: Script watchdog Python

Creare `~/AppData/Local/hermes/scripts/issue_notifier.py`:

- Funzione `get_projects()`: chiama GET `http://localhost:8001/api/projects`, filtra `archived_at is None`
- Funzione `get_finished_issues(project_id)`: chiama GET `http://localhost:8001/api/projects/{project_id}/issues?status=Finished`
- Funzione `load_state()`: carica `notification_state.json`, con recovery se corrotto
- Funzione `save_state(state)`: scrive atomicamente il file di stato
- Funzione `format_notification(project_name, issue)`: produce il messaggio Telegram in markdown
- Funzione `get_issue_url(project_id, issue_id)`: costruisce URL web UI
- Main: loop progetti → fetch issues → confronto con stato → output notifiche → update stato

Resilienza:
- Timeout 5s sulle richieste HTTP
- Stato corrotto → ricrea da zero
- Backend non raggiungibile → stderr log + exit 0 (nessun falso positivo)
- Output su stdout solo per nuove notifiche (separate da `---`)

## Task 2: Creazione cron job Hermes

Registrare il cron job via Hermes cronjob tool:

- Schedule: `every 5m`
- Script: `issue_notifier.py` (path risolto in `~/AppData/Local/hermes/scripts/`)
- no_agent=true (watchdog pattern, zero token)
- Deliver: default (auto-delivery al canale corrente — Telegram)
- Workdir: opzionale, non necessario

## Task 3: Verifica

- Eseguire lo script manualmente per test
- Verificare che produca output corretto
- Verificare resilienza a backend spento
