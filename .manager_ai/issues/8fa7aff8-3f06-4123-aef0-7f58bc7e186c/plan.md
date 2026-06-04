# Implementation Plan: Export/Import Agents and Pipelines

## Architecture Overview

Two-phase import (upload→preview→confirm), single-phase export (GET→download JSON). 
Backend: new service methods + router endpoints on existing routers.
Frontend: new API hooks + ImportPreviewModal component + export/import buttons on AgentsTab/PipelinesTab.

---

## Phase 1: Backend Schemas

**Files to create/modify:**
- `backend/app/schemas/export_import.py` (NEW)

**Schemas:**
```
ExportWrapper(type: Literal["agents","pipelines"], version: int=1, exported_at: str, items: list[dict])
AgentExportItem — subset of AgentResponse without created_at/updated_at
PipelineStepExportItem — PipelineStepResponse + agent: AgentExportItem (inline resolved agent)
PipelineExportItem — id, name, steps: list[PipelineStepExportItem]
ImportPreviewResponse(conflicts: list[ImportConflict], new: list, total: int)
AgentImportConflict(incoming: AgentExportItem, existing: AgentExportItem)
PipelineImportPreviewResponse(conflicts, new, missing_agents: list[{agent_id, name}], total)
ImportConflictAction(value: Literal["skip","overwrite"])  — per conflict ID
ImportConfirmRequest(file: Upload, conflicts: str)  — multipart form
ImportConfirmResponse(imported: int, skipped: int, errors: list[str])
```

**Why new file:** Keeps agent/pipeline schemas clean. Shared pattern.

---

## Phase 2: Backend Service Methods

### `backend/app/services/agent_service.py`

Add methods:
- `export_all() -> list[Agent]` — `select(Agent).order_by(Agent.name)`
- `export_by_id(agent_id: str) -> Agent` — reuse existing `get_by_id`, returns full ORM model
- `import_agents(agents_data: list[dict], conflict_map: dict[str, str], db_session) -> ImportConfirmResponse`
  - Parse conflict_map (JSON string → dict)
  - For each agent in agents_data:
    - If ID exists in DB and conflict_map says "overwrite": update all fields
    - If ID exists and conflict_map says "skip" (or missing): skip
    - If ID not in DB: create new agent
  - Return imported/skipped counts + errors list
  - IMPORTANT: use `allowed_tools` parsed as JSON list from file, `intent` as text, `model` nullable

### `backend/app/services/pipeline_service.py`

Add methods:
- `export_all() -> list[Pipeline]` — `select(Pipeline).options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent)).order_by(Pipeline.name)` (3-level eager load to get agent data in steps)
- `export_by_id(pipeline_id: str) -> Pipeline` — same eager loading pattern
- `import_pipelines(pipelines_data: list[dict], conflict_map: dict[str, str]) -> ImportConfirmResponse`
  - For each pipeline in pipelines_data:
    - If ID exists and "overwrite": delete existing steps (via cascade), update pipeline name, recreate steps with imported order_index and agent_id
    - If ID exists and "skip": skip
    - If ID not in DB: create pipeline with steps
  - For each step's `agent` field: create or update the referenced agent first (via AgentService)
  - If any step references an agent not in DB and not in file data: add to errors list, skip that pipeline
  - Return counts

**Important detail for add_step:** Current `add_step` ignores passed `order_index` and auto-computes. Need to either:
- Modify `add_step` to respect explicit `order_index` when > 0
- Or create `set_steps(pipeline_id, steps: list[dict])` that bulk-replaces steps with exact order_index

---

## Phase 3: Backend Router Endpoints

### `backend/app/routers/agents.py`

Add endpoints:

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/api/agents/export` | `export_agents_all` | Returns JSON with Content-Disposition: attachment |
| GET | `/api/agents/export/{agent_id}` | `export_agent_single` | 404 if not found |
| POST | `/api/agents/import/preview` | `import_agents_preview` | Multipart file upload → parse → check conflicts |
| POST | `/api/agents/import/confirm` | `import_agents_confirm` | Multipart file + conflicts JSON → apply |

**Export response pattern:**
```python
from fastapi.responses import Response
agents_data = [format_agent_for_export(a) for a in svc.export_all()]
wrapper = {"version": 1, "type": "agents", "exported_at": datetime.utcnow().isoformat() + "Z", "items": agents_data}
return Response(content=json.dumps(wrapper, indent=2), media_type="application/json",
    headers={"Content-Disposition": f'attachment; filename="agents-export.json"'})
