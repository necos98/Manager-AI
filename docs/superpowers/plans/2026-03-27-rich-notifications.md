# Rich Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich all WebSocket notification toasts with project name and issue name so the user sees `IssueName` as toast title and `ProjectName • event description` as description.

**Architecture:** Backend — add `project_name` and `issue_name` to every emitted event that has project/issue context. Frontend — replace flat toast call with a `buildToast()` helper that maps event type to readable title + description.

**Tech Stack:** Python/FastAPI backend, React/TypeScript frontend, sonner for toasts, WebSocket via EventService.

---

## File Map

| File | Change |
|---|---|
| `backend/app/hooks/registry.py` | Add `issue_name`/`project_name` from `HookContext.metadata` to all 3 hook event emits |
| `backend/app/services/issue_service.py` | Add project fetch + metadata to `accept_issue` and `cancel_issue` |
| `backend/app/mcp/server.py` | Add project fetch + `project_name` to `send_notification`; pass `project_name` to `embed_issue` |
| `backend/app/services/rag_service.py` | Add `project_name: str` param to `embed_file`/`embed_issue`; include in all emitted events |
| `backend/app/routers/files.py` | Capture project from `_check_project()` and pass `.name` to `embed_file` |
| `backend/tests/test_hook_registry.py` | Assert `issue_name`/`project_name` present in emitted hook events |
| `backend/tests/test_issue_service_hooks.py` | Assert `accept_issue` and `cancel_issue` pass metadata with names |
| `backend/tests/test_rag_service.py` | Update calls to pass `project_name`; assert field present in emitted events |
| `frontend/src/shared/context/event-context.tsx` | Add `buildToast()`, replace flat toast call |

---

### Task 1: Enrich hook events in `registry.py`

**Files:**
- Modify: `backend/app/hooks/registry.py`
- Test: `backend/tests/test_hook_registry.py`

- [ ] **Step 1: Write failing tests**

Open `backend/tests/test_hook_registry.py` and add these two tests at the end of the file:

```python
class SuccessHook(BaseHook):
    name = "success_hook"
    description = "A hook that succeeds"

    async def execute(self, context: HookContext) -> HookResult:
        return HookResult(success=True, output="done")


@patch("app.hooks.registry.event_service")
async def test_hook_events_include_issue_and_project_name(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    ctx = HookContext(
        project_id="p1",
        issue_id="i1",
        event=HookEvent.ISSUE_COMPLETED,
        metadata={"issue_name": "Fix login bug", "project_name": "My Project"},
    )
    await registry._run_hook(SuccessHook, ctx)
    # hook_started event
    started = mock_event_service.emit.call_args_list[0][0][0]
    assert started["issue_name"] == "Fix login bug"
    assert started["project_name"] == "My Project"
    # hook_completed event
    completed = mock_event_service.emit.call_args_list[1][0][0]
    assert completed["issue_name"] == "Fix login bug"
    assert completed["project_name"] == "My Project"


@patch("app.hooks.registry.event_service")
async def test_hook_failed_event_includes_names(mock_event_service):
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    ctx = HookContext(
        project_id="p1",
        issue_id="i1",
        event=HookEvent.ISSUE_COMPLETED,
        metadata={"issue_name": "Fix login bug", "project_name": "My Project"},
    )
    await registry._run_hook(FailingHook, ctx)
    failed = mock_event_service.emit.call_args_list[1][0][0]
    assert failed["issue_name"] == "Fix login bug"
    assert failed["project_name"] == "My Project"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_hook_registry.py::test_hook_events_include_issue_and_project_name tests/test_hook_registry.py::test_hook_failed_event_includes_names -v
```

Expected: FAIL — `KeyError` or `AssertionError` because the fields are not yet in the events.

- [ ] **Step 3: Update `_run_hook` in `registry.py`**

In `backend/app/hooks/registry.py`, replace the `_run_hook` method (lines 66–121) with:

