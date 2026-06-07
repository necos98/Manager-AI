# Implementation Plan: Export selettivo di Agenti e Pipeline con Save-As dialog

## Overview

Add checkbox-based multi-select export for Agents and Pipelines with Save-As dialog (`showSaveFilePicker` + fallback). Backend: two new POST batch endpoints. Frontend: shared `saveFile` utility, checkbox selection in both tabs, new hooks and API functions.

## Backend Changes

### 1. Batch export request schemas — `backend/app/schemas/export_import.py`

Add two Pydantic models:

```python
class AgentBatchExportRequest(BaseModel):
    agent_ids: list[str]

class PipelineBatchExportRequest(BaseModel):
    pipeline_ids: list[str]
```

### 2. Batch export services — `backend/app/services/agent_service.py` and `backend/app/services/pipeline_service.py`

**AgentService.export_batch(agent_ids: list[str])**:
- `SELECT * FROM agents WHERE id IN :agent_ids` via `select(Agent).where(Agent.id.in_(agent_ids))`
- Call `format_agent_export()` on each result
- Non-existent IDs skipped silently (SQL IN clause naturally ignores them)
- Return list of formatted dicts

**PipelineService.export_batch(pipeline_ids: list[str])**:
- `select(Pipeline).where(Pipeline.id.in_(pipeline_ids)).options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))`
- Same silent-skip for non-existent IDs
- Call `format_pipeline_export()` on each result
- Return list of formatted dicts

### 3. Batch export endpoints — `backend/app/routers/agents.py` and `backend/app/routers/pipelines.py`

**POST /api/agents/export/batch** (agents.py):
```python
@router.post("/export/batch")
async def export_agents_batch(request: AgentBatchExportRequest):
    if not request.agent_ids:
        raise HTTPException(400, "agent_ids must not be empty")
    items = await AgentService.export_batch(db, request.agent_ids)
    wrapper = build_export_wrapper("agents", items)
    return Response(
        content=json.dumps(wrapper, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=agents-export.json"}
    )
```

**POST /api/pipelines/export/batch** (pipelines.py):
Same pattern, filename `pipelines-export.json`.

## Frontend Changes

### 4. Shared utility: `downloadBlob` — `frontend/src/shared/utils/download.ts`

Extract the duplicated `downloadBlob` function from agents/hooks.ts and pipelines/hooks.ts into a shared file:

```typescript
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
```

### 5. Shared utility: `saveFile` — `frontend/src/shared/utils/saveFile.ts`

New function that tries native Save-As dialog, falls back to downloadBlob:

```typescript
import { downloadBlob } from "./download";

export async function saveFile(blob: Blob, defaultFilename: string) {
  if ("showSaveFilePicker" in window) {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName: defaultFilename });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return;
    } catch (err) {
      // User cancelled the save dialog — do nothing
      if (err instanceof DOMException && err.name === "AbortError") return;
      // Otherwise fall through to fallback
    }
  }
  // Fallback: downloadBlob for browsers without File System Access API
  downloadBlob(blob, defaultFilename);
}
```

### 6. Remove local `downloadBlob` from hooks files

- `frontend/src/features/agents/hooks.ts` — remove lines 6-13, import `downloadBlob` from `@/shared/utils/download` and `saveFile` from `@/shared/utils/saveFile`
- `frontend/src/features/pipelines/hooks.ts` — same treatment

### 7. Agents batch export API — `frontend/src/features/agents/api.ts`

Add:
```typescript
export async function exportAgentsBatch(agentIds: string[]): Promise<Blob> {
  const res = await fetch(buildUrl("/agents/export/batch"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agent_ids: agentIds }),
  });
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  return res.blob();
}
```

### 8. Agents batch export hook — `frontend/src/features/agents/hooks.ts`

Add new hook. Imports `saveFile` from shared utils. Uses `toast.success()` to notify user of completion per spec R5:

```typescript
export function useExportAgentsBatch() {
  return useMutation({
    mutationFn: (agentIds: string[]) => api.exportAgentsBatch(agentIds),
    onSuccess: (blob, agentIds) => {
      saveFile(blob, "agents-export.json");
      toast.success(`Exported ${agentIds.length} agent${agentIds.length === 1 ? '' : 's'}`);
    },
    onError: onMutationError,
  });
}
```

Also update `useExportAgents` and `useExportAgent` to import `downloadBlob` from shared utils instead of local.

### 9. AgentsTab checkbox selection — `frontend/src/features/agents/components/AgentsTab.tsx`

Changes:
- Add `selectedIds` state: `const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())`
- Import `useExportAgentsBatch` hook
- Add checkbox column to `<thead>`:
  - First `<th>` with `<input type="checkbox">` for select-all (checked = all visible rows selected, use ref for indeterminate state = partial selection)
