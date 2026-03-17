# Tech Stack Field Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `tech_stack` free-form text field to the `Project` model, exposed in the REST API, MCP tool, and frontend create/edit forms.

**Architecture:** New `Text` column on the `projects` table with Alembic migration. Pydantic schemas, service, router, and MCP tool each receive a one-field addition. Frontend forms get a new `<textarea>` with a guided placeholder.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, Pydantic v2, FastMCP, React, Tailwind, pytest (asyncio_mode=auto), SQLite in-memory for tests.

---

## Chunk 1: Backend

### Task 1: Add `tech_stack` to model and schemas (TDD)

**Files:**
- Modify: `backend/app/models/project.py`
- Modify: `backend/app/schemas/project.py`
- Modify: `backend/tests/test_project_service.py`
- Modify: `backend/tests/test_routers_projects.py`

- [ ] **Step 1: Write failing tests**

In `backend/tests/test_project_service.py`, add at the end:

```python
async def test_create_project_with_tech_stack(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test", tech_stack="Python, FastAPI")
    assert project.tech_stack == "Python, FastAPI"


async def test_create_project_tech_stack_defaults_to_empty(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test")
    assert project.tech_stack == ""


async def test_update_project_tech_stack(db_session):
    service = ProjectService(db_session)
    project = await service.create(name="Test", path="/tmp/test", tech_stack="Python")
    updated = await service.update(project.id, tech_stack="Python, FastAPI, React")
    assert updated.tech_stack == "Python, FastAPI, React"
```

In `backend/tests/test_routers_projects.py`, add at the end:

```python
@pytest.mark.asyncio
async def test_create_project_with_tech_stack(client):
    response = await client.post(
        "/api/projects",
        json={"name": "Test", "path": "/tmp/test", "tech_stack": "Python, FastAPI"},
    )
    assert response.status_code == 201
    assert response.json()["tech_stack"] == "Python, FastAPI"


@pytest.mark.asyncio
async def test_create_project_tech_stack_defaults_to_empty(client):
    response = await client.post("/api/projects", json={"name": "Test", "path": "/tmp"})
    assert response.status_code == 201
    assert response.json()["tech_stack"] == ""


@pytest.mark.asyncio
async def test_update_project_tech_stack(client):
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Test", "path": "/tmp", "tech_stack": "Python"},
    )
    project_id = create_resp.json()["id"]
    response = await client.put(
        f"/api/projects/{project_id}", json={"tech_stack": "Python, React"}
    )
    assert response.status_code == 200
    assert response.json()["tech_stack"] == "Python, React"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/jacob/manager_ai/backend && python -m pytest tests/test_project_service.py::test_create_project_with_tech_stack tests/test_routers_projects.py::test_create_project_with_tech_stack -v
```

Expected: FAIL — the service test fails with `TypeError: create() got an unexpected keyword argument 'tech_stack'`; the router test fails with `AssertionError` because `tech_stack` is not in the response JSON (Pydantic v2 silently drops unknown POST fields before they reach the service).

- [ ] **Step 3: Update the SQLAlchemy model**

In `backend/app/models/project.py`, add `text` to the existing `from sqlalchemy import ...` line and add the column after `description`.

Update the import line to:

```python
from sqlalchemy import Column, DateTime, String, Text, func, text
```

Then add the column (after the `description` line):

```python
tech_stack: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default=text("''"))
```

- [ ] **Step 4: Update Pydantic schemas**

In `backend/app/schemas/project.py`, add `tech_stack` to each class:

```python
class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    description: str = ""
    tech_stack: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    tech_stack: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    path: str
    description: str
    tech_stack: str
    created_at: datetime
    updated_at: datetime
    task_counts: dict[str, int] = {}

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Update `project_service.py` `create()` signature**

In `backend/app/services/project_service.py`, update the `create` method:

```python
async def create(self, name: str, path: str, description: str = "", tech_stack: str = "") -> Project:
    project = Project(name=name, path=path, description=description, tech_stack=tech_stack)
    self.session.add(project)
    await self.session.flush()
    return project
