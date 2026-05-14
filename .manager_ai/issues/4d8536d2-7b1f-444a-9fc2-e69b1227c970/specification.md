# Specification: Project Linking with Relationship Types

## Problem

Currently there is no way to declare that two projects are related. When modifying a project, there's no visibility into which other projects might be impacted. Example: "Project A" exposes APIs consumed by "Project B" — a change to A could break B.

## Solution

Allow users to declare **directional links** between projects, each with a free-text description of the relationship.

A link `A → B` means "A relates to B in this way". The reverse direction is NOT implied — if B also relates to A, a separate link must be created.

## Design Decisions

- **Directional**: A→B ≠ B→A. Each direction has its own description.
- **Free-text description**: No predefined enum. User writes how the projects relate.
- **Settings dialog integration**: Managed in the existing ProjectSettingsDialog, under a new "Linked Projects" section.

## Data Model

### New table: `project_links`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | auto-generated |
| `source_project_id` | FK→projects.id | The project that "links out" |
| `target_project_id` | FK→projects.id | The project being linked to |
| `description` | Text | Free-text description of how source relates to target |
| `created_at` | DateTime | server default now() |
| `updated_at` | DateTime | server default now() with onupdate |

Unique constraint on `(source_project_id, target_project_id)` — no duplicate directional links between the same pair.

### API Endpoints

Prefix: `/api/projects/{project_id}/links`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | List all links where project is source OR target. Returns list of `ProjectLinkResponse` with source/target project names populated. |
| `POST` | `/` | Create a link. Body: `{target_project_id, description}`. Source is `project_id` from path. |
| `PUT` | `/{link_id}` | Update description. Body: `{description}`. |
| `DELETE` | `/{link_id}` | Delete a link. |

## Frontend

### New section in `ProjectSettingsDialog`: "Linked Projects"

- List of existing links for the current project (both directions)
- Each link displayed as: `Source Name → Target Name` with description below
- Direction indicator (arrow icon) to make directionality obvious
- "Add Link" button:
  - Dropdown/combobox to select target project (filtered to exclude self)
  - Text field for description
  - Creates link where source = current project, target = selected project
- Edit button (pencil icon) to modify description
- Delete button (trash icon) with confirmation

### New Types

```ts
interface ProjectLink {
  id: string;
  source_project_id: string;
  source_project_name: string;
  target_project_id: string;
  target_project_name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

interface ProjectLinkCreate {
  target_project_id: string;
  description: string;
}

interface ProjectLinkUpdate {
  description: string;
}
```

### New API Functions

```ts
fetchProjectLinks(projectId: string): Promise<ProjectLink[]>
createProjectLink(projectId: string, data: ProjectLinkCreate): Promise<ProjectLink>
updateProjectLink(projectId: string, linkId: string, data: ProjectLinkUpdate): Promise<ProjectLink>
deleteProjectLink(projectId: string, linkId: string): Promise<void>
```

### New Hooks

```ts
useProjectLinks(projectId: string)         // useQuery
useCreateProjectLink(projectId: string)    // useMutation
useUpdateProjectLink(projectId: string)    // useMutation
useDeleteProjectLink(projectId: string)    // useMutation
```

## Files

### Backend (create/modify)
- **Create:** `backend/app/models/project_link.py` — SQLAlchemy model
- **Modify:** `backend/app/models/__init__.py` — register ProjectLink
- **Create:** `backend/app/schemas/project_link.py` — Pydantic schemas
- **Create:** `backend/app/services/project_link_service.py` — business logic
- **Create:** `backend/app/routers/project_links.py` — REST endpoints
- **Modify:** `backend/app/main.py` — register router

### Frontend (modify)
- **Modify:** `frontend/src/shared/types/index.ts` — add ProjectLink types
- **Modify:** `frontend/src/features/projects/api.ts` — add API functions
- **Modify:** `frontend/src/features/projects/hooks.ts` — add hooks
- **Modify:** `frontend/src/features/projects/components/project-settings-dialog.tsx` — add "Linked Projects" section

### Database
- One new migration via Alembic for the `project_links` table

## Constraints

- A project cannot link to itself (validated in service layer)
- Duplicate directional links (same source + target) rejected by DB unique constraint
- Deleting a project cascades to delete all its links (both as source and target)
- Link description is required (non-empty string)

## Scope

- Full CRUD for project links
- Display in project settings dialog
- No impact analysis UI yet (future: dashboard could show "projects that depend on this one")