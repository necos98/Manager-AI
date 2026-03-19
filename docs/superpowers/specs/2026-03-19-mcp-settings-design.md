# MCP Settings — Design Spec

## Overview

Aggiunta di un sistema di configurazione dei testi forniti all'LLM tramite MCP. I testi (descrizioni dei tool e messaggi di risposta) sono gestiti in una tabella `settings` nel database e modificabili dall'utente tramite una pagina "Settings" nel frontend. I valori di default sono versionati in un file JSON nel progetto.

## Obiettivi

- Permettere la modifica dei testi MCP (tool descriptions + response messages) senza toccare il codice
- Gestire i default tramite un file JSON versionabile via git
- Il MCP server legge i testi dal DB ad ogni chiamata (aggiornamento senza restart)
- Frontend con UI organizzata per categoria, badge "Customized", reset per singolo setting e globale

## Stack

Nessuna modifica allo stack esistente: FastAPI, SQLAlchemy, SQLite, React + Tailwind.

## Struttura dati

### Tabella `settings`

| Campo | Tipo | Note |
|-------|------|------|
| `key` | VARCHAR(255) | PK, es. `tool.save_task_plan.response_message` |
| `value` | TEXT | Valore personalizzato dall'utente |
| `updated_at` | TIMESTAMP | Auto-aggiornato |

La tabella contiene **solo i setting personalizzati**. Se una chiave non è presente, si usa il default dal JSON. Il reset cancella la riga (non sovrascrive con il default).

### File `backend/app/mcp/default_settings.json`

Source of truth per i valori di default. Versionabile via git.

```json
{
  "server.name": "Manager AI",
  "tool.get_next_task.description": "Get the highest priority task that needs work (Declined before New, then by priority). Returns task id, description, status, and decline_feedback if present. Returns null if none available.",
  "tool.get_task_details.description": "Get all details of a specific task.",
  "tool.get_task_status.description": "Get the current status of a task.",
  "tool.get_project_context.description": "Get project information (name, path, description, tech_stack).",
  "tool.set_task_name.description": "Set the name of a task after analysis.",
  "tool.save_task_plan.description": "Save a markdown plan for a task and set status to Planned. Only works for tasks in New or Declined status.\n\nIMPORTANT: After saving a plan, you MUST stop and wait for the user to approve or decline the plan via the frontend. Do NOT proceed with implementation until the task status changes to 'Accepted'. Poll get_task_status to check, but only after the user tells you they have reviewed the plan.",
  "tool.save_task_plan.response_message": "Plan saved. STOP HERE — do NOT proceed with implementation. The user must review and approve this plan in the frontend before you can continue. Wait for the user to confirm approval, then check the task status with get_task_status.",
  "tool.complete_task.description": "Mark a task as Finished and save the recap. Only works for tasks in Accepted status."
}
```

La convenzione delle chiavi è:
- `server.<campo>` — configurazione del server MCP
- `tool.<nome_tool>.description` — descrizione nel catalogo strumenti di Claude
- `tool.<nome_tool>.response_message` — testo nel corpo della risposta del tool

## Backend

### Modello SQLAlchemy

Nuovo file `backend/app/models/setting.py`:

```python
class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

### SettingsService

Nuovo file `backend/app/services/settings_service.py`:

- `get(key: str) -> str` — valore da DB se esiste, altrimenti dal JSON
- `get_all() -> list[SettingOut]` — merge DB + JSON, con flag `is_customized`
- `set(key: str, value: str) -> Setting` — upsert in DB
- `reset(key: str) -> None` — delete dalla DB
- `reset_all() -> None` — delete tutte le righe

Il JSON viene caricato una volta in memoria al primo accesso (`functools.lru_cache` o variabile modulo).

### Schema Pydantic

Nuovo file `backend/app/schemas/setting.py`:

```python
class SettingOut(BaseModel):
    key: str
    value: str          # valore attivo (DB o default)
    default: str        # valore dal JSON
    is_customized: bool # True se presente in DB

class SettingUpdate(BaseModel):
    value: str
```

### Router REST

Nuovo file `backend/app/routers/settings.py`, montato in `main.py`:

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/settings` | Lista tutti i setting con valore attivo, default e is_customized |
| PUT | `/api/settings/{key}` | Salva personalizzazione (upsert) |
| DELETE | `/api/settings/{key}` | Reset singolo setting |
| DELETE | `/api/settings` | Reset tutti i setting |

### MCP server

Il server MCP viene modificato per leggere i testi dal DB ad ogni chiamata:

**Tool descriptions:** lette dal JSON al momento del decoratore `@mcp.tool(description=...)`. Statiche per sessione MCP corrente, aggiornate alla prossima connessione di Claude. (Limite tecnico del protocollo MCP: le descrizioni vengono esposte al momento della handshake, non ad ogni chiamata.)

**Response messages:** letti dal DB ad ogni invocazione del tool tramite `SettingsService`. Aggiornamento in tempo reale senza restart.

Esempio per `save_task_plan`:

```python
@mcp.tool()
async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    async with async_session() as session:
        settings_service = SettingsService(session)
        response_msg = await settings_service.get("tool.save_task_plan.response_message")
        task_service = TaskService(session)
        # ... logica esistente ...
        return {"message": response_msg, ...}
```

## Frontend

### Nuova route

`/settings` — aggiunta in `App.jsx` e link nell'header.

### Pagina `SettingsPage`

Organizzata in **3 tab**:

| Tab | Chiavi |
|-----|--------|
| **Server** | `server.name` |
| **Tool Descriptions** | `tool.*.description` |
| **Response Messages** | `tool.*.response_message` |

**Per ogni setting:**
- Label leggibile derivata dalla chiave (es. `tool.save_task_plan.response_message` → "Save Task Plan")
- Textarea con il valore corrente
- Badge **"Customized"** (colore accent) se `is_customized: true`
- Pulsante reset (↺) per singolo setting — chiamata DELETE, ritorna al default
- Pulsante **"Save"** per ogni campo — salvataggio individuale

**In fondo alla pagina:**
- Pulsante "Reset all to defaults" con dialog di conferma

### API client

Aggiunte a `frontend/src/api/client.js`:

```js
getSettings: () => request("/settings"),
updateSetting: (key, value) => request(`/settings/${encodeURIComponent(key)}`, { method: "PUT", body: JSON.stringify({ value }) }),
resetSetting: (key) => request(`/settings/${encodeURIComponent(key)}`, { method: "DELETE" }),
resetAllSettings: () => request("/settings", { method: "DELETE" }),
```

## Migrazione database

Nuova migrazione Alembic che crea la tabella `settings`. Non modifica tabelle esistenti.

## Note implementative

- Il file `default_settings.json` viene letto con `importlib.resources` o path relativo al modulo Python
- Chiavi non riconosciute nel DB (es. da versioni precedenti) vengono ignorate in `get_all()`
- Il DELETE su `/api/settings/{key}` ritorna 204 anche se la chiave non era personalizzata (idempotente)
- Reset globale usa una singola query `DELETE FROM settings`