```

- [ ] **Step 6: Update `routers/projects.py` POST endpoint**

In `backend/app/routers/projects.py`, update the `create_project` handler to forward `tech_stack`:

```python
@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    service = ProjectService(db)
    project = await service.create(
        name=data.name, path=data.path, description=data.description, tech_stack=data.tech_stack
    )
    await db.commit()
    return await _enrich_project(service, project)
```

- [ ] **Step 7: Run all backend tests**

```bash
cd /home/jacob/manager_ai/backend && python -m pytest tests/test_project_service.py tests/test_routers_projects.py -v
```

Expected: All tests PASS (including existing ones).

- [ ] **Step 8: Generate Alembic migration**

```bash
cd /home/jacob/manager_ai/backend && alembic revision --autogenerate -m "add tech_stack to projects"
```

Open the generated file in `alembic/versions/` and verify `upgrade()` and `downgrade()` look like:

```python
def upgrade() -> None:
    op.add_column('projects', sa.Column('tech_stack', sa.Text(), nullable=False, server_default=sa.text("''")))

def downgrade() -> None:
    op.drop_column('projects', 'tech_stack')
```

If `server_default` is missing from the generated migration, add it manually.

- [ ] **Step 9: Commit**

```bash
cd /home/jacob/manager_ai && git add backend/app/models/project.py backend/app/schemas/project.py backend/app/services/project_service.py backend/app/routers/projects.py backend/tests/test_project_service.py backend/tests/test_routers_projects.py backend/alembic/versions/
git commit -m "feat: add tech_stack field to Project model, schemas, service, and router"
```

---

### Task 2: Update MCP tool and its test

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1: Write a failing test that calls the MCP tool directly**

The MCP tool uses `async with async_session() as session:` internally. In tests we patch `app.mcp.server.async_session` so the tool uses the test's in-memory DB session.

Add the following imports at the top of `backend/tests/test_mcp_tools.py`:

```python
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch
import app.mcp.server as mcp_server
```

Also update the shared `project` fixture (line 11–14) to include `tech_stack`:

```python
@pytest_asyncio.fixture
async def project(db_session):
    service = ProjectService(db_session)
    return await service.create(name="MCP Test", path="/tmp/mcp", description="MCP test project", tech_stack="Python, FastAPI")
```

Add a new test at the end of the file:

```python
@pytest.mark.asyncio
async def test_mcp_get_project_context_includes_tech_stack(db_session, project):
    """get_project_context tool returns tech_stack in its dict"""

    @asynccontextmanager
    async def fake_session():
        yield db_session

    class MockSessionmaker:
        def __call__(self):
            return fake_session()

    with patch("app.mcp.server.async_session", MockSessionmaker()):
        result = await mcp_server.get_project_context(str(project.id))

    assert result["tech_stack"] == "Python, FastAPI"
    assert result["name"] == "MCP Test"
```

Also update `test_mcp_project_context` to assert `tech_stack` on the ORM object:

```python
@pytest.mark.asyncio
async def test_mcp_project_context(project_service, project):
    """get_project_context returns project info"""
    fetched = await project_service.get_by_id(project.id)
    assert fetched.name == "MCP Test"
    assert fetched.path == "/tmp/mcp"
    assert fetched.description == "MCP test project"
    assert fetched.tech_stack == "Python, FastAPI"
```

- [ ] **Step 2: Run the new test to verify it fails**

```bash
cd /home/jacob/manager_ai/backend && python -m pytest tests/test_mcp_tools.py::test_mcp_get_project_context_includes_tech_stack -v
```

Expected: FAIL — `KeyError: 'tech_stack'` (the MCP tool's return dict doesn't include `tech_stack` yet).

- [ ] **Step 3: Update `get_project_context` in MCP server**

In `backend/app/mcp/server.py`, update the `get_project_context` tool:

```python
@mcp.tool()
async def get_project_context(project_id: str) -> dict:
    """Get project information (name, path, description, tech_stack)."""
    async with async_session() as session:
        project_service = ProjectService(session)
        try:
            pid = uuid.UUID(project_id)
        except ValueError:
            return {"error": f"Invalid project_id: {project_id!r}"}
        project = await project_service.get_by_id(pid)
        if project is None:
            return {"error": "Project not found"}
        return {
            "id": str(project.id),
            "name": project.name,
            "path": project.path,
            "description": project.description,
            "tech_stack": project.tech_stack,
        }
