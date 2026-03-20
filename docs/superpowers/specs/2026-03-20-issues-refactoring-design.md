# Refactoring: tasks → issues + task atomici strutturati

## Contesto

La tabella `tasks` rappresenta un concetto di alto livello (issue/ticket) che contiene spec, plan e recap. Il nome "task" e' fuorviante perche' i veri task atomici sono i passi del plan. Questo refactoring rinomina la tabella in `issues` e introduce una nuova tabella `tasks` per i task atomici strutturati.

## Gerarchia target

```
issues (ex "tasks")
  ├── specification (markdown)
  ├── plan (markdown libero)
  ├── tasks[] (task atomici strutturati)
  │     ├── {name, status, order}
  │     ├── {name, status, order}
  │     └── ...
  └── recap (markdown)
```

## Database

### Tabella `issues` (rinominata da `tasks`)

Stessi campi, solo il nome tabella cambia:

| Campo | Tipo | Note |
|-------|------|------|
| id | String(36) PK | UUID |
| project_id | String(36) FK | → projects.id |
| name | String(255) | nullable |
| description | Text | NOT NULL |
| status | IssueStatus enum | NEW, REASONING, PLANNED, ACCEPTED, DECLINED, FINISHED, CANCELED |
| priority | Integer | default 3, range 1-5 |
| specification | Text | nullable |
| plan | Text | nullable, markdown libero |
| recap | Text | nullable |
| decline_feedback | Text | nullable |
| created_at | DateTime | |
| updated_at | DateTime | |

### Nuova tabella `tasks`

| Campo | Tipo | Note |
|-------|------|------|
| id | String(36) PK | UUID |
| issue_id | String(36) FK | → issues.id, ON DELETE CASCADE |
| name | String(255) | NOT NULL |
| status | TaskStatus enum | PENDING, IN_PROGRESS, COMPLETED |
| order | Integer | NOT NULL, per ordinamento |
| created_at | DateTime | |
| updated_at | DateTime | |

### Constraint

Unique constraint composito su `(issue_id, order)` nella tabella `tasks` per evitare ordini duplicati.

### Migration

Una singola migration Alembic che:
1. `op.rename_table("tasks", "issues")` — rinomina tabella esistente
2. `op.create_table("tasks", ...)` — crea nuova tabella con FK verso `issues`

Downgrade: `op.drop_table("tasks")` poi `op.rename_table("issues", "tasks")`.

Nessuna perdita di dati: la rename preserva tutti i record esistenti.

## Backend

### Models

**`models/issue.py`** (ex `models/task.py`):
- Classe `Issue` con `__tablename__ = "issues"`
- Enum `IssueStatus` (ex `TaskStatus`): NEW, REASONING, PLANNED, ACCEPTED, DECLINED, FINISHED, CANCELED
- `VALID_TRANSITIONS` aggiornato con `IssueStatus`:
  - **Rimuovere**: (NEW, PLANNED), (DECLINED, PLANNED) — non si salta piu' REASONING
  - **Aggiungere**: (REASONING, PLANNED) — unica via verso PLANNED
  - Le transizioni NEW→REASONING e DECLINED→REASONING restano gestite implicitamente da `create_spec()` nel service
  - Transizioni finali: (REASONING→PLANNED), (PLANNED→ACCEPTED), (PLANNED→DECLINED), (ACCEPTED→FINISHED), qualsiasi→CANCELED
- Relationship: `tasks = relationship("Task", back_populates="issue", cascade="all, delete-orphan", order_by="Task.order")`

**`models/project.py`** (aggiorna):
- Rinomina relationship: `tasks = relationship("Task", ...)` → `issues = relationship("Issue", back_populates="project")`

**`models/task.py`** (nuovo):
- Classe `Task` con `__tablename__ = "tasks"`
- Enum `TaskStatus`: PENDING, IN_PROGRESS, COMPLETED
- Campi: id, issue_id (FK), name, status, order, created_at, updated_at
- Relationship: `issue = relationship("Issue", back_populates="tasks")`
- `VALID_TASK_TRANSITIONS`: (PENDING→IN_PROGRESS), (IN_PROGRESS→COMPLETED)

### Schemas

**`schemas/issue.py`** (ex `schemas/task.py`):
- `IssueCreate(description, priority)`
- `IssueUpdate(description?, priority?)`
- `IssueStatusUpdate(status, decline_feedback?)`
- `IssueResponse(id, project_id, name, description, status, priority, specification, plan, recap, decline_feedback, tasks: list[TaskResponse] = [], created_at, updated_at)` — importa `TaskResponse` da `schemas/task.py`

**`schemas/task.py`** (nuovo):
- `TaskCreate(name)`
- `TaskBulkCreate(tasks: list[TaskCreate])`
- `TaskUpdate(name?, status?)`
- `TaskResponse(id, issue_id, name, status, order, created_at, updated_at)`

### Services

