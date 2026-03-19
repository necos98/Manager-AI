# MCP Settings — Design Spec

## Overview

Aggiunta di un sistema di configurazione dei testi forniti all'LLM tramite MCP. I testi (descrizioni dei tool e messaggi di risposta) sono gestiti in una tabella `settings` nel database e modificabili dall'utente tramite una pagina "Settings" nel frontend. I valori di default sono versionati in un file JSON nel progetto.

## Obiettivi

- Permettere la modifica dei testi MCP (tool descriptions + response messages) senza toccare il codice
- Gestire i default tramite un file JSON versionabile via git
- I response messages vengono letti dal DB ad ogni chiamata MCP (aggiornamento in tempo reale)
- Le tool descriptions richiedono un restart del backend per essere aggiornate (limite del protocollo MCP: le descrizioni vengono esposte alla handshake, non ad ogni chiamata)
- Frontend con UI organizzata per categoria, badge "Customized", reset per singolo setting e globale

## Stack

Nessuna modifica allo stack esistente: FastAPI, SQLAlchemy, SQLite, React + Tailwind.

## Struttura dati

### Tabella `settings`

| Campo | Tipo | Note |
|-------|------|------|
| `key` | VARCHAR(255) | PK, es. `tool.save_task_plan.response_message` |
| `value` | TEXT | Valore personalizzato dall'utente |
| `updated_at` | TIMESTAMP | `server_default=func.now()`, `onupdate=func.now()` |

La tabella contiene **solo i setting personalizzati**. Se una chiave non è presente, si usa il default dal JSON. Il reset cancella la riga (non sovrascrive con il default).

### Modello SQLAlchemy

Nuovo file `backend/app/models/setting.py`:

```python
class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

### File `backend/app/mcp/default_settings.json`

Source of truth per i valori di default. Versionabile via git. Contiene **9 chiavi totali**: 1 server, 7 tool descriptions, 1 response message.

Convenzione chiavi:
- `server.<campo>` — configurazione del server MCP
- `tool.<nome_tool>.description` — descrizione nel catalogo strumenti di Claude (richiede restart per aggiornare)
- `tool.<nome_tool>.response_message` — testo nel corpo della risposta del tool (aggiornato in tempo reale)

```json
{
  "server.name": "Manager AI",
  "tool.get_next_task.description": "Get the highest priority task that needs work (Declined before New, then by priority). Returns task id, description, status, and decline_feedback if present. Returns null if none available.",
  "tool.get_task_details.description": "Get all details of a specific task.",
  "tool.get_task_status.description": "Get the current status of a task.",
  "tool.get_project_context.description": "Get project information (name, path, description, tech_stack).",
  "tool.set_task_name.description": "Set the name of a task after analysis.",
  "tool.save_task_plan.description": "Save a markdown plan for a task and set status to Planned. Only works for tasks in New or Declined status.\n\nIMPORTANT: After saving a plan, you MUST stop and wait for the user to approve or decline the plan via the frontend. Do NOT proceed with implementation until the task status changes to 'Accepted'.",
  "tool.save_task_plan.response_message": "Plan saved. STOP HERE — do NOT proceed with implementation. The user must review and approve this plan in the frontend before you can continue. Wait for the user to confirm approval, then check the task status with get_task_status.",
  "tool.complete_task.description": "Mark a task as Finished and save the recap. Only works for tasks in Accepted status."
}
```

Solo `save_task_plan` ha un `response_message` configurabile perché è l'unico tool che restituisce un testo istruzionale a Claude. Gli altri tool restituiscono dati strutturati.

## Backend

### Schema Pydantic

Nuovo file `backend/app/schemas/setting.py`:

```python
class SettingOut(BaseModel):
    key: str
    value: str          # valore attivo (DB o default)
    default: str        # valore dal JSON
    is_customized: bool # True se presente in DB

class SettingUpdate(BaseModel):
    value: str = Field(..., min_length=1)
```

### SettingsService

Nuovo file `backend/app/services/settings_service.py`. Segue il pattern esistente: costruttore con `session: AsyncSession`.

```python
class SettingsService:
    def __init__(self, session: AsyncSession): ...

    async def get(self, key: str) -> str:
        """Ritorna il valore DB se la riga esiste, altrimenti il valore dal JSON.
        Solleva KeyError se la chiave non è presente nel JSON (mai in DB senza default)."""

    async def get_all(self) -> list[SettingOut]:
        """Merge DB + JSON defaults. Solo chiavi presenti nel JSON sono incluse.
        Chiavi in DB senza corrispondenza nel JSON vengono ignorate."""

    async def set(self, key: str, value: str) -> Setting:
        """Upsert in DB. Solleva KeyError se la chiave non è nel JSON — il router
        catcha KeyError e restituisce HTTP 404."""

    async def reset(self, key: str) -> None:
        """Delete ORM della riga da DB. Idempotente: nessun errore se la chiave non è personalizzata."""

    async def reset_all(self) -> None:
        """Delete ORM di tutte le righe (non bulk SQL, per coerenza con il lifecycle ORM)."""