```

**Import preview logic:**
1. Parse uploaded .json file
2. Validate wrapper format (version=1, type="agents")
3. For each item, check if ID exists in DB — separate into `conflicts` (exists) and `new` (not exists)
4. Return ImportPreviewResponse

**Import confirm logic:**
1. Re-parse the uploaded .json file (file is re-uploaded, not stored server-side)
2. Parse conflicts JSON string → dict
3. Call `svc.import_agents(items, conflict_map)`
4. Commit, return ImportConfirmResponse
5. On error: raise appropriate AppError with details

### `backend/app/routers/pipelines.py`

Add endpoints (same pattern):

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| GET | `/api/pipelines/export` | `export_pipelines_all` | With eager-loaded agent data |
| GET | `/api/pipelines/export/{pipeline_id}` | `export_pipeline_single` | 404 if not found |
| POST | `/api/pipelines/import/preview` | `import_pipelines_preview` | Also checks missing agent deps |
| POST | `/api/pipelines/import/confirm` | `import_pipelines_confirm` | Creates/updates agent refs too |

**Pipeline export format — each step gets inline `agent` field:**
```python
{
  "id": pipeline.id,
  "name": pipeline.name,
  "steps": [{
    "id": step.id,
    "agent_id": step.agent_id,
    "order_index": step.order_index,
    "agent": {
      "id": step.agent.id,
      "name": step.agent.name,
      "model": step.agent.model,
      "allowed_tools": step.agent.allowed_tools,
      "intent": step.agent.intent
    }
  }]
}
```

**Preview also checks:** for each pipeline step, does the referenced agent exist in DB or in the import file? Flag missing ones.

---

## Phase 4: Frontend Types & API Client

### `frontend/src/shared/types/index.ts`

Add types:
```typescript
interface AgentExportItem { id, name, model, allowed_tools, intent }
interface PipelineStepExportItem { id, pipeline_id, agent_id, order_index, agent: AgentExportItem }
interface PipelineExportItem { id, name, steps: PipelineStepExportItem[] }
interface ExportWrapper<T> { version: number, type: string, exported_at: string, items: T[] }
interface ImportConflict<T> { incoming: T, existing: T }
interface ImportPreviewResponse<T> { conflicts: ImportConflict<T>[], new: T[], total: number }
interface PipelineImportPreviewResponse extends ImportPreviewResponse<PipelineExportItem> { missing_agents: { agent_id: string, name: string }[] }
interface ImportConfirmResponse { imported: number, skipped: number, errors: string[] }
```

### `frontend/src/features/agents/api.ts`

Add functions:
```typescript
exportAgents(): Promise<Blob>  — fetch GET /agents/export as blob (not JSON)
exportAgent(agentId): Promise<Blob> — GET /agents/export/{agentId}
importAgentsPreview(file: File): Promise<ImportPreviewResponse<AgentExportItem>> — uploadRequest POST /agents/import/preview
importAgentsConfirm(file: File, conflicts: Record<string, string>): Promise<ImportConfirmResponse> — uploadRequest POST /agents/import/confirm
```

### `frontend/src/features/pipelines/api.ts`

Add functions (same pattern):
```typescript
exportPipelines(): Promise<Blob>
exportPipeline(pipelineId): Promise<Blob>
importPipelinesPreview(file: File): Promise<PipelineImportPreviewResponse>
importPipelinesConfirm(file: File, conflicts: Record<string, string>): Promise<ImportConfirmResponse>
```

**Download helper (shared):**
```typescript
// In a shared util or inline in hooks:
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
```

---

## Phase 5: Frontend Hooks

### `frontend/src/features/agents/hooks.ts`

Add hooks:
```typescript
useExportAgents() — useMutation({ mutationFn: () => api.exportAgents(), onSuccess: (blob) => downloadBlob(blob, "agents-export.json") })
useExportAgent(agentId) — useMutation({ mutationFn: () => api.exportAgent(agentId), onSuccess: (blob) => downloadBlob(blob, `agent-${agentId}.json`) })
useImportAgentsPreview() — useMutation({ mutationFn: (file) => api.importAgentsPreview(file) })
useImportAgentsConfirm() — useMutation({ mutationFn: ({ file, conflicts }) => api.importAgentsConfirm(file, conflicts), onSuccess: () => { invalidate agentKeys.all(); toast.success(...) } })
```

### `frontend/src/features/pipelines/hooks.ts`

Same pattern — `useExportPipelines`, `useExportPipeline`, `useImportPipelinesPreview`, `useImportPipelinesConfirm`.

---

## Phase 6: Frontend — ImportPreviewModal Component

**New file:** `frontend/src/shared/components/ImportPreviewModal.tsx`

A generic modal component that works for both agents and pipelines:

```
Props:
  isOpen: boolean
  onClose: () => void
  title: string (e.g. "Import Agents" / "Import Pipelines")
  previewData: ImportPreviewResponse<T> | PipelineImportPreviewResponse | null
  isLoading: boolean
  error: string | null
  onConfirm: (conflicts: Record<string, string>) => void
  isConfirming: boolean

