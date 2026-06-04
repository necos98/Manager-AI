# Export/Import Agents and Pipelines in JSON Format

## Overview
Allow users to export agents and pipelines (including their step configurations) as downloadable JSON files, and import such files back into any Manager AI instance. This enables sharing agent/pipeline definitions between colleagues and across projects.

Two separate operations:
- **Export**: read current data, produce JSON, trigger browser download.
- **Import**: upload JSON file → preview contents with conflict detection → confirm to persist.

---

## Scope

### In scope
- Export single agent (JSON download)
- Export single pipeline, auto-including all referenced agents in the export
- Export all agents (bulk)
- Export all pipelines (bulk), auto-including all referenced agents
- Import agents from a JSON file
- Import pipelines from a JSON file (referenced agents must already exist or be co-imported)
- Two-phase import: upload → preview/conflict resolution → confirm
- Conflict detection by strict UUID match on `id` field — name collisions are NOT conflicts
- UI for both export and import on Agents and Pipelines tabs
- New REST API endpoints for export and import

### Out of scope
- Import/export of pipeline runs, messages, or execution history
- Cross-instance ID migration (IDs stay as-is from the source file)
- Bulk export/import of both types in a single file (agents and pipelines are separate operations)
- Version migration — only version 1 of the export format is supported
- Import validation beyond schema compliance and ID conflicts

---

## Data Format

### Export wrapper envelope
```
{
  "version": 1,
  "type": "agents" | "pipelines",
  "exported_at": "2026-06-04T21:00:00Z",
  "items": [ ... ]
}
```

### Agent item (matches Agent schema)
```
{
  "id": "uuid-string",
  "name": "string",
  "model": "string | null",
  "allowed_tools": ["string", ...] | null,
  "intent": "string"
}
```
Note: `created_at` and `updated_at` are NOT exported (timestamps belong to the source instance).

### Pipeline item (includes resolved agent data)
```
{
  "id": "uuid-string",
  "name": "string",
  "steps": [
    {
      "id": "uuid-string",
      "agent_id": "uuid-string",
      "order_index": 0,
      "agent": { ... }  // full agent object (same shape as agent item above)
    }
  ]
}
```
Each pipeline step includes the complete agent definition inline. This ensures a pipeline export is self-contained — importing a pipeline file means all referenced agents are available or can be created.

---

## API Endpoints

All new endpoints under `/api/agents/export`, `/api/agents/import`, `/api/pipelines/export`, `/api/pipelines/import`.

### Export Agent(s)

**GET /api/agents/export/{agent_id}** — Export single agent
- Response 200: `application/json` with Content-Disposition: attachment header
- Response body: export wrapper `{ version: 1, type: "agents", exported_at, items: [agent] }`

**GET /api/agents/export** — Export all agents
- Response 200: same as single but `items` contains all agents
- Response 200 (empty): `items: []` when no agents exist

### Export Pipeline(s)

**GET /api/pipelines/export/{pipeline_id}** — Export single pipeline
- Resolves all steps, includes full agent objects inline
- Response 200: export wrapper `{ version: 1, type: "pipelines", exported_at, items: [pipeline] }`
- Response 404: pipeline not found

**GET /api/pipelines/export** — Export all pipelines
- Response 200: `items` contains all pipelines with resolved agents
- Response 200 (empty): `items: []` when no pipelines exist

### Import Agents

**POST /api/agents/import/preview** — First phase: upload file for preview
- Request: multipart/form-data with a `.json` file
- Response 200: `{ conflicts: [agent_with_id_matching_existing], new: [agents_not_found], total: count }`
- Each conflict item includes both `existing` (current DB state) and `incoming` (from file) representations
- Response 400: invalid JSON format, wrong type field, unsupported version

**POST /api/agents/import/confirm** — Second phase: apply the import
- Request: multipart/form-data with the same `.json` file + a `conflicts` field (JSON string)
- Conflicts format: `{ "<agent_id>": "skip" | "overwrite" }` — only needed for IDs that matched during preview
- Unmentioned conflicted IDs default to "skip" (keep existing)
- Backend re-parses the file and applies conflict resolution choices
- Response 200: `{ imported: count, skipped: count, errors: [details] }`
- Response 400: invalid conflicts format, or attempting to import pipelines without required agents

### Import Pipelines

