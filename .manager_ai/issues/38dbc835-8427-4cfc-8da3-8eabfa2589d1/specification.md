## Specifica: Bulk actions su Kanban board

### 1. Obiettivo

Aggiungere la possibilità di selezionare più issue sulla Kanban board ed eseguire azioni bulk: cambio status, assegnazione tags, cancellazione, cambio priority, cambio category. Ogni azione deve validare le transizioni consentite e mostrare feedback appropriato.

### 2. Backend — API REST

#### 2.1 Nuovo endpoint: `PATCH /api/projects/{project_id}/issues/bulk/status`

- **Request body:**
  ```json
  {
    "issue_ids": ["uuid1", "uuid2"],
    "status": "Planned"
  }
  ```
- **Response:** `{ "updated": 2, "errors": { "uuid3": "Invalid transition" } }`
- **Comportamento:** Itera sulle issue, chiama `update_status` per ciascuna. Raccoglie errori senza fermarsi (best-effort). Se tutte falliscono, ritorna 400 con `{ "updated": 0, "errors": { ... } }`.

#### 2.2 Nuovo endpoint: `PATCH /api/projects/{project_id}/issues/bulk/tags`

- **Request body:**
  ```json
  {
    "issue_ids": ["uuid1", "uuid2"],
    "tags": ["bug", "frontend"],
    "mode": "add" | "remove" | "set"
  }
  ```
- **Response:** `{ "updated": 2, "errors": {} }`
- **Comportamento:** `add` aggiunge tags alla lista esistente (deduplica). `remove` rimuove. `set` sostituisce completamente.

#### 2.3 Nuovo endpoint: `POST /api/projects/{project_id}/issues/bulk/delete`

- **Request body:**
  ```json
  {
    "issue_ids": ["uuid1", "uuid2"]
  }
  ```
- **Response:** `{ "deleted": 2, "errors": {} }`

#### 2.4 Nuovo endpoint: `PATCH /api/projects/{project_id}/issues/bulk/priority`

- **Request body:**
  ```json
  {
    "issue_ids": ["uuid1", "uuid2"],
    "priority": 1
  }
  ```
- **Response:** `{ "updated": 2, "errors": {} }`

#### 2.5 Nuovo endpoint: `PATCH /api/projects/{project_id}/issues/bulk/category`

- **Request body:**
  ```json
  {
    "issue_ids": ["uuid1", "uuid2"],
    "category": "feature" | null
  }
  ```
- **Response:** `{ "updated": 2, "errors": {} }`

#### 2.6 Schemas

Aggiungere in `backend/app/schemas/issue.py`:
- `BulkStatusUpdate` — issue_ids list, status
- `BulkTagsUpdate` — issue_ids, tags, mode enum (add|remove|set)
- `BulkDeleteRequest` — issue_ids
- `BulkPriorityUpdate` — issue_ids, priority
- `BulkCategoryUpdate` — issue_ids, category (nullable)
- `BulkResponse` — updated/deleted int, errors dict

#### 2.7 Service

Aggiungere in `issue_service.py` metodi:
- `bulk_update_status(project_id, issue_ids, status) -> dict`
- `bulk_update_tags(project_id, issue_ids, tags, mode) -> dict`
- `bulk_delete(project_id, issue_ids) -> dict`
- `bulk_update_priority(project_id, issue_ids, priority) -> dict`
- `bulk_update_category(project_id, issue_ids, category) -> dict`

Ogni metodo itera e chiama i metodi esistenti (update_status, update_fields, delete). Non c'è logica di transazione — ogni operazione è atomica sul singolo issue.

#### 2.8 Router

Nuovo file `backend/app/routers/issues_bulk.py` con prefisso `/api/projects/{project_id}/issues/bulk`. Registrato in `main.py`.

### 3. Frontend — Componenti UI

#### 3.1 Stato di selezione nella KanbanBoard

- Nuovo stato `selectMode: boolean` in KanbanBoard
- Nuovo stato `selectedIssueIds: Set<string>` in KanbanBoard
- Pulsante "Select" nella toolbar (accanto ai filtri) che attiva selectMode
- In selectMode: compare un pulsante "Cancel" per uscire dalla modalità
- Counter "N selected" quando 1+ card sono selezionate

#### 3.2 Checkbox su KanbanCard

- In selectMode: mostra una checkbox all'inizio di ogni card (lato sinistro del contenuto)
- Click sulla checkbox: toggle selezione
- Click sulla card (non sulla checkbox): naviga alla issue come sempre
- La card selezionata ha un effetto visivo (ring/border highlight)

#### 3.3 BulkActionBar (nuovo componente)

- `BulkActionBar` — barra sticky sopra/fissa in basso che appare quando 1+ card è selezionata
- Contiene:
  - **Count** "3 issues selected"
  - **Change Status** — dropdown con tutte le status validi, poi conferma
    - Per ogni issue selezionata, valida la transizione individualmente
    - Chiama `PATCH /api/projects/{project_id}/issues/bulk/status`
  - **Assign Tags** — apre il TagInput esistente in modalità multi-selezione
    - Mostra opzione radio: Add / Remove / Set
    - Chiama `PATCH /api/projects/{project_id}/issues/bulk/tags`
  - **Change Priority** — dropdown numerico 1-5
    - Chiama `PATCH /api/projects/{project_id}/issues/bulk/priority`
  - **Change Category** — dropdown con categorie disponibili + "None"
    - Chiama `PATCH /api/projects/{project_id}/issues/bulk/category`
  - **Delete** — pulsante rosso con dialogo di conferma
    - Chiama `POST /api/projects/{project_id}/issues/bulk/delete`
  - **Deselect all** — deseleziona tutto

#### 3.4 Select all in column

- In selectMode: header di ogni colonna mostra checkbox "Select all"
- Click seleziona/deseleziona tutte le card visibili in quella colonna

#### 3.5 API hooks

Nuovo file `frontend/src/features/issues/hooks-bulk.ts`:
- `useBulkUpdateStatus(projectId)` — mutation per bulk status
- `useBulkUpdateTags(projectId)` — mutation per bulk tags
- `useBulkDelete(projectId)` — mutation per bulk delete
- `useBulkUpdatePriority(projectId)` — mutation per bulk priority
- `useBulkUpdateCategory(projectId)` — mutation per bulk category

Ogni mutation invalida `issueKeys.all(projectId)` dopo il successo.

#### 3.6 API functions

Nuovo file `frontend/src/features/issues/api-bulk.ts`:
- `bulkUpdateStatus(projectId, data)`
- `bulkUpdateTags(projectId, data)`
- `bulkDeleteIssues(projectId, data)`
- `bulkUpdatePriority(projectId, data)`
- `bulkUpdateCategory(projectId, data)`

### 4. Transizioni e validazione

Le transizioni di status permesse sono quelle già definite in `kanban-board.tsx` (`VALID_TRANSITIONS`):
- New → Reasoning, Reasoning → Planned, Planned → Accepted, Accepted → Finished
- Qualunque status → Canceled

Il backend valida usando `IssueService.update_status()` già esistente.

### 5. Non incluso (scope escluso)

- Non si modifica il backend existing `list_by_project` endpoint
- Non si tocca il sistema di drag & drop esistente
- Non si aggiungono shortcut da tastiera per selezione multipla
- Non si implementa bulk per la creazione di issue
