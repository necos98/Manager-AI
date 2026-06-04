## Implementation Plan: Export/Import Agents & Pipelines

### Architecture Overview

3 new backend REST endpoints, new schemas, and frontend export/import controls plus conflict modal. No new pages. No new models. No new DB tables.

### Files to Create
1. `backend/app/schemas/export_import.py` — Pydantic models for export/import payloads
2. `frontend/src/features/conflicts/ConflictModal.tsx` — Shared conflict resolution component
3. `frontend/src/features/agents/api.export.ts` — Agent export API functions
4. `frontend/src/features/pipelines/api.export.ts` — Pipeline export API functions
5. `frontend/src/features/export/hooks.ts` — Shared export/import React Query hooks

### Files to Modify
1. `backend/app/routers/agents.py` — Add export endpoint
2. `backend/app/routers/pipelines.py` — Add export endpoint
3. `backend/app/routers/__init__.py` or add `backend/app/routers/import_export.py` — Add import endpoint (+ main.py if new router)
4. `backend/app/services/agent_service.py` — Add `get_by_names()` batch lookup
5. `backend/app/services/pipeline_service.py` — Add `get_by_name()` and `get_pipeline_with_agents()`
6. `frontend/src/features/agents/components/AgentsTab.tsx` — Add checkboxes, export buttons, import zone
7. `frontend/src/features/pipelines/components/PipelinesTab.tsx` — Add checkboxes, export buttons, import zone
8. `frontend/src/features/agents/api.ts` — Add exportAgent/import functions
9. `frontend/src/features/pipelines/api.ts` — Add exportPipeline/import functions
10. `frontend/src/features/agents/hooks.ts` — Add export/import mutations
11. `frontend/src/features/pipelines/hooks.ts` — Add export/import mutations

---

### Step 1: Backend Schemas — `backend/app/schemas/export_import.py`

```python
class ExportedAgent(BaseModel):
    id: str
    name: str
    model: str | None = None
    allowed_tools: list[str] | None = None
    intent: str = ""
    created_at: str | None = None
    updated_at: str | None = None

class ExportedPipelineStep(BaseModel):
    order_index: int
    agent: ExportedAgent  # inline full agent data

class ExportedPipeline(BaseModel):
    id: str
    name: str
    steps: list[ExportedPipelineStep]
    created_at: str | None = None
    updated_at: str | None = None

class ExportPayload(BaseModel):
    version: str = "1.0"
    exported_at: str
    agents: list[ExportedAgent] = []
    pipelines: list[ExportedPipeline] = []

class ImportConflict(BaseModel):
    name: str
    type: str  # "agent" | "pipeline"
    existing_id: str
    will_overwrite: bool = False

class ImportRequest(BaseModel):
    file_content: str  # JSON string uploaded

class ImportResult(BaseModel):
    created_agents: int
    updated_agents: int
    skipped_agents: int
    created_pipelines: int
    updated_pipelines: int
    skipped_pipelines: int
    conflicts: list[ImportConflict]
    errors: list[str] = []

class ConflictResolveRequest(BaseModel):
    overwrite_ids: list[str]  # IDs of entities to overwrite
    file_content: str
```

### Step 2: Backend Export Endpoints

#### `backend/app/routers/agents.py` — add `POST /api/agents/export`
- Accept JSON body `{agent_ids: list[str]}` (empty = export all)
- Fetch agents by IDs (or all if empty)
- Return `ExportPayload` with `agents` populated, `pipelines` empty

#### `backend/app/routers/pipelines.py` — add `POST /api/pipelines/export`
- Accept JSON body `{pipeline_ids: list[str]}` (empty = export all)
- Fetch pipelines with eager-loaded steps + agent data
- Inline full agent data in each step's `agent` key
- Return `ExportPayload` with `pipelines` populated, `agents` empty

### Step 3: Backend Import Endpoint

New file or in `backend/app/routers/agents.py`:

#### `POST /api/import` (initial detection pass) OR `POST /api/import/resolve` (conflict resolution)

