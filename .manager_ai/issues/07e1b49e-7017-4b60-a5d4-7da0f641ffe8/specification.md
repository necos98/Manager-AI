# Integrazione Playwright per Testing End-to-End

## Obiettivo

Integrare Playwright in Manager AI come server MCP indipendente, orchestrato da Claude Code, per eseguire test browser end-to-end contestuali alle issue del progetto.

## Architettura

Due server MCP indipendenti, Claude Code orchestra entrambi in parallelo:

```
┌─────────────────────────────────────────────────┐
│                  Claude Code                     │
│  (usa entrambi i server MCP in parallelo)        │
└──────────┬──────────────────────┬────────────────┘
           │                      │
     Manager AI MCP        Playwright MCP
     (progetti, credenziali)  (browser tools)
```

**Manager AI MCP** espone contesto progetto: URL progetto, credenziali per ruolo.  
**Playwright MCP** (`@playwright/mcp`) è browser puro, indipendente, gestito come subprocess da Manager AI.

## Database: Nuova Tabella `project_credentials`

Le credenziali vanno nel database SQLite (sicurezza — non versionato in git, a differenza di `.manager_ai/`).

```sql
CREATE TABLE project_credentials (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL,             -- "admin", "user", "readonly", ecc.
    url TEXT NOT NULL,              -- URL pagina login della web app target
    encrypted_fields TEXT NOT NULL, -- JSON credenziali cifrato con Fernet (chiave server)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id, role)
);
```

## Nuovo Campo `url` in `projects`

```sql
ALTER TABLE projects ADD COLUMN url TEXT;  -- NULLABLE: solo progetti web usano Playwright
```

## Tool MCP Esposti da Manager AI

### `get_project_url`
- **Input**: `project_id`
- **Output**: URL del progetto (o null)
- **Uso**: Claude ottiene l'URL base della web app da testare

### `list_credentials`
- **Input**: `project_id`
- **Output**: Lista ruoli disponibili (solo i nomi ruolo, mai i valori)
- **Uso**: Claude sa quali ruoli può impersonare

### `get_credential`
- **Input**: `project_id`, `role`
- **Output**: URL + credenziali decifrate (username, password, eventuali campi extra)
- **Sicurezza**: I valori non appaiono mai nei log; il tool MCP restituisce i dati solo a Claude Code in sessione

### `set_credential`
- **Input**: `project_id`, `role`, `url`, `fields` (JSON con credenziali)
- **Output**: ok
- **Uso**: L'utente (o Claude su sua richiesta) salva le credenziali

### `delete_credential`
- **Input**: `project_id`, `role`
- **Output**: ok

## Backend: Nuovi Componenti

### Model
- `ProjectCredential`: SQLAlchemy model per tabella `project_credentials`
- `Project.url`: nuovo campo nullable

### Service
- `CredentialService`: CRUD con cifratura/decifratura Fernet
  - `create_credential(project_id, role, url, fields)`
  - `get_credentials(project_id)` → lista ruoli
  - `get_credential(project_id, role)` → dati decifrati
  - `delete_credential(project_id, role)`
  - `encrypt_fields(fields: dict) -> str`
  - `decrypt_fields(encrypted: str) -> dict`
  - Chiave Fernet da `MANAGER_AI_SECRET_KEY` env var (generata automaticamente se assente)

### Router
- `GET /api/projects/{project_id}/credentials` → lista ruoli
- `GET /api/projects/{project_id}/credentials/{role}` → dati decifrati (equivale a `get_credential`)
- `POST /api/projects/{project_id}/credentials` → crea/aggiorna
- `DELETE /api/projects/{project_id}/credentials/{role}` → elimina

### MCP Tools (in `app/mcp/server.py`)
- `get_project_url(project_id)`
- `list_credentials(project_id)`
- `get_credential(project_id, role)`

### Migration
- Alembic migration per `project_credentials` + `projects.url`

## Frontend: Project Settings

Nuova sezione "Test Credentials" nella pagina settings del progetto:
- **Campo URL progetto**: input testuale per `project.url`
- **Lista credenziali**: tabella con ruolo, URL login, data modifica
- **Form aggiunta**: ruolo (input), URL login (input), campi credenziali (coppie chiave-valore dinamiche)
- **Azioni**: modifica, elimina

## Gestione Playwright MCP Server

### Installazione
- Tramite `npx @playwright/mcp@latest`
- Manager AI verifica presenza e installa automaticamente se assente
- Aggiunge la configurazione al `claude.json` del progetto

### Avvio / Stop
- Manager AI spawna il subprocess all'inizio della sessione di test
- Health check: richiesta HTTP al server MCP per verificare sia vivo
- Stop: kill del processo su timeout di inattività (default 5 min) o fine sessione

### Configurazione
- `--browser chromium` (default)
- `--headless` (parametrizzabile: headless per CI, headed per dev)
- `--viewport` configurabile da settings progetto

## Flusso Tipico

```
1. Setup progetto
   Project settings → url = "https://mia-app.com"
   Credentials → admin (user, pass), user (user, pass)

2. Issue: task "Verifica login admin e creazione issue"
   
3. Claude Code esegue:
   → get_project_url("proj-123") → "https://mia-app.com"
   → list_credentials("proj-123") → ["admin", "user"]
   → get_credential("proj-123", "admin") → {url, username, password}
   → @playwright/mcp: browser_navigate(login_url)
   → browser_fill("#user", username)
   → browser_fill("#pass", password)
   → browser_click("button[type=submit]")
   → browser_snapshot() → verifica presenza "Dashboard"
   → browser_screenshot() → salva evidenza nella issue
```

## Potenzialità

| Area | Valore |
|------|--------|
| Zero-config testing | URL e credenziali configurati una volta, Claude li usa automaticamente |
| Test contestuali | Ogni issue può avere task di verifica browser real-time |
| Multi-ruolo | Stesso flusso testato con ruoli diversi senza riscrivere script |
| Evidenza visiva | Screenshot automatici nei report, video replay su fallimento |
| CI-ready | Headless di default, eseguibile in pipeline senza display |
| Indipendenza | Playwright MCP è server standard, aggiornabile separatamente da Manager AI |

## Rischi e Mitigazioni

| Rischio | Mitigazione |
|--------|-------------|
| Credenziali in chiaro | Cifratura Fernet lato server, mai nei log, tabella separata fuori da git |
| Processi zombie Playwright | Timeout inattività + health check periodico + kill forzato su shutdown |
| Dipendenza da npx/rete | Verifica presenza binario, opzione installazione locale, messaggio chiaro se offline |
| Test flaky su UI dinamica | Snapshot testuali (accessibility tree) più stabili degli screenshot pixel-perfect |
| Chiave Fernet persa | Backup automatico della chiave, generazione automatica al primo avvio |
