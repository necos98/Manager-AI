# Ask & Brainstorming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an "Ask & Brainstorming" section to Manager AI that opens a Claude Code terminal session pre-loaded with a brainstorming prompt, embedding the terminal inline in the page.

**Architecture:** New Claude command file provides the brainstorming prompt; a new backend endpoint `POST /api/terminals/ask` spawns the terminal using a configurable command from global settings; a new frontend route renders the page with an embedded `TerminalPanel`.

**Tech Stack:** Python/FastAPI (backend), React/TanStack Router (frontend), xterm.js (terminal rendering), SQLite settings store.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `claude_resources/commands/ask-and-brainstorm.md` | Claude slash command — brainstorming instructions |
| Modify | `backend/app/mcp/default_settings.json` | Add `ask_brainstorm_command` default |
| Modify | `backend/app/schemas/terminal.py` | Add `AskTerminalCreate` schema |
| Modify | `backend/app/routers/terminals.py` | Add `POST /api/terminals/ask` endpoint |
| Create | `backend/tests/test_ask_terminal.py` | Tests for the new endpoint |
| Modify | `frontend/src/shared/types/index.ts` | Add `AskTerminalCreate` type |
| Modify | `frontend/src/features/terminals/api.ts` | Add `createAskTerminal` function |
| Modify | `frontend/src/features/terminals/hooks.ts` | Add `useCreateAskTerminal` hook |
| Create | `frontend/src/routes/projects/$projectId/ask.tsx` | Ask & Brainstorming page |
| Modify | `frontend/src/routeTree.gen.ts` | Register new route |
| Modify | `frontend/src/shared/components/app-sidebar.tsx` | Add sidebar nav item |

---

### Task 1: Create the Claude command file

**Files:**
- Create: `claude_resources/commands/ask-and-brainstorm.md`

- [ ] **Step 1: Create the command file**

`claude_resources/commands/ask-and-brainstorm.md`:
```markdown
Start an Ask & Brainstorming session for project ID: $ARGUMENTS

1. Call the "Manager_AI" MCP tool `get_project_context` with the provided project ID to load project name, description, and tech stack.
2. Briefly introduce yourself: you are in listening and brainstorming mode for this project. You are here to help the user think through ideas, architectural decisions, trade-offs, and creative directions.
3. Wait for the user's input. Do NOT act autonomously — stay in listening mode.
4. For each message from the user:
   - Reason collaboratively and help structure their thinking.
   - If relevant, use `search_project_context` with the project ID to retrieve context from existing files or completed issues.
   - Surface trade-offs, suggest directions, and ask clarifying questions when useful.
5. Issue creation (optional — only when the user explicitly asks):
   - Before creating an issue, confirm you have: a clear name, a description, and enough context.
   - If anything is missing, ask the user before proceeding.
   - Use `create_issue` with the project ID, name, and description.
   - After creation, confirm the issue ID and name to the user.
6. Never create issues, files, or make any changes unless explicitly requested by the user.
```

- [ ] **Step 2: Commit**

```bash
git add claude_resources/commands/ask-and-brainstorm.md
git commit -m "feat: add ask-and-brainstorm Claude command"
```

---

### Task 2: Add setting key to default_settings.json

**Files:**
- Modify: `backend/app/mcp/default_settings.json`

- [ ] **Step 1: Add the new setting key**

Open `backend/app/mcp/default_settings.json` and add this entry (at the end, before the closing `}`):

```json
  "ask_brainstorm_command": "claude /ask-and-brainstorm $project_id"
```

The full file ends like:
```json
  "terminal_theme": "catppuccin",
  "ask_brainstorm_command": "claude /ask-and-brainstorm $project_id"
}
```

- [ ] **Step 2: Verify the setting loads**

```bash
cd backend
python -c "
import json
from pathlib import Path
data = json.loads(Path('app/mcp/default_settings.json').read_text())
assert 'ask_brainstorm_command' in data
print('OK:', data['ask_brainstorm_command'])
"
```

