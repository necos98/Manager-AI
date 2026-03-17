# Tech Stack Field for Projects

**Date:** 2026-03-17
**Status:** Approved

## Overview

Add a `tech_stack` free-form text field to the `Project` model so that users can document the technologies used in a project. This field is exposed to AI agents via the MCP `get_project_context` tool, giving them the necessary context to work effectively on tasks.

## Data Model

**Step 1** — update the SQLAlchemy model (`app/models/project.py`) first, adding the column after `description`. Include `server_default` in the model so autogenerate emits it:

```python
tech_stack: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default=sa.text("''"))
```

(Import `sqlalchemy as sa` at the top if not already present.)

**Step 2** — then generate a **new** Alembic revision (do not edit the existing `55bc4073dd1c_initial_schema.py`):

```bash
alembic revision --autogenerate -m "add tech_stack to projects"
```

Autogenerate requires the model to be updated before running, and requires `server_default` to be declared in the model for it to appear in the migration. Verify the generated migration has `server_default=sa.text("''")` and `nullable=False` in `op.add_column`:

```python
def upgrade() -> None:
    op.add_column('projects', sa.Column('tech_stack', sa.Text(), nullable=False, server_default=sa.text("''")))

def downgrade() -> None:
    op.drop_column('projects', 'tech_stack')
```

The `server_default` is required so existing rows in the database receive an empty string when the migration runs. The Python-side `default=""` in the model is insufficient for `ADD COLUMN` on a non-nullable column.

## Backend Schemas (`app/schemas/project.py`)

Add the following field to each class (these are additions to existing fields, not replacements):

- `ProjectCreate`: `tech_stack: str = ""` — no `Field` validator; `Text` is unbounded so no `max_length` needed.
- `ProjectUpdate`: `tech_stack: str | None = None` — `None` means "not provided / keep existing". `""` clears the field. Do **not** use `str = ""` here or partial updates would break. The "omit = keep" behavior is driven by `exclude_unset=True` in the router. If a client explicitly sends `"tech_stack": null`, the service's `if value is not None` guard silently discards it (field unchanged, no error) — inherited existing behavior.
- `ProjectResponse`: `tech_stack: str`

## Backend Service & Router

### `project_service.py`

`create()` has a fixed signature. Update it to accept `tech_stack: str = ""`:

```python
async def create(self, name: str, path: str, description: str = "", tech_stack: str = "") -> Project:
    project = Project(name=name, path=path, description=description, tech_stack=tech_stack)
    ...
```

`update()` already applies non-`None` fields generically — no changes needed.

### `routers/projects.py`

The POST endpoint must forward `tech_stack` to `service.create()`:

```python
project = await service.create(
    name=data.name, path=data.path, description=data.description, tech_stack=data.tech_stack
)
```

## MCP Tool (`app/mcp/server.py`)

Update `get_project_context` docstring and return dict:

```python
"""Get project information (name, path, description, tech_stack)."""
...
return {
    "id": str(project.id),
    "name": project.name,
    "path": project.path,
    "description": project.description,
    "tech_stack": project.tech_stack,
}
```

## Frontend

### `NewProjectPage.jsx`

- Extend initial state: `{ name: "", path: "", description: "", tech_stack: "" }`
- New `<textarea>` below `description` (use `rows={3}` to match existing style):
  - Label: **Tech Stack**
  - Placeholder: `Languages, frameworks, databases, infra… e.g. Python 3.12, FastAPI, PostgreSQL, React, Tailwind`
  - `value={form.tech_stack}`
  - `onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}`

### `ProjectDetailPage.jsx`

**`useState` initialization** (line 15) — update to include `tech_stack`:

```js
const [editForm, setEditForm] = useState({ name: "", path: "", description: "", tech_stack: "" });
```

**`startEditing` function** — explicitly include `tech_stack`:

```js
setEditForm({ name: project.name, path: project.path, description: project.description || "", tech_stack: project.tech_stack || "" });
```

**Read view** — display below `description` if non-empty:

```jsx
{project.tech_stack && (
  <p className="text-sm text-gray-500 mt-1"><span className="font-medium">Tech Stack:</span> {project.tech_stack}</p>
)}
```

**Edit form** — add a `<textarea rows={3}>` with `value={editForm.tech_stack}` and `onChange={(e) => setEditForm({ ...editForm, tech_stack: e.target.value })}`, same styling as `description` textarea.

## Error Handling

No special error handling required — the field is optional (defaults to `""`), validated by the existing Pydantic layer.

## Testing

Update existing tests using the service layer to create projects (via `ProjectService.create()`). Add `tech_stack` to creation calls and assert on it:

- **`test_project_service.py`**: pass `tech_stack="Python, FastAPI"` in creation; assert `project.tech_stack == "Python, FastAPI"`.
- **`test_routers_projects.py`**: include `tech_stack` in POST and PUT request bodies (router uses `PUT` for updates); assert the field in JSON responses.
- **`test_mcp_tools.py` (`test_mcp_project_context`)**: the existing test uses a shared `project` fixture (a `@pytest_asyncio.fixture` that calls `service.create(...)`). Add `tech_stack="Python, FastAPI"` to the `create()` call **inside that shared fixture**. Then in `test_mcp_project_context`, assert `fetched.tech_stack == "Python, FastAPI"` on the ORM object returned by `get_by_id()`. The `get_project_context` MCP tool function itself is not called directly in unit tests (it uses an internal `async_session` that is not injectable) — this is consistent with how all other MCP tools are tested in this file.

No new test files needed.