**POST /api/pipelines/import/preview** — First phase
- Same pattern as agents import
- Preview includes: new pipelines, conflicting pipelines (by ID)
- Also checks: are all referenced agents present in DB or in the same file? If not, flags them as missing dependencies
- Response: `{ conflicts: [...], new: [...], missing_agents: [{agent_id, agent_name}], total: count }`

**POST /api/pipelines/import/confirm** — Second phase
- Same multipart pattern as agents import (file + `conflicts` JSON field)
- On overwrite: deletes existing steps and recreates from file (full replacement)
- Creates/updates referenced agents inline (from the `agent` field in each step)
- Missing agents (referenced by ID but not present in file or DB) are a blocker — response 400
- Response 200: `{ imported: count, skipped: count, errors: [details] }`

---

## Import Flow

1. User clicks "Import" button on Agents or Pipelines tab
2. File picker dialog opens, accepts `.json` files only
3. User selects file → frontend sends to `/import/preview`
4. Backend parses, validates schema, checks for ID conflicts against DB
5. Preview modal appears showing:
   - **New items** (green section): items whose IDs don't match anything in DB
   - **Conflicts** (yellow section): items whose IDs match existing records, with side-by-side comparison (existing vs incoming)
   - For pipelines: also shows any **missing agent dependencies** (red section)
6. For each conflict, user picks: "Skip" (keep existing) or "Overwrite" (replace with incoming)
7. User clicks "Confirm Import"
8. Frontend sends `/import/confirm` with conflict resolution choices
9. Backend applies changes, returns summary
10. Success toast + list refresh

---

## Conflict Resolution Rules

- **Strict UUID match**: only items with matching `id` fields are conflicts
- **No name matching**: same name but different ID = treated as new item (different agent)
- **Default action**: unspecified conflicted IDs default to "skip" (don't overwrite)
- **Pipeline dependencies**: if a pipeline references agents that don't exist in DB AND aren't in the import file, the preview flags them. The confirm endpoint rejects such imports unless the agents are also being imported in the same operation.

---

## UI Requirements

### Export triggers
- **Agents tab**: "Export All" button in toolbar. Each agent row gets an "Export" icon/button in actions column.
- **Pipelines tab**: "Export All" button in toolbar. Each pipeline row/card gets an "Export" icon/button.
- On click: triggers browser file download (no confirmation needed — export is low-risk).
- Pipeline export download includes all referenced agents in the file (self-contained).

### Import triggers
- **Agents tab**: "Import" button in toolbar → file picker → preview modal → confirm.
- **Pipelines tab**: "Import" button in toolbar → file picker → preview modal → confirm.
- Preview modal layout:
  - Header: "Import Preview — X items found, Y conflicts"
  - Sectioned list: new (green), conflicts (yellow), missing deps (red, pipelines only)
  - Conflict row: inline diff showing field-by-field comparison
  - Conflict actions: radio/dropdown per item — "Skip" vs "Overwrite"
  - Footer: "Cancel" and "Confirm Import (X items)" button
- After confirm: success toast + list refresh

### Loading/error states
- Preview loading: spinner in modal
- Preview error: error message in modal (invalid format, wrong type, etc.)
- Confirm loading: button shows spinner, modal not closable
- Confirm error: error toast, modal stays open for retry
- Export loading: button shows spinner during download
- Export error: error toast

---

## Acceptance Criteria

1. Can export a single agent → downloads valid JSON file
2. Can export all agents → file contains all agents
3. Can export a single pipeline → file contains pipeline with all referenced agents inline
4. Can export all pipelines → file contains all pipelines with agents inline
5. Can import agents JSON → all new agents created
6. Can import agents JSON with conflicts → overwrite and skip work correctly
7. Can import pipelines JSON → pipelines created with correct steps
8. Import with missing agent dependencies → preview shows them, confirm rejects
9. Empty export (no agents/pipelines) → valid JSON with empty items array
10. Invalid JSON upload → clear error message
11. Wrong type field (uploading pipeline file to agents import) → clear error message
12. Frontend handles loading, empty, error states for all new UI components

---

## Non-goals

- No export of pipeline execution history or run data
- No cross-version migration (only version 1)
- No batch file containing both agents and pipelines in one operation
- No drag-and-drop file upload (standard file picker is sufficient)
- No encryption or password protection on export files
- No import undo — standard delete is the recovery mechanism