Expected output: `OK: claude /ask-and-brainstorm $project_id`

- [ ] **Step 3: Commit**

```bash
git add backend/app/mcp/default_settings.json
git commit -m "feat: add ask_brainstorm_command setting"
```

---

### Task 3: Add AskTerminalCreate schema

**Files:**
- Modify: `backend/app/schemas/terminal.py`

- [ ] **Step 1: Add the schema**

Open `backend/app/schemas/terminal.py` and add after `TerminalCreate`:

```python
class AskTerminalCreate(BaseModel):
    project_id: str
```

The full file becomes:
```python
from datetime import datetime

from pydantic import BaseModel


class TerminalCreate(BaseModel):
    issue_id: str
    project_id: str
    run_commands: bool = True


class AskTerminalCreate(BaseModel):
    project_id: str


class TerminalResponse(BaseModel):
    id: str
    issue_id: str
    project_id: str
    project_path: str
    status: str
    created_at: datetime
    cols: int
    rows: int


class TerminalListResponse(BaseModel):
    id: str
    issue_id: str
    project_id: str
    project_path: str
    issue_name: str | None = None
    project_name: str | None = None
    status: str
    created_at: datetime
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/terminal.py
git commit -m "feat: add AskTerminalCreate schema"
```

---

### Task 4: Write failing tests for POST /api/terminals/ask

**Files:**
- Create: `backend/tests/test_ask_terminal.py`

- [ ] **Step 1: Write the test file**

`backend/tests/test_ask_terminal.py`:
```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.routers.terminals import get_terminal_service


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.create = MagicMock(return_value={
        "id": "term-ask-1",
        "issue_id": "",
        "project_id": "proj-1",
        "project_path": "C:/fake",
        "status": "active",
        "created_at": "2026-03-29T00:00:00Z",
        "cols": 120,
        "rows": 30,
    })
    svc.get_pty = MagicMock(return_value=MagicMock())
    return svc


@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_terminal_service] = lambda: mock_service
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_ask_terminal(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=True):
        mock_path.return_value = "C:/fake"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "term-ask-1"
        assert data["project_id"] == "proj-1"


@pytest.mark.asyncio
async def test_create_ask_terminal_invalid_project(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path:
        mock_path.side_effect = ValueError("Project not found")
        resp = await client.post("/api/terminals/ask", json={"project_id": "nonexistent"})
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_ask_terminal_invalid_path(client, mock_service):
    with patch("app.routers.terminals.get_project_path", new_callable=AsyncMock) as mock_path, \
         patch("app.routers.terminals.os.path.isdir", return_value=False):
        mock_path.return_value = "C:/does-not-exist"
        resp = await client.post("/api/terminals/ask", json={"project_id": "proj-1"})
        assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_ask_terminal.py -v
```