State:
  conflictChoices: Record<string, "skip" | "overwrite"> (default all "skip")

Layout:
  Header: title + item count
  Error section (if error): red banner with message, retry button
  Loading state: spinner
  Sections (when data loaded):
    - Green section: "New items (X)" — list of names/IDs
    - Yellow section: "Conflicts (X)" — each with dropdown select (Skip/Overwrite) + compact diff
    - Red section (pipelines only): "Missing agent dependencies (X)" — warning list
  Footer:
    - Cancel button
    - Confirm button: "Confirm Import (X items)" — disabled if no items to import
      Shows spinner when isConfirming
```

**No new file needed** if we keep it simple and inline in each tab. But for DRY, a shared component in `shared/components/` is better. The spec reviewer can decide.

---

## Phase 7: Frontend — AgentsTab & PipelinesTab Updates

### `frontend/src/features/agents/components/AgentsTab.tsx`

Changes:
1. **Toolbar buttons** — add "Export All" and "Import" buttons next to existing buttons
2. **Row actions** — add download/export icon button to each agent row
3. **Import state** — `useState` for import modal open, preview data, file reference
4. **Import flow**:
   - "Import" click → hidden `<input type="file" accept=".json">` opens
   - File selected → `importAgentsPreview.mutate(file)` → preview modal appears
   - User resolves conflicts → confirm import
   - Success → toast + refetch list
5. **Export flow**:
   - "Export All" click → `exportAgents.mutate()` → blob downloads
   - Row export click → `exportAgent.mutate(agentId)` → blob downloads
6. **Error states**: toast on export error, modal shows preview error

### `frontend/src/features/pipelines/components/PipelinesTab.tsx`

Same pattern:
1. Toolbar: "Export All" + "Import" buttons
2. Pipeline card actions: export icon per pipeline
3. Same import flow with preview modal
4. Pipeline-specific: missing_agents warning section in preview

---

## Phase 8: Backend Tests

### `backend/tests/test_routers_agents.py` (new file or add to existing)

Tests for:
- `GET /api/agents/export` — returns valid JSON with all agents
- `GET /api/agents/export/{id}` — returns single agent
- `GET /api/agents/export/{id}` non-existent — 404
- `POST /api/agents/import/preview` — valid file returns conflicts/new
- `POST /api/agents/import/preview` — invalid JSON → 400
- `POST /api/agents/import/confirm` — import new agents
- `POST /api/agents/import/confirm` — overwrite existing agent
- `POST /api/agents/import/confirm` — skip existing agent

### `backend/tests/test_routers_pipelines.py` (new or add to existing)

Tests for:
- `GET /api/pipelines/export` — returns pipelines with inline agent data
- `POST /api/pipelines/import/preview` — detects missing agent deps
- `POST /api/pipelines/import/confirm` — imports pipeline with agent creation
- Conflict resolution for pipelines

---

## Dependency Order

```
Phase 1 (Schemas) ──→ Phase 2 (Services) ──→ Phase 3 (Routers)
                                                │
Phase 4 (Frontend Types + API) ──→ Phase 5 (Hooks) ──→ Phase 6 (Modal) ──→ Phase 7 (Tab UI)
                                                │
Phase 8 (Tests) ──→ can start after Phase 3
```

Phases 1→3 and 4→7 can run in parallel (backend/frontend are independent).

---

## Key Gotchas & Constraints

1. **PipelineService.add_step ignores order_index** — always auto-computes max+1. For import, either modify to respect explicit `order_index > 0`, or add a new bulk `set_steps` method.
2. **Pipeline import cascade**: deleting a pipeline cascades to step_runs. Import overwrite should warn if pipeline has runs (or just proceed — low risk per spec).
3. **File re-parsing**: confirm endpoints re-parse the uploaded file (not stored server-side). The same file must be re-uploaded in the confirm request.
4. **Export wrapper format**: pipeline export uses `"pipelines"` (plural) per spec review fix. Agent export uses `"agents"`.
5. **No timestamps in agent export**: `created_at`/`updated_at` omitted from export items.
6. **Pipeline step order**: imported steps must preserve `order_index` exactly as in the file. Direct table manipulation (delete+recreate) rather than using `add_step` auto-assignment.
7. **JSON serialization**: `allowed_tools` and `intent` fields — `intent` is TEXT in DB but string in JSON. `allowed_tools` is JSON already.