**`services/issue_service.py`** (ex `services/task_service.py`):
- Stessa logica, rinominata: `IssueService`
- Tutti i metodi restano identici nella semantica, solo nomi aggiornati
- `get_next_task()` → `get_next_issue()` (seleziona prossima issue per priorita')
- `decline_issue(issue_id, project_id, feedback)` — nuovo metodo, PLANNED → DECLINED con feedback (simmetrico ad `accept_issue`)
- `save_plan()` — rimuovere, metodo legacy gia' disabilitato nel MCP
- `get_for_project` usa `selectinload(Issue.tasks)` per eager loading dei task atomici

**`services/task_service.py`** (nuovo):
- `TaskService` per i task atomici
- `create_bulk(issue_id, tasks[{name}])` — crea task con ordine sequenziale
- `replace_all(issue_id, tasks[{name}])` — elimina tutti i task dell'issue e ricrea
- `update(task_id, **kwargs)` — aggiorna name e/o status con validazione transizioni
- `delete(task_id)` — elimina singolo task
- `list_by_issue(issue_id)` — lista ordinata per `order`

### Routers (REST API)

**`routers/issues.py`** (ex `routers/tasks.py`):

| Metodo | Endpoint | Azione |
|--------|----------|--------|
| POST | `/api/projects/{pid}/issues` | Crea issue |
| GET | `/api/projects/{pid}/issues` | Lista issues (filtro status opzionale) |
| GET | `/api/projects/{pid}/issues/{iid}` | Dettaglio issue (include tasks[]) |
| PUT | `/api/projects/{pid}/issues/{iid}` | Aggiorna campi |
| PATCH | `/api/projects/{pid}/issues/{iid}/status` | Aggiorna stato |
| DELETE | `/api/projects/{pid}/issues/{iid}` | Elimina issue (cascade tasks) |

**`routers/tasks.py`** (nuovo):

| Metodo | Endpoint | Azione |
|--------|----------|--------|
| POST | `/api/projects/{pid}/issues/{iid}/tasks` | Crea task in blocco |
| GET | `/api/projects/{pid}/issues/{iid}/tasks` | Lista tasks dell'issue |
| PATCH | `/api/projects/{pid}/issues/{iid}/tasks/{tid}` | Aggiorna singolo task (name/status) |
| DELETE | `/api/projects/{pid}/issues/{iid}/tasks/{tid}` | Elimina singolo task |
| PUT | `/api/projects/{pid}/issues/{iid}/tasks` | Sostituisci tutti i tasks |

### MCP Tools

**Issue tools** (rinominati):

| Tool | Parametri | Azione |
|------|-----------|--------|
| `get_issue_details` | project_id, issue_id | Ritorna tutti i campi + tasks[] |
| `get_issue_status` | project_id, issue_id | Ritorna id e stato |
| `set_issue_name` | project_id, issue_id, name | Imposta nome |
| `create_issue_spec` | project_id, issue_id, spec | Crea spec (NEW/DECLINED → REASONING) |
| `edit_issue_spec` | project_id, issue_id, spec | Modifica spec |
| `create_issue_plan` | project_id, issue_id, plan | Crea plan markdown (REASONING → PLANNED) |
| `edit_issue_plan` | project_id, issue_id, plan | Modifica plan |
| `accept_issue` | project_id, issue_id | PLANNED → ACCEPTED |
| `complete_issue` | project_id, issue_id, recap | ACCEPTED → FINISHED con recap |
| `decline_issue` | project_id, issue_id, feedback | PLANNED → DECLINED con feedback |
| `cancel_issue` | project_id, issue_id | → CANCELED |
| `get_project_context` | project_id | Invariato |

**Task tools** (nuovi):

| Tool | Parametri | Azione |
|------|-----------|--------|
| `create_plan_tasks` | issue_id, tasks[{name}] | Crea task atomici in blocco |
| `replace_plan_tasks` | issue_id, tasks[{name}] | Sostituisci tutti i task |
| `update_task_status` | task_id, status | Aggiorna stato (pending/in_progress/completed) |
| `update_task_name` | task_id, name | Rinomina singolo task |
| `delete_task` | task_id | Elimina singolo task |
| `get_plan_tasks` | issue_id | Lista task ordinati |

### default_settings.json

Aggiornare tutte le chiavi da `tool.{verb}_task_{noun}` a `tool.{verb}_issue_{noun}` e aggiungere le chiavi per i nuovi task tools.

### Terminal system — rename `task_id` → `issue_id`

Il sistema terminali e' collegato alle issue (ex task). Tutti i riferimenti a `task_id` diventano `issue_id`:

- **`schemas/terminal.py`**: `TerminalCreate.task_id` → `issue_id`, `TerminalResponse.task_id` → `issue_id`, `task_name` → `issue_name`
- **`services/terminal_service.py`**: parametro `task_id` → `issue_id`, deduplicazione per `issue_id`
- **`routers/terminals.py`**: query param `task_id` → `issue_id`, import `Task` → `Issue`, `db.get(Task, ...)` → `db.get(Issue, ...)`, enrichment dict key `task_name` → `issue_name`
- **`frontend/src/api/client.js`**: body di `createTerminal` cambia `{ task_id: ... }` → `{ issue_id: ... }`

## Frontend

### Rinomina file

| Attuale | Nuovo |
|---------|-------|
| `pages/NewTaskPage.jsx` | `pages/NewIssuePage.jsx` |
| `pages/TaskDetailPage.jsx` | `pages/IssueDetailPage.jsx` |
| `components/TaskList.jsx` | `components/IssueList.jsx` |

### API client (`api/client.js`)

```javascript
// Issues (ex Tasks)
listIssues: (projectId, status) => ...`/projects/${projectId}/issues`...
getIssue: (projectId, issueId) => ...`/projects/${projectId}/issues/${issueId}`...
createIssue: (projectId, data) => ...
updateIssue: (projectId, issueId, data) => ...
updateIssueStatus: (projectId, issueId, data) => ...
deleteIssue: (projectId, issueId) => ...

// Tasks (atomici)
listTasks: (projectId, issueId) => ...`/projects/${projectId}/issues/${issueId}/tasks`...
createTasks: (projectId, issueId, tasks) => ...POST
replaceTasks: (projectId, issueId, tasks) => ...PUT
updateTask: (projectId, issueId, taskId, data) => ...PATCH
deleteTask: (projectId, issueId, taskId) => ...DELETE

// Terminals — task_id → issue_id
listTerminals: (projectId, issueId) => ...
createTerminal: (issueId, projectId) => ...
```

### Routes (`App.jsx`)

```
/projects/:id/issues/new → NewIssuePage
/projects/:id/issues/:issueId → IssueDetailPage
```

### IssueDetailPage

Aggiungere sezione che mostra la lista dei task atomici con stato (checkbox o status badge).

### ProjectDetailPage / ProjectCard

Aggiornare label da "tasks" a "issues" e `task_counts` → `issue_counts`.

### StatusBadge

Aggiungere gestione dei nuovi valori `TaskStatus`: PENDING, IN_PROGRESS, COMPLETED (colori/icone distinti dagli `IssueStatus`).

### Pagine terminali

- `TaskDetailPage.jsx` (→ `IssueDetailPage.jsx`): `api.listTerminals(null, taskId)` → `api.listTerminals(null, issueId)`
- `ProjectDetailPage.jsx`: `activeTerminalTaskIds` → `activeTerminalIssueIds`
- `TerminalsPage.jsx`: label aggiornate da "task" a "issue"

## Regola di naming

- **"issue"**: il contenitore top-level (ex "task") — spec, plan, recap
- **"task"**: i passi atomici strutturati dentro al plan di un issue
- Quando nel codice si legge "task" deve riferirsi SOLO ai task atomici
- **Import**: tutti gli import del vecchio `Task` (ora `Issue`) nel codebase devono essere aggiornati. `models/__init__.py` esporta sia `Issue` che `Task` (il nuovo modello atomico)

## File coinvolti (~40)

### Backend (crea/rinomina)
- `models/issue.py` (rinomina da task.py)
- `models/task.py` (nuovo)
- `models/project.py` (aggiorna relationship)
- `models/__init__.py`
- `schemas/issue.py` (rinomina da task.py)
- `schemas/task.py` (nuovo)
- `schemas/project.py` (rename `task_counts` → `issue_counts`)
- `schemas/terminal.py` (rename `task_id` → `issue_id`)
- `services/issue_service.py` (rinomina da task_service.py)
- `services/task_service.py` (nuovo)
- `services/project_service.py` (rename `get_task_counts` → `get_issue_counts`)
- `services/terminal_service.py` (rename `task_id` → `issue_id`)
- `routers/issues.py` (rinomina da tasks.py)
- `routers/tasks.py` (nuovo)
- `routers/projects.py` (aggiorna enrichment + rename)
- `routers/terminals.py` (rename `task_id` → `issue_id`)
- `mcp/server.py`
- `mcp/default_settings.json`
- `main.py`
- `alembic/versions/xxx_rename_tasks_to_issues.py` (nuova migration)

### Backend test (crea/rinomina)
- `tests/test_issue_service.py` (rinomina)
- `tests/test_task_service.py` (nuovo)
- `tests/test_routers_issues.py` (rinomina)
- `tests/test_routers_tasks.py` (nuovo)
- `tests/test_mcp_tools.py`
- `tests/test_project_service.py`
- `tests/test_routers_projects.py`
- `tests/test_terminal_service.py`
- `tests/test_terminal_router.py`
- `tests/conftest.py`

### Frontend
- `api/client.js`
- `pages/NewIssuePage.jsx` (rinomina da NewTaskPage.jsx)
- `pages/IssueDetailPage.jsx` (rinomina da TaskDetailPage.jsx)
- `pages/ProjectDetailPage.jsx`
- `pages/TerminalsPage.jsx`
- `components/IssueList.jsx` (rinomina da TaskList.jsx)
- `components/ProjectCard.jsx`
- `components/StatusBadge.jsx`
- `App.jsx`
