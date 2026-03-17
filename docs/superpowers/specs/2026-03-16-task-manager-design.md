# Task Manager for Claude Code — Design Spec

## Overview

Software di gestione task e contesto per lo sviluppo software con Claude Code. Un unico backend Python serve sia le API REST (per il frontend React) sia il server MCP (per Claude Code). PostgreSQL con pgvector come database.

## Stack tecnologico

- **Backend:** Python, FastAPI, SQLAlchemy, Alembic, libreria ufficiale `mcp`
- **Frontend:** Vite + React + Tailwind CSS
- **Database:** PostgreSQL 16 + pgvector
- **Infrastruttura:** Docker Compose

## Struttura del progetto

```
manager_ai/
├── docker-compose.yml
├── .env
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/
│   ├── alembic.ini
│   └── app/
│       ├── main.py           # FastAPI app + MCP server mount
│       ├── config.py         # settings
│       ├── database.py       # engine, session
│       ├── models/
│       │   ├── __init__.py
│       │   ├── project.py
│       │   └── task.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── project.py
│       │   └── task.py
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── projects.py
│       │   └── tasks.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── project_service.py
│       │   └── task_service.py
│       └── mcp/
│           ├── __init__.py
│           └── server.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── api/
│       │   └── client.js
│       ├── components/
│       │   ├── ProjectCard.jsx
│       │   ├── TaskList.jsx
│       │   ├── TaskDetail.jsx
│       │   ├── StatusBadge.jsx
│       │   └── MarkdownViewer.jsx
│       └── pages/
│           ├── ProjectsPage.jsx
│           ├── NewProjectPage.jsx
│           ├── ProjectDetailPage.jsx
│           ├── NewTaskPage.jsx
│           └── TaskDetailPage.jsx
```

## Modelli dati

### Project

| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK, generato automaticamente |
| name | VARCHAR(255) | Nome del progetto |
| path | VARCHAR(500) | Path della directory del progetto |
| description | TEXT | Contesto iniziale dato dall'utente |
| description_embedding | VECTOR(1536) | Embedding (fase successiva) |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

### Task

| Campo | Tipo | Note |
|-------|------|------|
| id | UUID | PK, generato automaticamente |
| project_id | UUID | FK → Project |
| name | VARCHAR(255) | Nullable — impostato da Claude |
| description | TEXT | Descrizione inserita dall'utente |
| status | ENUM | New, Planned, Accepted, Declined, Finished, Canceled |
| priority | INTEGER | 1 (massima) - 5 (minima) |
| plan | TEXT | Piano markdown creato da Claude |
| recap | TEXT | Recap finale scritto da Claude |
| decline_feedback | TEXT | Feedback utente al decline |
| description_embedding | VECTOR(1536) | Embedding (fase successiva) |
| plan_embedding | VECTOR(1536) | Embedding (fase successiva) |
| recap_embedding | VECTOR(1536) | Embedding (fase successiva) |
| created_at | TIMESTAMP | Auto |
| updated_at | TIMESTAMP | Auto |

**Note:** I campi embedding sono predisposti ma non popolati in questa fase. La generazione degli embeddings sarà implementata successivamente.

### Transizioni di stato

```
New → Planned        (Claude analizza e crea il piano)
Declined → Planned   (Claude ri-analizza con feedback e crea nuovo piano)
Planned → Accepted   (utente approva dal frontend)
Planned → Declined   (utente rifiuta con feedback)
Accepted → Finished  (Claude completa e scrive recap)
Any → Canceled       (utente cancella dal frontend)
```

Quando un task viene declinato, lo stato resta **Declined** con il feedback salvato. Claude, alla prossima richiesta di task, riceverà i task Declined (con priorità sopra ai New) e potrà leggere il feedback tramite `get_task_details`, creare un nuovo piano, e riportare il task a Planned.

### Validazione transizioni

Il backend valida le transizioni di stato. Transizioni non elencate sopra vengono rifiutate con HTTP 422. Errori restituiti nel formato:

```json
{"detail": "Invalid state transition from X to Y"}
```

### Validazione generale

- `priority`: deve essere tra 1 e 5 (HTTP 422 altrimenti)
- `project.path`: stringa non vuota, nessuna validazione su disco
- Risorse non trovate: HTTP 404 con `{"detail": "Resource not found"}`
- Task non appartenente al progetto (MCP): HTTP 403 con `{"detail": "Task does not belong to project"}`

## API REST (frontend → backend)

### Projects

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | `/api/projects` | Crea progetto (name, path, description) |
| GET | `/api/projects` | Lista progetti |
| GET | `/api/projects/{id}` | Dettaglio progetto |
| PUT | `/api/projects/{id}` | Aggiorna progetto |
| DELETE | `/api/projects/{id}` | Elimina progetto |