- Add checkbox to each `<tr>` in `<tbody>`:
  - First `<td>` with checkbox input
  - `onChange` toggles ID in selectedIds set
- Show counter in header: `<span className="text-sm text-muted-foreground">{selectedIds.size} selected</span>`
- Add "Export Selected" `<Button>` next to "Export All":
  - `disabled={selectedIds.size === 0 || exportAgentsBatch.isPending}`
  - Shows spinner when pending
  - `onClick` calls `exportAgentsBatch.mutate([...selectedIds])`
- Keep existing "Export All" and per-row export buttons unchanged

### 10. Pipelines batch export API — `frontend/src/features/pipelines/api.ts`

Add:
```typescript
export async function exportPipelinesBatch(pipelineIds: string[]): Promise<Blob> {
  const res = await fetch(buildUrl("/pipelines/export/batch"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pipeline_ids: pipelineIds }),
  });
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  return res.blob();
}
```

### 11. Pipelines batch export hook — `frontend/src/features/pipelines/hooks.ts`

Add new hook. Same pattern as agents — imports `saveFile` and `toast.success()`:

```typescript
export function useExportPipelinesBatch() {
  return useMutation({
    mutationFn: (pipelineIds: string[]) => api.exportPipelinesBatch(pipelineIds),
    onSuccess: (blob, pipelineIds) => {
      saveFile(blob, "pipelines-export.json");
      toast.success(`Exported ${pipelineIds.length} pipeline${pipelineIds.length === 1 ? '' : 's'}`);
    },
    onError: onMutationError,
  });
}
```

### 12. PipelinesTab checkbox selection — `frontend/src/features/pipelines/components/PipelinesTab.tsx`

Changes:
- Add `selectedIds` state
- Import `useExportPipelinesBatch` hook
- Add checkbox to each pipeline card header (left side, before the expand/collapse button)
- Add header-level select-all checkbox next to the section title
- Show counter in header bar
- Add "Export Selected" button next to "Export All"
- Keep existing single-export per card

## Data Flow

```
User checks N items → Click "Export Selected (N)"
  → useMutation fires → api.exportXxxBatch([ids])
    → POST /api/xxx/export/batch { xxx_ids: [...] }
      → Service.export_batch(ids) → SELECT ... WHERE id IN (...)
      → format each item → build_export_wrapper → JSON Response
    → res.blob() → saveFile(blob, filename)
      → showSaveFilePicker({ suggestedName })
        → createWritable → write(blob) → close()
      → OR fallback: downloadBlob(blob, filename)
    → toast.success("Exported N items")
```

## Files Modified (13 total)

| # | File | Change |
|---|------|--------|
| 1 | `backend/app/schemas/export_import.py` | Add batch request schemas |
| 2 | `backend/app/services/agent_service.py` | Add `export_batch` method |
| 3 | `backend/app/services/pipeline_service.py` | Add `export_batch` method |
| 4 | `backend/app/routers/agents.py` | Add POST batch endpoint |
| 5 | `backend/app/routers/pipelines.py` | Add POST batch endpoint |
| 6 | `frontend/src/shared/utils/download.ts` | **NEW** — shared downloadBlob |
| 7 | `frontend/src/shared/utils/saveFile.ts` | **NEW** — saveFile with Save-As + fallback |
| 8 | `frontend/src/features/agents/api.ts` | Add batch export API function |
| 9 | `frontend/src/features/agents/hooks.ts` | Add batch hook, import shared downloadBlob |
| 10 | `frontend/src/features/agents/components/AgentsTab.tsx` | Add checkbox selection + UI |
| 11 | `frontend/src/features/pipelines/api.ts` | Add batch export API function |
| 12 | `frontend/src/features/pipelines/hooks.ts` | Add batch hook, import shared downloadBlob |
| 13 | `frontend/src/features/pipelines/components/PipelinesTab.tsx` | Add checkbox selection + UI |

## Acceptance Criteria Mapping

| AC | Covered by |
|----|-----------|
| 1. Select N agents → file with only those | R1 backend + R3 frontend (AgentsTab) |
| 2. Select N pipelines → file with those (incl nested agents) | R1 backend + R4 frontend (PipelinesTab) |
| 3. Select-all checkbox toggles all visible | AgentsTab + PipelinesTab implementation |
| 4. Counter "N selected" updates in real time | useState set tracking |
| 5. Export Selected disabled when 0 | Disabled prop on button |
| 6. Batch endpoint rejects empty body with 400 | Backend validation |
| 7. Save-As dialog on Chromium | showSaveFilePicker in saveFile.ts |
| 8. Fallback downloadBlob on Firefox/Safari | Catch block in saveFile.ts |
| 9. Loading spinner + success/error feedback | useMutation pending state + toast in onSuccess + toast in onMutationError |
| 10. Single export unchanged | No changes to useExportAgent/useExportPipeline |
