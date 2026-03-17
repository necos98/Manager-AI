# Tech Stack Field for Projects

**Date:** 2026-03-17
**Status:** Approved

## Overview

Add a `tech_stack` free-form text field to the `Project` model so that users can document the technologies used in a project. This field is exposed to AI agents via the MCP `get_project_context` tool, giving them the necessary context to work effectively on tasks.

## Data Model

New column on the `projects` table:

```sql
ALTER TABLE projects ADD COLUMN tech_stack TEXT NOT NULL DEFAULT '';
```

SQLAlchemy model (`app/models/project.py`):

```python
tech_stack: Mapped[str] = mapped_column(Text, nullable=False, default="")
```

Alembic migration: add nullable=False, server_default `''`.

## Backend Schemas (`app/schemas/project.py`)

- `ProjectCreate`: `tech_stack: str = ""`
- `ProjectUpdate`: `tech_stack: str | None = None`
- `ProjectResponse`: `tech_stack: str`

No changes needed to `project_service.py` — the service already handles fields generically via the update schema.

## MCP Tool (`app/mcp/server.py`)

`get_project_context` response gains a new key:

```python
"tech_stack": project.tech_stack,
```

This ensures AI agents receive the tech stack context alongside name, path, and description.

## Frontend

### `NewProjectPage.jsx`

New `<textarea>` field below `description`:

- Label: **Tech Stack**
- Placeholder: `Languages, frameworks, databases, infra… e.g. Python 3.12, FastAPI, PostgreSQL, React, Tailwind`
- Bound to `form.tech_stack`

### `ProjectDetailPage.jsx`

**Read view:** display `tech_stack` below `description` if non-empty, with a muted label "Tech Stack".

**Edit form:** same `<textarea>` as in `NewProjectPage`, pre-filled with `project.tech_stack`.

State and handlers (`editForm`) extended to include `tech_stack`.

## Error Handling

No special error handling required — the field is optional (defaults to empty string) and validated by the existing Pydantic layer.

## Testing

Existing tests for project creation, update, and MCP tools cover the field by including it in fixture payloads. No new test files needed; existing tests should be updated to include `tech_stack` where projects are created or asserted.