```

Il JSON viene letto una volta e tenuto in memoria come variabile di modulo (non richiede lru_cache, è read-only).

### Router REST

Nuovo file `backend/app/routers/settings.py`, montato in `main.py` con `app.include_router(settings.router)`.

**Importante per il routing FastAPI:** la route `DELETE /api/settings` deve essere registrata **prima** di `DELETE /api/settings/{key}` per evitare conflitti.

| Metodo | Endpoint | Response | Descrizione |
|--------|----------|----------|-------------|
| GET | `/api/settings` | `200 list[SettingOut]` | Lista tutti i setting con valore attivo, default e is_customized |
| PUT | `/api/settings/{key}` | `200 SettingOut` | Salva personalizzazione (upsert). Il service solleva KeyError → router restituisce 404 se la chiave non è nel JSON |
| DELETE | `/api/settings` | `204 No Content` | Reset tutti i setting |
| DELETE | `/api/settings/{key}` | `204 No Content` | Reset singolo setting (idempotente) |

### MCP server

**Tool descriptions:** lette da `default_settings.json` all'avvio del server (import time) e passate come `description=` ai decoratori `@mcp.tool()`. Le modifiche tramite frontend richiedono un **restart del backend** per essere applicate alle descriptions. Questo comportamento è comunicato all'utente nel frontend con una nota nella tab "Tool Descriptions".

**Response messages:** letti dal DB ad ogni invocazione tramite `SettingsService`. Aggiornamento in tempo reale.

Esempio integrazione in `save_task_plan`:

```python
@mcp.tool()
async def save_task_plan(project_id: str, task_id: str, plan: str) -> dict:
    async with async_session() as session:
        settings_service = SettingsService(session)
        task_service = TaskService(session)
        try:
            task = await task_service.save_plan(task_id, project_id, plan)
            await session.commit()
            response_msg = await settings_service.get("tool.save_task_plan.response_message")
            return {
                "id": task.id,
                "status": task.status.value,
                "plan": task.plan,
                "message": response_msg,
            }
        except (ValueError, PermissionError) as e:
            await session.rollback()
            return {"error": str(e)}
```

### Migrazione Alembic

Nuova migrazione Alembic (deliverable esplicito) che crea la tabella `settings`. Non modifica tabelle esistenti.

## Frontend

### Aggiornamenti App.jsx

- Aggiunta route `/settings` → `<SettingsPage />`
- Aggiunta link "Settings" nell'`<header>` esistente accanto al logo

### Nuova pagina `SettingsPage`

Organizzata in **3 tab**. La categoria è derivata dal prefisso della chiave:

| Tab | Prefisso chiave | Esempio chiavi |
|-----|----------------|---------------|
| **Server** | `server.` | `server.name` |
| **Tool Descriptions** | `tool.*.description` | `tool.save_task_plan.description` |
| **Response Messages** | `tool.*.response_message` | `tool.save_task_plan.response_message` |

**Nota visibile nella tab "Tool Descriptions":** "Le modifiche alle descrizioni dei tool hanno effetto dopo il riavvio del backend."

**Per ogni setting:**
- Label leggibile derivata dalla chiave (es. `tool.save_task_plan.response_message` → "Save Task Plan")
- Textarea con il valore corrente
- Badge **"Customized"** (accent color) se `is_customized: true`
- Pulsante reset (↺) per singolo setting — chiama `DELETE /api/settings/{key}`, aggiorna stato locale
- Pulsante **"Save"** per ogni campo — salvataggio individuale tramite `PUT /api/settings/{key}`

**In fondo alla pagina:**
- Pulsante "Reset all to defaults" con dialog di conferma — chiama `DELETE /api/settings`

### API client

Aggiunte a `frontend/src/api/client.js`:

```js
getSettings: () => request("/settings"),
updateSetting: (key, value) =>
  request(`/settings/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  }),
resetSetting: (key) =>
  request(`/settings/${encodeURIComponent(key)}`, { method: "DELETE" }),
resetAllSettings: () => request("/settings", { method: "DELETE" }),
```
