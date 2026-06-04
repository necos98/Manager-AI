# Export/Import Agents & Pipelines

## Overview
Allow users to export agents and pipelines (including their step structure with agent references) as downloadable JSON files, and import such files back into the system. This enables sharing agents and pipelines between colleagues or across different Manager AI instances.

## Scope
- Export agents (single selection via checkbox, or bulk "Export All")
- Export pipelines including their step structure — each step embeds the referenced agent's full data inline
- Import agents and pipelines from a JSON file via upload button or drag-and-drop zone
- Conflict detection: when an imported agent or pipeline has a name that already exists, present the user with a list of conflicts and let them choose which ones to overwrite
- UI: inline export/import controls on the existing Agents and Pipelines management pages

## Out of Scope (Non-goals)
- Export/import of projects or other entity types
- Cross-instance sync or automatic replication
- Version history or migration of entities across different software versions
- Bulk import of multiple files at once
- Encryption or password protection of exported files

## Functional Requirements

### FR1 — Export Agents
- User can select individual agents via checkbox and trigger export
- User can trigger "Export All" to export every agent
- Exported file contains a JSON array of agent objects
- Each agent object includes: id, name, model, allowed_tools, intent, created_at, updated_at
- File is downloaded as `.json` with a meaningful filename (e.g. `agents-export-2026-06-04.json`)

### FR2 — Export Pipelines
- User can select individual pipelines via checkbox and trigger export
- User can trigger "Export All" to export every pipeline
- Exported file contains a JSON array of pipeline objects
- Each pipeline object includes: id, name, steps (ordered), created_at, updated_at
- Each step includes the order_index, PLUS the full agent data (id, name, model, allowed_tools, intent) embedded inline under an `agent` key — so the file is self-contained and doesn't require the importing instance to already have those agents
- File is downloaded as `.json` with a meaningful filename

### FR3 — Import
- Import zone on both Agents and Pipelines pages: drag-and-drop area + file picker button
- Only `.json` files accepted
- On file select/drop, the system reads and parses the file
- Import on the Agents page processes only the `agents` array from the JSON file; import on the Pipelines page processes only the `pipelines` array
- If no conflicts exist, entities are imported immediately
- If conflicts exist (same name as an existing agent or pipeline), show a conflict resolution modal
- Conflict modal lists each conflicting entity with a multi-select checkbox
- User selects which existing entities to overwrite
- Non-selected conflicting entities are skipped (not imported)
- Entities without conflicts are imported regardless of conflict selections
- On import, new UUIDs are generated for all new entities (original file IDs are not preserved). For overwritten entities, the existing ID on the target instance is retained.

### FR4 — JSON Format
- Top-level wrapper object with `version` field (initial value `"1.0"`) and `exported_at` timestamp
- Top-level `agents` and `pipelines` arrays (one or both may be populated)
- Pipeline steps include expanded agent data under an `agent` key for self-contained pipelines
- Consistent schema across export and import

#### Example structure:
```json
{
  "version": "1.0",
  "exported_at": "2026-06-04T12:00:00Z",
  "agents": [
    {
      "id": "uuid-here",
      "name": "My Agent",
      "model": "sonnet",
      "allowed_tools": ["read", "write"],
      "intent": "Do something",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "pipelines": [
    {
      "id": "uuid-here",
      "name": "My Pipeline",
      "steps": [
        {
          "order_index": 0,
          "agent": {
            "id": "uuid-here",
            "name": "My Agent",
            "model": "sonnet",
            "allowed_tools": ["read", "write"],
            "intent": "Do something"
          }
        }
      ],
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### FR5 — Error Handling
- Invalid JSON: show clear error message ("Invalid file format")
- Missing required fields: show error and skip that entity, continue with rest
- Empty file: show "No agents or pipelines found in file"
- Duplicate entries within the same file (detected by matching `name`): skip duplicates and report count

## Constraints
- Must work within existing agents/pipelines UI pages — no new top-level pages
- Must not break existing CRUD functionality for agents and pipelines
- Must handle the case where pipelines reference agents that don't exist on the importing instance (need to create agents first or reject)
- Backend does the validation; frontend handles upload UX and conflict display

## Acceptance Criteria
1. User can export 1+ selected agents → downloads valid JSON file
2. User can Export All agents → downloads file with all agents
3. User can export 1+ selected pipelines → downloads file with expanded agent data
4. User can Export All pipelines → downloads file with all pipelines
5. User drags JSON file onto import zone → agents/pipelines are imported
6. User clicks upload button → file picker opens → agents/pipelines imported
7. When importing agents that already exist → conflict modal appears with checkboxes
8. User selects which conflicts to overwrite → selected ones updated, rest skipped
9. New entities without conflicts are always imported (with new UUIDs)
10. Invalid JSON file shows appropriate error message
11. Pipeline import creates referenced agents if they don't exist (creates them first, then creates pipeline)
12. Pipeline import with referenced agents that already exist on target instance: agents matched by name, pipeline created referencing those existing agents