```python
async def _run_hook(
    self, hook_class: type[BaseHook], context: HookContext
) -> None:
    hook = hook_class()
    now = datetime.now(timezone.utc).isoformat()

    await event_service.emit(
        {
            "type": "hook_started",
            "hook_name": hook.name,
            "hook_description": hook.description,
            "issue_id": context.issue_id,
            "project_id": context.project_id,
            "issue_name": context.metadata.get("issue_name", ""),
            "project_name": context.metadata.get("project_name", ""),
            "timestamp": now,
        }
    )

    try:
        result = await hook.execute(context)
    except Exception as exc:  # noqa: BLE001
        logger.error("Hook %s failed with exception: %s", hook.name, exc)
        await event_service.emit(
            {
                "type": "hook_failed",
                "hook_name": hook.name,
                "issue_id": context.issue_id,
                "project_id": context.project_id,
                "issue_name": context.metadata.get("issue_name", ""),
                "project_name": context.metadata.get("project_name", ""),
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return

    if result.success:
        await event_service.emit(
            {
                "type": "hook_completed",
                "hook_name": hook.name,
                "issue_id": context.issue_id,
                "project_id": context.project_id,
                "issue_name": context.metadata.get("issue_name", ""),
                "project_name": context.metadata.get("project_name", ""),
                "output": result.output,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    else:
        logger.warning("Hook %s returned error: %s", hook.name, result.error)
        await event_service.emit(
            {
                "type": "hook_failed",
                "hook_name": hook.name,
                "issue_id": context.issue_id,
                "project_id": context.project_id,
                "issue_name": context.metadata.get("issue_name", ""),
                "project_name": context.metadata.get("project_name", ""),
                "error": result.error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
```

- [ ] **Step 4: Run full hook registry tests**

```bash
cd backend && python -m pytest tests/test_hook_registry.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/hooks/registry.py backend/tests/test_hook_registry.py
git commit -m "feat: add issue_name and project_name to hook events"
```

---

### Task 2: Enrich `accept_issue` and `cancel_issue` hooks

**Files:**
- Modify: `backend/app/services/issue_service.py`
- Test: `backend/tests/test_issue_service_hooks.py`

- [ ] **Step 1: Write failing tests**

In `backend/tests/test_issue_service_hooks.py`, replace `test_accept_issue_fires_hook` and `test_cancel_issue_fires_hook` with versions that assert on metadata:

```python
@patch("app.services.issue_service.hook_registry")
async def test_accept_issue_fires_hook_with_metadata(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Accept me", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_ACCEPTED
    ctx = args[0][1]
    assert ctx.metadata.get("issue_name") == "Accept me"
    assert ctx.metadata.get("project_name") == "Test"


@patch("app.services.issue_service.hook_registry")
async def test_cancel_issue_fires_hook_with_metadata(mock_registry, db_session, project):
    mock_registry.fire = AsyncMock()
    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Cancel me", priority=1)
    await service.cancel_issue(issue.id, project.id)
    mock_registry.fire.assert_called_once()
    args = mock_registry.fire.call_args
    assert args[0][0] == HookEvent.ISSUE_CANCELLED
    ctx = args[0][1]
    assert ctx.metadata.get("issue_name") == "Cancel me"
    assert ctx.metadata.get("project_name") == "Test"
```

Note: the `project` fixture in this file creates a project with `name="Test"`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_issue_service_hooks.py::test_accept_issue_fires_hook_with_metadata tests/test_issue_service_hooks.py::test_cancel_issue_fires_hook_with_metadata -v
```

Expected: FAIL — `ctx.metadata` is `{}`.

- [ ] **Step 3: Update `accept_issue` in `issue_service.py`**

Replace the `accept_issue` method (lines 178–190) with:

```python
async def accept_issue(self, issue_id: str, project_id: str) -> Issue:
    issue = await self.get_for_project(issue_id, project_id)
    if issue.status != IssueStatus.PLANNED:
        raise InvalidTransitionError(
            f"Can only accept issues in Planned status, got {issue.status.value}"
        )
    issue.status = IssueStatus.ACCEPTED
    await self.session.flush()
    project = await ProjectService(self.session).get_by_id(project_id)
    await hook_registry.fire(
        HookEvent.ISSUE_ACCEPTED,
        HookContext(
            project_id=project_id,
            issue_id=issue_id,
            event=HookEvent.ISSUE_ACCEPTED,
            metadata={
                "issue_name": issue.name or (issue.description or "")[:50] or "Untitled",
                "project_name": project.name if project else "",
            },
        ),
    )
    return issue
```

- [ ] **Step 4: Update `cancel_issue` in `issue_service.py`**

Replace the `cancel_issue` method (lines 192–200) with:

```python
async def cancel_issue(self, issue_id: str, project_id: str) -> Issue:
    issue = await self.get_for_project(issue_id, project_id)
    issue.status = IssueStatus.CANCELED
    await self.session.flush()
    project = await ProjectService(self.session).get_by_id(project_id)
    await hook_registry.fire(
        HookEvent.ISSUE_CANCELLED,
        HookContext(
            project_id=project_id,
            issue_id=issue_id,
            event=HookEvent.ISSUE_CANCELLED,
            metadata={
                "issue_name": issue.name or (issue.description or "")[:50] or "Untitled",
                "project_name": project.name if project else "",
            },
        ),
    )
    return issue