### Tasks

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| POST | `/api/projects/{project_id}/tasks` | Crea task (description, priority) |
| GET | `/api/projects/{project_id}/tasks` | Lista task (filtrabili per status via query param `?status=New`) |
| GET | `/api/projects/{project_id}/tasks/{task_id}` | Dettaglio task |
| PUT | `/api/projects/{project_id}/tasks/{task_id}` | Aggiorna task (solo campi utente: `description`, `priority`) |
| PATCH | `/api/projects/{project_id}/tasks/{task_id}/status` | Cambia stato (con validazione transizioni + decline_feedback) |
| DELETE | `/api/projects/{project_id}/tasks/{task_id}` | Elimina task |

## MCP Tools (Claude Code → backend)

Tutti i tool accettano sempre `project_id` per validazione di appartenenza.

| Tool | Parametri | Descrizione |
|------|-----------|-------------|
| `get_next_task` | `project_id` | Ritorna il task da lavorare con priorità più alta. Ordine: Declined prima di New, poi per priorità (numero più basso). Risponde con `id`, `description`, `status`, e `decline_feedback` (se presente). Ritorna `null` se non ci sono task disponibili |
| `get_task_details` | `project_id`, `task_id` | Tutti i dettagli di un task |
| `get_task_status` | `project_id`, `task_id` | Stato attuale del task |
| `get_project_context` | `project_id` | Info del progetto (nome, path, descrizione) |
| `set_task_name` | `project_id`, `task_id`, `name` | Imposta il nome del task |
| `save_task_plan` | `project_id`, `task_id`, `plan` | Salva piano markdown, stato → Planned. Accetta task in stato New o Declined |
| `complete_task` | `project_id`, `task_id`, `recap` | Stato → Finished, salva recap. Accetta solo task in stato Accepted |

### Flusso MCP tipico

1. Claude legge `manager.json` dal progetto → ottiene `project_id`
2. Claude chiama `get_next_task(project_id)` → riceve id, descrizione, stato, e eventuale feedback
3. Se il task è Declined: Claude legge il `decline_feedback` e ne tiene conto
4. Claude chiama `set_task_name(project_id, task_id, name)` + `save_task_plan(project_id, task_id, plan)` → stato diventa Planned
5. Claude comunica all'utente che il piano è pronto e chiede di accettare o declinare dal frontend
6. L'utente accetta/declina dal frontend, poi torna a Claude e gli dice di procedere
7. Claude chiama `get_task_status(project_id, task_id)` per verificare la decisione
8. Se Declined: il task sarà ripreso al prossimo `get_next_task`
9. Se Accepted: Claude implementa → chiama `complete_task(project_id, task_id, recap)`

**Nota:** Claude non fa polling autonomo. L'utente è responsabile di dire a Claude quando procedere dopo aver accettato/declinato un task dal frontend.

### File manager.json

Ogni progetto gestito avrà nella sua root un file `manager.json`:

```json
{
  "project_uuid": "uuid-del-progetto"
}
```

Creato manualmente dall'utente dopo aver registrato il progetto nel frontend. Claude Code legge questo file per determinare il `project_id` da usare nelle chiamate MCP.

## Infrastruttura Docker

### docker-compose.yml

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: manager_ai
      POSTGRES_USER: manager
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+asyncpg://manager:${DB_PASSWORD}@db:5432/manager_ai

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

- **db:** PostgreSQL 16 con pgvector preinstallato
- **backend:** FastAPI che serve API REST + MCP server (Streamable HTTP su `/mcp`)
- **frontend:** Build statico React servito da nginx

### Health Check

Il backend espone `GET /health` per il health check di Docker Compose.

### MCP Transport

Streamable HTTP sull'endpoint `/mcp`. Claude Code si configura con:

```json
{
  "mcpServers": {
    "manager-ai": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Frontend

### Pagine

| Pagina | Route | Descrizione |
|--------|-------|-------------|
| Lista progetti | `/` | Card con nome, path, conteggio task per stato |
| Nuovo progetto | `/projects/new` | Form: name, path, description |
| Dettaglio progetto | `/projects/:id` | Lista task con filtri stato, ordinamento priorità |
| Nuovo task | `/projects/:id/tasks/new` | Form: description, priority (1-5) |
| Dettaglio task | `/projects/:id/tasks/:taskId` | Stato, piano markdown, recap, bottoni Accept/Decline |

### Flusso Decline

Nella pagina dettaglio task, il bottone "Decline" mostra una textarea per il feedback. Il submit invia PATCH con stato Declined + feedback. Il task resta in stato Declined finché Claude non lo riprende con `get_next_task`.

### Componenti principali

- `ProjectCard` — card nella lista progetti
- `TaskList` — lista/tabella task con filtri e ordinamento
- `TaskDetail` — vista completa con piano markdown renderizzato
- `StatusBadge` — badge colorato per stato
- `MarkdownViewer` — rendering markdown per piano e recap