Expected: FAIL — `404 Not Found` (endpoint doesn't exist yet)

---

### Task 5: Implement POST /api/terminals/ask

**Files:**
- Modify: `backend/app/routers/terminals.py`

- [ ] **Step 1: Add import and endpoint**

At the top of `backend/app/routers/terminals.py`, add `AskTerminalCreate` to the schema import:

```python
from app.schemas.terminal import AskTerminalCreate, TerminalCreate, TerminalListResponse, TerminalResponse
```

Then add the new endpoint **before** `@router.get("")` (after the existing `create_terminal` endpoint, around line 157):

```python
@router.post("/ask", response_model=TerminalResponse, status_code=201)
async def create_ask_terminal(
    data: AskTerminalCreate,
    db: AsyncSession = Depends(get_db),
    service: TerminalService = Depends(get_terminal_service),
):
    try:
        project_path = await get_project_path(data.project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.isdir(project_path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {project_path}")

    # Fetch project shell config
    from app.models.project import Project
    project_obj = await db.get(Project, data.project_id)
    project_shell = project_obj.shell if project_obj else None

    try:
        terminal = service.create(
            issue_id="",
            project_id=data.project_id,
            project_path=project_path,
            shell=project_shell,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to spawn terminal: {e}")

    # Inject Manager AI environment variables
    try:
        pty = service.get_pty(terminal["id"])
        env_vars = {
            "MANAGER_AI_TERMINAL_ID": terminal["id"],
            "MANAGER_AI_PROJECT_ID": data.project_id,
            "MANAGER_AI_BASE_URL": f"http://localhost:{os.environ.get('BACKEND_PORT', '8000')}",
        }
        import platform
        set_cmd = "set" if platform.system() == "Windows" else "export"
        env_commands = " && ".join(f"{set_cmd} {k}={v}" for k, v in env_vars.items())
        pty.write(env_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject env vars for ask terminal %s", terminal["id"], exc_info=True)

    # Inject project custom variables
    try:
        from app.services.project_variable_service import ProjectVariableService
        var_svc = ProjectVariableService(db)
        custom_vars = await var_svc.list(data.project_id)
        if custom_vars:
            pty = service.get_pty(terminal["id"])
            import platform
            set_cmd = "set" if platform.system() == "Windows" else "export"
            var_commands = " && ".join(f"{set_cmd} {v.name}={v.value}" for v in custom_vars)
            pty.write(var_commands + "\r\n")
    except Exception:
        logger.warning("Failed to inject custom vars for ask terminal %s", terminal["id"], exc_info=True)

    # Read and inject the ask_brainstorm_command from settings
    try:
        from app.services.settings_service import SettingsService
        settings_svc = SettingsService(db)
        cmd = await settings_svc.get("ask_brainstorm_command")
        variables = {
            "$project_id": data.project_id,
            "$project_path": project_path,
        }
        for var, val in variables.items():
            cmd = cmd.replace(var, val)
        pty = service.get_pty(terminal["id"])
        pty.write(cmd + "\r\n")
    except Exception:
        logger.warning("Failed to inject ask command for terminal %s", terminal["id"], exc_info=True)

    return TerminalResponse(**terminal)
```

**Important:** The `/ask` route must be registered **before** any `/{terminal_id}` parameterized routes to avoid FastAPI matching "ask" as a terminal ID. The existing code already has a comment about this pattern (see `# NOTE: /config and /count MUST be defined before /{terminal_id} routes`). Place `POST /ask` before `GET /config`.

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_ask_terminal.py -v
```

Expected:
```
PASSED tests/test_ask_terminal.py::test_create_ask_terminal
PASSED tests/test_ask_terminal.py::test_create_ask_terminal_invalid_project
PASSED tests/test_ask_terminal.py::test_create_ask_terminal_invalid_path
```

- [ ] **Step 3: Run full test suite to confirm no regressions**

```bash
cd backend
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/terminals.py backend/tests/test_ask_terminal.py
git commit -m "feat: add POST /api/terminals/ask endpoint"
```

---

### Task 6: Frontend — types, API, hook

**Files:**
- Modify: `frontend/src/shared/types/index.ts`
- Modify: `frontend/src/features/terminals/api.ts`
- Modify: `frontend/src/features/terminals/hooks.ts`

- [ ] **Step 1: Add AskTerminalCreate type**

In `frontend/src/shared/types/index.ts`, find the `// ── Terminal ──` section and add after `TerminalCreate`:

```typescript
export interface AskTerminalCreate {
  project_id: string;
}
```

- [ ] **Step 2: Add createAskTerminal API function**

In `frontend/src/features/terminals/api.ts`, add the import of `AskTerminalCreate` to the existing import line:

```typescript
import type { AskTerminalCreate, Terminal, TerminalCommand, ... } from "@/shared/types";
```

Then add the function after `createTerminal`:

```typescript
export function createAskTerminal(data: AskTerminalCreate): Promise<Terminal> {
  return request("/terminals/ask", { method: "POST", body: JSON.stringify(data) });
}
```

- [ ] **Step 3: Add useCreateAskTerminal hook**

In `frontend/src/features/terminals/hooks.ts`, add the import of `AskTerminalCreate`:

```typescript
import type { AskTerminalCreate, TerminalCreate, TerminalCommandUpdate } from "@/shared/types";
```

Then add the hook after `useCreateTerminal`:

```typescript
export function useCreateAskTerminal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AskTerminalCreate) => api.createAskTerminal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: terminalKeys.all });
      queryClient.invalidateQueries({ queryKey: terminalKeys.count });
    },
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/shared/types/index.ts frontend/src/features/terminals/api.ts frontend/src/features/terminals/hooks.ts
git commit -m "feat: add AskTerminalCreate type, API function, and hook"
```

---

### Task 7: Frontend — Ask & Brainstorming page

**Files:**
- Create: `frontend/src/routes/projects/$projectId/ask.tsx`

- [ ] **Step 1: Create the route file**

`frontend/src/routes/projects/$projectId/ask.tsx`:

```tsx
import { useState, useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { MessageSquare } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { TerminalPanel } from "@/features/terminals/components/terminal-panel";
import { useCreateAskTerminal } from "@/features/terminals/hooks";
import { useProject } from "@/features/projects/hooks";
import { toast } from "sonner";

export const Route = createFileRoute("/projects/$projectId/ask")({
  component: AskPage,
});

function AskPage() {
  const { projectId } = Route.useParams();
  const { data: project } = useProject(projectId);
  const [terminalId, setTerminalId] = useState<string | null>(null);
  const createAskTerminal = useCreateAskTerminal();

  useEffect(() => {
    document.title = project ? `Ask & Brainstorming - ${project.name}` : "Ask & Brainstorming";
  }, [project]);

  const handleStart = async () => {
    try {
      const terminal = await createAskTerminal.mutateAsync({ project_id: projectId });
      setTerminalId(terminal.id);
    } catch (err) {
      toast.error("Failed to start session: " + (err instanceof Error ? err.message : "Unknown error"));
    }
  };

  const handleNewConversation = () => {
    setTerminalId(null);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div>
          {project && (
            <p className="text-sm text-muted-foreground mb-0.5">{project.name}</p>
          )}
          <h1 className="text-xl font-semibold">Ask & Brainstorming</h1>
        </div>
        {terminalId && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleNewConversation}
          >
            New conversation
          </Button>
        )}
      </div>

      {!terminalId ? (
        <div className="flex flex-col items-center justify-center flex-1 gap-4 p-6">
          <MessageSquare className="size-12 text-muted-foreground" />
          <div className="text-center">
            <h2 className="text-lg font-medium mb-1">Start a brainstorming session</h2>
            <p className="text-sm text-muted-foreground max-w-md">
              Claude will load your project context and help you think through ideas, architectural decisions, and creative directions. You can also ask it to create issues.
            </p>
          </div>
          <Button
            onClick={handleStart}
            disabled={createAskTerminal.isPending}
          >
            {createAskTerminal.isPending ? "Starting..." : "Start conversation"}
          </Button>
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <TerminalPanel
            terminalId={terminalId}
            onSessionEnd={handleNewConversation}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/routes/projects/\$projectId/ask.tsx
git commit -m "feat: add Ask & Brainstorming page route"
```

---

### Task 8: Frontend — routeTree and sidebar

**Files:**
- Modify: `frontend/src/routeTree.gen.ts`
- Modify: `frontend/src/shared/components/app-sidebar.tsx`

- [ ] **Step 1: Update routeTree.gen.ts**

In `frontend/src/routeTree.gen.ts`:

**Add import** (with the other project route imports):
```typescript
import { Route as ProjectsProjectIdAskRouteImport } from "./routes/projects/$projectId/ask"
```

**Add const** (with the other project route consts, after `ProjectsProjectIdActivityRoute`):
```typescript
const ProjectsProjectIdAskRoute = ProjectsProjectIdAskRouteImport.update({
  id: "/ask",
  path: "/ask",
  getParentRoute: () => ProjectsProjectIdRoute,
} as any)
```

**Add to FileRoutesByPath** (inside the interface, with the other project routes):
```typescript
"/projects/$projectId/ask": {
  id: "/projects/$projectId/ask"
  path: "/ask"
  fullPath: "/projects/$projectId/ask"
  preLoaderRoute: typeof ProjectsProjectIdAskRouteImport
  parentRoute: typeof ProjectsProjectIdRoute
}
```

**Add to ProjectsProjectIdRouteChildren interface**:
```typescript
interface ProjectsProjectIdRouteChildren {
  ProjectsProjectIdActivityRoute: typeof ProjectsProjectIdActivityRoute
  ProjectsProjectIdAskRoute: typeof ProjectsProjectIdAskRoute
  ProjectsProjectIdCommandsRoute: typeof ProjectsProjectIdCommandsRoute
  ProjectsProjectIdFilesRoute: typeof ProjectsProjectIdFilesRoute
  ProjectsProjectIdIssuesRoute: typeof ProjectsProjectIdIssuesRouteWithChildren
  ProjectsProjectIdLibraryRoute: typeof ProjectsProjectIdLibraryRoute
  ProjectsProjectIdVariablesRoute: typeof ProjectsProjectIdVariablesRoute
}
```

**Add to ProjectsProjectIdRouteChildren const**:
```typescript
const ProjectsProjectIdRouteChildren: ProjectsProjectIdRouteChildren = {
  ProjectsProjectIdActivityRoute: ProjectsProjectIdActivityRoute,
  ProjectsProjectIdAskRoute: ProjectsProjectIdAskRoute,
  ProjectsProjectIdCommandsRoute: ProjectsProjectIdCommandsRoute,
  ProjectsProjectIdFilesRoute: ProjectsProjectIdFilesRoute,
  ProjectsProjectIdIssuesRoute: ProjectsProjectIdIssuesRouteWithChildren,
  ProjectsProjectIdLibraryRoute: ProjectsProjectIdLibraryRoute,
  ProjectsProjectIdVariablesRoute: ProjectsProjectIdVariablesRoute,
}
```

- [ ] **Step 2: Update app-sidebar.tsx**

In `frontend/src/shared/components/app-sidebar.tsx`:

**Add `MessageSquare` to the lucide-react import:**
```typescript
import {
  Activity,
  BookOpen,
  CircleDot,
  Download,
  FileText,
  FolderSync,
  Key,
  LayoutDashboard,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Plug,
  Settings,
  SquareTerminal,
  Terminal,
} from "lucide-react";
```

**Add nav item** in the `projectNav` array, between "Activity" and "Library":
```typescript
{
  label: "Activity",
  to: "/projects/$projectId/activity" as const,
  params: { projectId },
  icon: Activity,
},
{
  label: "Ask & Brainstorming",
  to: "/projects/$projectId/ask" as const,
  params: { projectId },
  icon: MessageSquare,
},
{
  label: "Library",
  to: "/projects/$projectId/library" as const,
  params: { projectId },
  icon: BookOpen,
},
```

- [ ] **Step 3: Verify frontend lints clean**

```bash
cd frontend
npm run lint
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routeTree.gen.ts frontend/src/shared/components/app-sidebar.tsx
git commit -m "feat: register ask route and add Ask & Brainstorming sidebar item"
```

---

## Summary

8 tasks, ~20 steps total. Backend is TDD (tests written before endpoint). Frontend follows existing patterns exactly (same structure as `library.tsx`, same hook pattern as `useCreateTerminal`).

After completing all tasks, the flow is:
1. User opens "Ask & Brainstorming" in sidebar
2. Clicks "Start conversation" → `POST /api/terminals/ask`
3. Backend reads `ask_brainstorm_command` from settings, resolves `$project_id`, spawns PTY and injects `claude /ask-and-brainstorm <project_id>`
4. Claude reads `ask-and-brainstorm.md`, calls `get_project_context`, enters listening mode
5. `TerminalPanel` renders inline via WebSocket
6. Terminal also visible in `/terminals` list
7. `ask_brainstorm_command` is editable in `/settings` like any other setting