```

- [ ] **Step 5: Run all issue service hook tests**

```bash
cd backend && python -m pytest tests/test_issue_service_hooks.py -v
```

Expected: all 5 tests PASS (3 original + 2 new).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/issue_service.py backend/tests/test_issue_service_hooks.py
git commit -m "feat: pass issue_name and project_name in accept/cancel hook context"
```

---

### Task 3: Add `project_name` to `send_notification` in `server.py`

**Files:**
- Modify: `backend/app/mcp/server.py`

No new test file needed — `send_notification` is an MCP tool wired to event_service; the pattern is identical to what was already tested in the registry.

- [ ] **Step 1: Update `send_notification`**

In `backend/app/mcp/server.py`, replace the `send_notification` function (lines 214–232) with:

```python
@mcp.tool(description=_desc["tool.send_notification.description"])
async def send_notification(project_id: str, issue_id: str, title: str, message: str = "") -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.get_for_project(issue_id, project_id)
        except AppError as e:
            return {"error": e.message}
        issue_name = issue.name or (issue.description or "")[:50] or "Untitled issue"
        project = await ProjectService(session).get_by_id(project_id)
        project_name = project.name if project else ""
        await event_service.emit({
            "type": "notification",
            "title": title,
            "message": message,
            "project_id": project_id,
            "issue_id": issue_id,
            "issue_name": issue_name,
            "project_name": project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"success": True}
```

- [ ] **Step 2: Run related tests to verify no regression**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py -v
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/app/mcp/server.py
git commit -m "feat: add project_name to send_notification event"
```

---

### Task 4: Add `project_name` to `RagService` embedding events

**Files:**
- Modify: `backend/app/services/rag_service.py`
- Test: `backend/tests/test_rag_service.py`

- [ ] **Step 1: Write failing tests**

In `backend/tests/test_rag_service.py`, update the two existing embedding tests and add one new assertion. Replace `test_embed_file_async` and `test_embed_issue_async` with:

```python
async def test_embed_file_async(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/test.txt", mime_type="text/plain",
        original_name="test.txt", project_name="My Project",
    )
    mock_pipeline.embed_file.assert_called_once()
    mock_event_service.emit.assert_called_once()
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_completed"
    assert event["project_name"] == "My Project"
    assert event["project_id"] == "p1"