```

- [ ] **Step 4: Run all MCP tests**

```bash
cd /home/jacob/manager_ai/backend && python -m pytest tests/test_mcp_tools.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
cd /home/jacob/manager_ai/backend && python -m pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
cd /home/jacob/manager_ai && git add backend/app/mcp/server.py backend/tests/test_mcp_tools.py
git commit -m "feat: expose tech_stack in MCP get_project_context tool"
```

---

## Chunk 2: Frontend

### Task 3: Update `NewProjectPage.jsx`

**Files:**
- Modify: `frontend/src/pages/NewProjectPage.jsx`

- [ ] **Step 1: Update initial state and add textarea**

In `frontend/src/pages/NewProjectPage.jsx`, make the following changes:

**Line 7** — extend initial form state:
```js
const [form, setForm] = useState({ name: "", path: "", description: "", tech_stack: "" });
```

**After the Description `<div>` block (after line 55, before the button `<div>`)** — add the Tech Stack field:

```jsx
<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">Tech Stack</label>
  <textarea
    value={form.tech_stack}
    onChange={(e) => setForm({ ...form, tech_stack: e.target.value })}
    className="w-full border rounded px-3 py-2"
    rows={3}
    placeholder="Languages, frameworks, databases, infra… e.g. Python 3.12, FastAPI, PostgreSQL, React, Tailwind"
  />
</div>
```

- [ ] **Step 2: Verify in the browser**

Start the dev stack and navigate to `/projects/new`. Confirm:
- "Tech Stack" textarea appears below "Description"
- Typing in it updates correctly
- Submitting a new project with a tech stack value succeeds and redirects to the project detail page
- The project detail page shows the tech stack value

```bash
# If running via Docker Compose:
docker compose up -d
# Then open http://localhost:5173/projects/new
```

- [ ] **Step 3: Commit**

```bash
cd /home/jacob/manager_ai && git add frontend/src/pages/NewProjectPage.jsx
git commit -m "feat: add tech_stack field to new project form"
```

---

### Task 4: Update `ProjectDetailPage.jsx`

**Files:**
- Modify: `frontend/src/pages/ProjectDetailPage.jsx`

- [ ] **Step 1: Update state, startEditing, read view, and edit form**

In `frontend/src/pages/ProjectDetailPage.jsx`, make four targeted changes:

**1. Line 15** — extend `editForm` initial state:
```js
const [editForm, setEditForm] = useState({ name: "", path: "", description: "", tech_stack: "" });
```

**2. `startEditing` function (line 30)** — add `tech_stack`:
```js
const startEditing = () => {
  setEditForm({ name: project.name, path: project.path, description: project.description || "", tech_stack: project.tech_stack || "" });
  setEditError(null);
  setEditing(true);
};
```

**3. Read view** — after the `{project.description && ...}` line (line 122), add:
```jsx
{project.tech_stack && (
  <p className="text-sm text-gray-500 mt-1">
    <span className="font-medium">Tech Stack:</span> {project.tech_stack}
  </p>
)}
```

**4. Edit form** — after the Description `<div>` block in the edit form (after the closing `</div>` of description, before the buttons `<div>`), add:
```jsx
<div>
  <label className="block text-sm font-medium text-gray-700 mb-1">Tech Stack</label>
  <textarea
    value={editForm.tech_stack}
    onChange={(e) => setEditForm({ ...editForm, tech_stack: e.target.value })}
    className="w-full border rounded px-3 py-2"
    rows={3}
  />
</div>
```

- [ ] **Step 2: Verify in the browser**

Navigate to an existing project's detail page. Confirm:
- If the project has a `tech_stack` value, it appears in the read view below `description`
- Clicking "Edit" pre-populates the Tech Stack textarea
- Saving updates the displayed value
- Clearing the field and saving removes it from the read view

- [ ] **Step 3: Commit**

```bash
cd /home/jacob/manager_ai && git add frontend/src/pages/ProjectDetailPage.jsx
git commit -m "feat: add tech_stack field to project detail view and edit form"
```