**V1 — Single-pass import with inline conflict response:**
- Accept `{file_content: string}`
- Parse JSON, validate version/format
- Extract agents array and pipelines array
- For each agent: check if name exists via `AgentService.get_by_name()`
  - If exists: add to `conflicts` list
  - If not: create with new UUID
- For each pipeline: check if name exists via `PipelineService.get_by_name()`
  - If exists: add to `conflicts` list
  - If not: check referenced agents, create missing ones, create pipeline
- If no conflicts: commit and return counts
- If conflicts: return `ImportResult` with conflict list, **don't commit** (rollback)

**V2 — Conflict resolution:**
- Accept `{file_content: string, overwrite_ids: list[str]}`
- Re-parse file
- For agents in conflicts and in overwrite_ids: update existing agent
- For pipelines in conflicts and in overwrite_ids: update existing pipeline
- For entities not in conflicts: import normally
- Commit, return final counts

### Step 4: Backend Service Additions

#### `AgentService`:
```python
async def get_by_names(self, names: list[str]) -> dict[str, Agent]:
    """Batch lookup by name. Returns dict of name -> Agent."""
```

#### `PipelineService`:
```python
async def get_by_name(self, name: str) -> Pipeline | None:
    """Find pipeline by name."""
```

### Step 5: Frontend — Shared Types & API

Add export/import types to `frontend/src/shared/types/index.ts`:
```typescript
interface ExportedAgent { ... }
interface ExportedPipelineStep { ... }
interface ExportedPipeline { ... }
interface ExportPayload { ... }
interface ImportConflict { ... }
interface ImportResult { ... }
```

### Step 6: Frontend — AgentsTab Export

**Checkbox column**: Add `<input type="checkbox">` to each table row, track `selectedAgents: Set<string>`.

**Export Selected button**: When clicked, POST selected IDs to `/agents/export`, receive JSON, trigger browser download via `URL.createObjectURL(new Blob([json], {type: 'application/json'}))`.

**Export All button**: POST empty list to `/agents/export`, same download logic.

### Step 7: Frontend — PipelinesTab Export

Same pattern but for pipelines. Checkbox on each card header, Export Selected + Export All in header toolbar.

### Step 8: Frontend — Import Zone (shared component pattern on each tab)

Drop zone component:
- Drag-and-drop area with dashed border
- "Click to browse" file picker button
- Accept `.json` only
- On file select/drop: read file content, POST to `/import`
- If response has conflicts: show `ConflictModal`
- If no conflicts: show success toast with counts

### Step 9: Frontend — ConflictModal Component

Props: `conflicts: ImportConflict[], onResolve: (overwrite_ids: string[]) => void, onCancel: () => void`

UI:
- Modal title: "Import Conflicts Found"
- List each conflict with entity name, type badge, existing info
- Each row has a checkbox labeled "Overwrite"
- "Select All" / "Deselect All" toggle
- Import button (disabled if nothing selected) + Cancel button
- On Import: POST to `/import/resolve` with selected overwrite IDs

### Step 10: Frontend — React Query Hooks

- `useExportAgents()` — mutation
- `useExportPipelines()` — mutation
- `useImportEntities()` — mutation (calls `/import` first pass)
- `useResolveImport()` — mutation (calls `/import/resolve`)

All invalidate `agentKeys.all()` and `pipelineKeys.all()` on success.

### Implementation Order (Tasks)

1. Create backend schemas for export/import
2. Add `get_by_names()` to AgentService and `get_by_name()` to PipelineService
3. Add agent export endpoint
4. Add pipeline export endpoint
5. Add import endpoint (two-phase: detection + resolution)
6. Add export/import types to frontend shared types
7. Add export/import API functions and React Query hooks
8. Add export controls and import zone to AgentsTab
9. Add export controls and import zone to PipelinesTab
10. Build ConflictModal component
11. Wire up conflict resolution flow
12. Test full flow end-to-end