async def test_embed_issue_async(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_issue(
        project_id="p1", source_id="i1",
        issue_data={"name": "Test", "specification": "spec"},
        project_name="My Project",
    )
    mock_pipeline.embed_issue.assert_called_once()
    event = mock_event_service.emit.call_args[0][0]
    assert event["project_name"] == "My Project"
    assert event["project_id"] == "p1"
```

Also update `test_embed_file_skipped` and `test_embed_file_failure_broadcasts_event` to pass `project_name="My Project"`:

```python
async def test_embed_file_skipped(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    mock_pipeline.embed_file.return_value = "skipped"
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/test.docx", mime_type="application/msword",
        original_name="test.docx", project_name="My Project",
    )
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_skipped"


async def test_embed_file_failure_broadcasts_event(mock_pipeline, mock_event_service):
    from app.services.rag_service import RagService
    mock_pipeline.embed_file.side_effect = RuntimeError("extraction failed")
    svc = RagService(pipeline=mock_pipeline, event_service=mock_event_service)
    await svc.embed_file(
        project_id="p1", source_id="f1",
        file_path="/fake/test.txt", mime_type="text/plain",
        original_name="test.txt", project_name="My Project",
    )
    event = mock_event_service.emit.call_args[0][0]
    assert event["type"] == "embedding_failed"
    assert "extraction failed" in event["error"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_rag_service.py -v
```

Expected: FAIL — `embed_file`/`embed_issue` don't accept `project_name` yet.

- [ ] **Step 3: Update `embed_file` in `rag_service.py`**

Replace the `embed_file` method signature and body with:

```python
async def embed_file(
    self,
    project_id: str,
    source_id: str,
    file_path: str,
    mime_type: str,
    original_name: str,
    project_name: str = "",
):
    """Embed a file asynchronously (runs CPU-bound work in thread)."""
    async with _source_lock(source_id):
        try:
            result = await asyncio.to_thread(
                self.pipeline.embed_file,
                project_id=project_id,
                source_id=source_id,
                file_path=file_path,
                mime_type=mime_type,
                original_name=original_name,
            )
            if result == "skipped":
                await self.event_service.emit({
                    "type": "embedding_skipped",
                    "source_type": "file",
                    "source_id": source_id,
                    "title": original_name,
                    "reason": f"No extractor for MIME type: {mime_type}",
                    "project_id": project_id,
                    "project_name": project_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                await self.event_service.emit({
                    "type": "embedding_completed",
                    "source_type": "file",
                    "source_id": source_id,
                    "title": original_name,
                    "project_id": project_id,
                    "project_name": project_name,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        except Exception as e:
            logger.exception("Embedding failed for file %s", source_id)
            await self.event_service.emit({
                "type": "embedding_failed",
                "source_type": "file",
                "source_id": source_id,
                "title": original_name,
                "error": str(e),
                "project_id": project_id,
                "project_name": project_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
```

- [ ] **Step 4: Update `embed_issue` in `rag_service.py`**

Replace the `embed_issue` method signature and body with:

```python
async def embed_issue(self, project_id: str, source_id: str, issue_data: dict, project_name: str = ""):
    """Embed a completed issue asynchronously."""
    title = issue_data.get("name") or "Untitled Issue"
    async with _source_lock(source_id):
        try:
            await asyncio.to_thread(
                self.pipeline.embed_issue,
                project_id=project_id,
                source_id=source_id,
                issue_data=issue_data,
            )
            await self.event_service.emit({
                "type": "embedding_completed",
                "source_type": "issue",
                "source_id": source_id,
                "title": title,
                "project_id": project_id,
                "project_name": project_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.exception("Embedding failed for issue %s", source_id)
            await self.event_service.emit({
                "type": "embedding_failed",
                "source_type": "issue",
                "source_id": source_id,
                "title": title,
                "error": str(e),
                "project_id": project_id,
                "project_name": project_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
```

- [ ] **Step 5: Run rag service tests**

```bash
cd backend && python -m pytest tests/test_rag_service.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/rag_service.py backend/tests/test_rag_service.py
git commit -m "feat: add project_name and project_id to embedding events"
```

---

### Task 5: Update `RagService` call sites

**Files:**
- Modify: `backend/app/mcp/server.py` (complete_issue)
- Modify: `backend/app/routers/files.py` (upload_files)

- [ ] **Step 1: Update `complete_issue` in `server.py` to pass `project_name`**

In `backend/app/mcp/server.py`, replace the `complete_issue` function (lines 109–135) with:

```python
@mcp.tool(description=_desc["tool.complete_issue.description"])
async def complete_issue(project_id: str, issue_id: str, recap: str) -> dict:
    async with async_session() as session:
        issue_service = IssueService(session)
        try:
            issue = await issue_service.complete_issue(issue_id, project_id, recap)
            # Extract data while session is open
            issue_data = {
                "name": issue.name or (issue.description or "")[:100],
                "specification": issue.specification,
                "plan": issue.plan,
                "recap": issue.recap,
            }
            issue_id_val = issue.id
            project = await ProjectService(session).get_by_id(project_id)
            project_name = project.name if project else ""
            await session.commit()

            # Trigger async embedding
            rag = get_rag_service()
            asyncio.create_task(rag.embed_issue(
                project_id=project_id,
                source_id=issue_id_val,
                issue_data=issue_data,
                project_name=project_name,
            ))

            return {"id": issue_id_val, "status": issue.status.value, "recap": issue.recap}
        except AppError as e:
            return {"error": e.message}
```

- [ ] **Step 2: Update `upload_files` in `files.py` to pass `project_name`**

In `backend/app/routers/files.py`, replace the `upload_files` endpoint (lines 36–56) with:

```python
@router.post("", response_model=list[ProjectFileResponse], status_code=201)
async def upload_files(project_id: str, files: list[UploadFile], db: AsyncSession = Depends(get_db)):
    project = await _check_project(project_id, db)
    service = FileService(db)
    try:
        records = await service.upload_files(project_id, files)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    # Trigger async embedding for each uploaded file
    rag = get_rag_service()
    for record in records:
        file_path = service.get_file_path(project_id, record.stored_name)
        asyncio.create_task(rag.embed_file(
            project_id=project_id,
            source_id=record.id,
            file_path=file_path,
            mime_type=record.mime_type,
            original_name=record.original_name,
            project_name=project.name,
        ))
    return [ProjectFileResponse.from_model(r) for r in records]
```

- [ ] **Step 3: Run full backend test suite**

```bash
cd backend && python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/app/mcp/server.py backend/app/routers/files.py
git commit -m "feat: pass project_name to embed_issue and embed_file call sites"
```

---

### Task 6: Update frontend toast logic

**Files:**
- Modify: `frontend/src/shared/context/event-context.tsx`

- [ ] **Step 1: Replace `ws.onmessage` handler in `event-context.tsx`**

Replace the entire file content with:

```typescript
import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { queryClient } from "@/shared/lib/query-client";

interface EventContextValue {
  // Extensible if needed
}

const EventContext = createContext<EventContextValue | null>(null);

const notificationAudio = new Audio("/sounds/notification.wav");
notificationAudio.volume = 0.5;

function unlockAudio() {
  notificationAudio
    .play()
    .then(() => {
      notificationAudio.pause();
      notificationAudio.currentTime = 0;
    })
    .catch(() => {});
  document.removeEventListener("click", unlockAudio);
  document.removeEventListener("keydown", unlockAudio);
}
document.addEventListener("click", unlockAudio);
document.addEventListener("keydown", unlockAudio);

function playNotificationSound() {
  try {
    notificationAudio.currentTime = 0;
    notificationAudio.play().catch(() => {});
  } catch {
    // Audio API unavailable
  }
}

function buildToast(data: Record<string, unknown>): { title: string; description: string } {
  const type = data.type as string;
  const issueName = (data.issue_name as string) || "";
  const projectName = (data.project_name as string) || "";
  const title = (data.title as string) || "";
  const message = (data.message as string) || "";
  const hookName = (data.hook_name as string) || "";
  const error = (data.error as string) || "";

  const prefix = projectName ? `${projectName} • ` : "";

  switch (type) {
    case "notification":
      return {
        title: issueName || "Notifica",
        description: `${prefix}${message}`,
      };
    case "hook_started":
      return {
        title: issueName || "Hook avviato",
        description: `${prefix}${hookName} in esecuzione…`,
      };
    case "hook_completed":
      return {
        title: issueName || "Hook completato",
        description: `${prefix}${hookName} completato`,
      };
    case "hook_failed":
      return {
        title: issueName || "Hook fallito",
        description: `${prefix}${error || "Errore sconosciuto"}`,
      };
    case "embedding_completed":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding completato`,
      };
    case "embedding_failed":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding fallito: ${error}`,
      };
    case "embedding_skipped":
      return {
        title: title || "Embedding",
        description: `${prefix}Embedding saltato`,
      };
    default:
      return {
        title: issueName || title || "Evento",
        description: `${prefix}${message || "New event"}`,
      };
  }
}

export function EventProvider({ children }: { children: React.ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const backoffRef = useRef(1000);
  const cleanedUpRef = useRef(false);
  const navigate = useNavigate();

  const connect = useCallback(() => {
    if (cleanedUpRef.current) return;

    const backendPort = import.meta.env.VITE_BACKEND_PORT || "8000";
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.hostname}:${backendPort}/api/events/ws`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      if (cleanedUpRef.current) {
        ws.close();
        return;
      }
      backoffRef.current = 1000;
    };

    ws.onmessage = (event) => {
      if (cleanedUpRef.current) return;
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;
        const projectId = data.project_id as string | undefined;
        const issueId = data.issue_id as string | undefined;

        const { title, description } = buildToast(data);

        toast(title, {
          description,
          action:
            projectId && issueId
              ? {
                  label: "View",
                  onClick: () => {
                    navigate({
                      to: "/projects/$projectId/issues/$issueId",
                      params: { projectId, issueId },
                    });
                  },
                }
              : undefined,
        });

        playNotificationSound();

        // Invalidate relevant queries for real-time updates
        if (projectId && issueId) {
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId, "issues", issueId],
          });
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId, "issues"],
          });
        } else if (projectId) {
          queryClient.invalidateQueries({
            queryKey: ["projects", projectId],
          });
        }
      } catch {
        // Ignore unparseable messages
      }
    };

    ws.onclose = () => {
      if (cleanedUpRef.current) return;
      const delay = Math.min(backoffRef.current, 30000);
      backoffRef.current = Math.min(backoffRef.current * 2, 30000);
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [navigate]);

  useEffect(() => {
    cleanedUpRef.current = false;
    connect();

    return () => {
      cleanedUpRef.current = true;
      clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close();
        }
        wsRef.current = null;
      }
    };
  }, [connect]);

  return (
    <EventContext.Provider value={{}}>
      {children}
    </EventContext.Provider>
  );
}

export function useEvents() {
  return useContext(EventContext);
}
```

- [ ] **Step 2: Run ESLint**

```bash
cd frontend && npm run lint
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/shared/context/event-context.tsx
git commit -m "feat: rich toast notifications with project and issue names"
```

---

## Verification

After all tasks are complete, run the full backend suite one final time:

```bash
cd backend && python -m pytest -v
```

All tests must pass before considering the feature complete.
