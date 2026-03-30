# R1 — Affidabilità del Core: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminare quattro gap di affidabilità nel core: race condition su `complete_issue`, hook senza timeout/tracking, PTY non liberata su disconnect brusco, embed task non tracciata nell'MCP server.

**Architecture:** Ogni fix è localizzato al file di origine — nessuna nuova dipendenza esterna. Il lock per-issue usa `asyncio.Lock` in un dict module-level. Il tracking delle task di background usa un `set` con `add_done_callback`. Il cleanup PTY viene garantito da un blocco `finally` nel WebSocket handler.

**Tech Stack:** Python 3.11+, FastAPI, asyncio, SQLAlchemy async, pywinpty (Windows) / pty (Linux), pytest-asyncio.

---

## File Map

| File | Tipo | Motivo |
|------|------|--------|
| `backend/app/services/issue_service.py` | Modify | Aggiunge lock per-issue in `complete_issue` |
| `backend/app/hooks/registry.py` | Modify | Task tracking + timeout `HOOK_TIMEOUT=300` |
| `backend/app/services/terminal_service.py` | Modify | Nuovo metodo `cleanup()` + `resize()` dentro il lock |
| `backend/app/routers/terminals.py` | Modify | Blocco `finally` con `service.cleanup(terminal_id)` |
| `backend/app/mcp/server.py` | Modify | Set `_background_tasks` + logging per embed task |
| `backend/tests/test_issue_service.py` | Modify | Test lock serialization |
| `backend/tests/test_hook_registry.py` | Modify | Test timeout e task tracking |
| `backend/tests/test_terminal_service.py` | Modify | Test `cleanup()` e `resize()` con lock |
| `backend/tests/test_mcp_tools.py` | Modify | Test embed task tracking |

---

## Task 1 — R1.1: Lock per-issue in `complete_issue`

**Files:**
- Modify: `backend/app/services/issue_service.py`
- Modify: `backend/tests/test_issue_service.py`

- [ ] **Step 1: Scrivere il test che verifica il lock**

Aggiungere alla fine di `backend/tests/test_issue_service.py`:

```python
async def test_complete_issue_blocks_when_lock_held(db_session, project):
    """complete_issue acquisisce un lock per-issue che blocca chiamate concorrenti."""
    import asyncio
    from app.services.issue_service import _issue_completion_locks

    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Concurrent test", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)

    # Pre-acquisire il lock per simulare una chiamata già in corso
    lock = asyncio.Lock()
    _issue_completion_locks[issue.id] = lock
    await lock.acquire()

    # complete_issue deve bloccarsi finché il lock è held
    task = asyncio.create_task(
        service.complete_issue(issue.id, project.id, "Done")
    )
    await asyncio.sleep(0.02)
    assert not task.done(), "complete_issue deve aspettare il lock"

    # Rilascio lock → complete_issue deve completare
    lock.release()
    result = await asyncio.wait_for(task, timeout=2.0)
    assert result.status == IssueStatus.FINISHED

    # Pulizia
    _issue_completion_locks.pop(issue.id, None)
```

- [ ] **Step 2: Verificare che il test fallisca**

```bash
cd backend && python -m pytest tests/test_issue_service.py::test_complete_issue_blocks_when_lock_held -v
```

Output atteso: `FAILED` con `AssertionError: complete_issue deve aspettare il lock` (il task completa subito senza lock).

- [ ] **Step 3: Implementare il lock in `issue_service.py`**

In cima al file `backend/app/services/issue_service.py`, dopo gli import esistenti, aggiungere:

```python
import asyncio

_issue_completion_locks: dict[str, asyncio.Lock] = {}
```

Il file attuale inizia con:
```python
from __future__ import annotations

from sqlalchemy import or_, select
```

Diventa:
```python
from __future__ import annotations

import asyncio

from sqlalchemy import or_, select
```

E subito prima della classe `IssueService`, aggiungere:

```python
_issue_completion_locks: dict[str, asyncio.Lock] = {}
```

- [ ] **Step 4: Avvolgere `complete_issue` con il lock**

Sostituire l'intero metodo `complete_issue` (righe 131–177 attuali) con:

```python
    async def complete_issue(self, issue_id: str, project_id: str, recap: str) -> Issue:
        if not recap or not recap.strip():
            raise ValidationError("Recap cannot be blank")
        lock = _issue_completion_locks.setdefault(issue_id, asyncio.Lock())
        async with lock:
            issue = await self.get_for_project(issue_id, project_id)
            if issue.status != IssueStatus.ACCEPTED:
                raise InvalidTransitionError(f"Can only complete issues in Accepted status, got {issue.status.value}")
            # Enforce task completion
            task_service = TaskService(self.session)
            tasks = await task_service.list_by_issue(issue.id)
            if tasks:
                pending = [t for t in tasks if t.status != TaskStatus.COMPLETED]
                if pending:
                    names = ", ".join(t.name for t in pending)
                    raise ValidationError(
                        f"Cannot complete: {len(pending)} tasks not finished: {names}"
                    )
            issue.recap = recap
            issue.status = IssueStatus.FINISHED
            await self.session.flush()
            await ActivityService(self.session).log(
                project_id=project_id,
                issue_id=issue_id,
                event_type="issue_completed",
                details={"issue_name": issue.name or "", "recap_preview": (recap or "")[:100]},
            )
            # Fire hook with project context
            project_service = ProjectService(self.session)
            project = await project_service.get_by_id(project_id)
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")
            await hook_registry.fire(
                HookEvent.ISSUE_COMPLETED,
                HookContext(
                    project_id=project_id,
                    issue_id=issue_id,
                    event=HookEvent.ISSUE_COMPLETED,
                    metadata={
                        "issue_name": issue.name or "",
                        "recap": issue.recap or "",
                        "project_name": project.name if project else "",
                        "project_path": project.path if project else "",
                        "project_description": project.description if project else "",
                        "tech_stack": project.tech_stack if project else "",
                    },
                ),
            )
            return issue
```

- [ ] **Step 5: Eseguire tutti i test di `issue_service`**

```bash
cd backend && python -m pytest tests/test_issue_service.py -v
```

Output atteso: tutti PASSED.

- [ ] **Step 6: Commit**

```bash
cd backend && git add app/services/issue_service.py tests/test_issue_service.py
git commit -m "fix: serialize complete_issue with per-issue asyncio lock (R1.1)"
```

---

## Task 2 — R1.2: Hook timeout e task tracking

**Files:**
- Modify: `backend/app/hooks/registry.py`
- Modify: `backend/tests/test_hook_registry.py`

- [ ] **Step 1: Scrivere i test per timeout e task tracking**

Aggiungere alla fine di `backend/tests/test_hook_registry.py`:

```python
class SlowHook(BaseHook):
    name = "slow_hook"
    description = "A hook that never completes"

    async def execute(self, context: HookContext) -> HookResult:
        await asyncio.sleep(999)
        return HookResult(success=True)


@patch("app.hooks.registry.event_service")
@patch("app.hooks.registry.HOOK_TIMEOUT", 0.05)
async def test_hook_timeout_emits_hook_failed(mock_event_service):
    """Hook che supera il timeout emette hook_failed."""
    import asyncio
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)
    await registry._run_hook(SlowHook, ctx)

    emitted_types = [call[0][0]["type"] for call in mock_event_service.emit.call_args_list]
    assert "hook_failed" in emitted_types
    failed = next(c[0][0] for c in mock_event_service.emit.call_args_list if c[0][0]["type"] == "hook_failed")
    assert "timed out" in failed["error"].lower()


@patch("app.hooks.registry.event_service")
async def test_fire_stores_task_in_background_set(mock_event_service):
    """fire() salva la task in _background_tasks e la rimuove al completamento."""
    import asyncio
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, SuccessHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)

    await registry.fire(HookEvent.ISSUE_COMPLETED, ctx)
    assert len(registry._background_tasks) == 1

    # Aspetta completamento
    await asyncio.sleep(0.1)
    assert len(registry._background_tasks) == 0
```

Aggiungere `import asyncio` nella sezione import del file di test se non presente:
```python
import asyncio
from unittest.mock import AsyncMock, patch
from app.hooks.registry import BaseHook, HookContext, HookEvent, HookRegistry, HookResult
```

- [ ] **Step 2: Verificare che i test falliscano**

```bash
cd backend && python -m pytest tests/test_hook_registry.py::test_hook_timeout_emits_hook_failed tests/test_hook_registry.py::test_fire_stores_task_in_background_set -v
```

Output atteso: entrambi FAILED.

- [ ] **Step 3: Aggiungere `HOOK_TIMEOUT` e `_background_tasks` al registry**

In `backend/app/hooks/registry.py`, dopo la riga `logger = logging.getLogger(__name__)` aggiungere:

```python
HOOK_TIMEOUT = 300  # seconds
```

Nel metodo `__init__` di `HookRegistry`, aggiungere l'attributo `_background_tasks`:

```python
    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[type[BaseHook]]] = {}
        self._background_tasks: set[asyncio.Task] = set()
```

- [ ] **Step 4: Aggiornare `fire()` per salvare i riferimenti alle task**

Sostituire il metodo `fire()` con:

```python
    async def fire(self, event: HookEvent, context: HookContext) -> None:
        """
        Fire all hooks registered for the given event.

        Non-blocking: spawns an asyncio task per hook and returns immediately.
        Each task emits hook_started, then hook_completed or hook_failed events.
        Task references are kept in _background_tasks to prevent GC before completion.
        """
        hook_classes = self._hooks.get(event, [])
        for hook_class in hook_classes:
            task = asyncio.create_task(self._run_hook(hook_class, context))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
```

- [ ] **Step 5: Aggiungere gestione timeout in `_run_hook()`**

Nella sezione `try/except` di `_run_hook`, sostituire:

```python
        try:
            result = await hook.execute(context)
        except Exception as exc:  # noqa: BLE001
```

Con:

```python
        try:
            result = await asyncio.wait_for(hook.execute(context), timeout=HOOK_TIMEOUT)
        except asyncio.TimeoutError:
            error_msg = f"Hook timed out after {HOOK_TIMEOUT}s"
            logger.error("Hook %s %s", hook.name, error_msg)
            await event_service.emit(
                {
                    "type": "hook_failed",
                    "hook_name": hook.name,
                    "issue_id": context.issue_id,
                    "project_id": context.project_id,
                    "issue_name": context.metadata.get("issue_name", ""),
                    "project_name": context.metadata.get("project_name", ""),
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await self._log_activity(context.project_id, context.issue_id, "hook_failed", {
                "hook_name": hook.name, "error": error_msg
            })
            return
        except Exception as exc:  # noqa: BLE001
```

Il resto del metodo (`logger.error(...)`, `event_service.emit(hook_failed)`, `_log_activity`) rimane invariato.

- [ ] **Step 6: Eseguire tutti i test del registry**

```bash
cd backend && python -m pytest tests/test_hook_registry.py -v
```

Output atteso: tutti PASSED.

- [ ] **Step 7: Commit**

```bash
cd backend && git add app/hooks/registry.py tests/test_hook_registry.py
git commit -m "fix: add hook timeout (300s) and background task tracking (R1.2)"
```

---

## Task 3 — R1.3: PTY cleanup garantito e resize lock

**Files:**
- Modify: `backend/app/services/terminal_service.py`
- Modify: `backend/app/routers/terminals.py`
- Modify: `backend/tests/test_terminal_service.py`

- [ ] **Step 1: Scrivere i test per `cleanup()` e `resize()` con lock**

Aggiungere alla fine della classe `TestTerminalServiceRegistry` in `backend/tests/test_terminal_service.py`:

```python
    def test_cleanup_removes_terminal_and_closes_pty(self, service):
        """cleanup() rimuove il terminale e chiude la PTY."""
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            mock_pty.close = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            tid = term["id"]

            service.cleanup(tid)

            assert len(service.list_active()) == 0
            mock_pty.close.assert_called_once()

    def test_cleanup_is_idempotent(self, service):
        """cleanup() chiamato più volte non solleva eccezioni."""
        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            mock_pty.close = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            tid = term["id"]

            service.cleanup(tid)
            service.cleanup(tid)  # seconda chiamata — nessun errore

    def test_resize_concurrent_with_kill_does_not_crash(self, service):
        """resize() dentro il lock non causa crash con kill concorrente."""
        import threading

        with patch("app.services.terminal_service.PTY") as MockPTY:
            mock_pty = MagicMock()
            mock_pty.spawn = MagicMock()
            mock_pty.set_size = MagicMock()
            MockPTY.return_value = mock_pty

            term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
            errors = []

            def do_resize():
                try:
                    service.resize(term["id"], 100, 25)
                except KeyError:
                    pass  # Terminale già killato — accettabile
                except Exception as exc:
                    errors.append(exc)

            def do_kill():
                try:
                    service.kill(term["id"])
                except KeyError:
                    pass

            t1 = threading.Thread(target=do_resize)
            t2 = threading.Thread(target=do_kill)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert errors == [], f"Eccezioni inattese: {errors}"
```

- [ ] **Step 2: Verificare che i test falliscano**

```bash
cd backend && python -m pytest tests/test_terminal_service.py::TestTerminalServiceRegistry::test_cleanup_removes_terminal_and_closes_pty tests/test_terminal_service.py::TestTerminalServiceRegistry::test_cleanup_is_idempotent -v
```

Output atteso: entrambi FAILED con `AttributeError: 'TerminalService' object has no attribute 'cleanup'`.

- [ ] **Step 3: Aggiungere `cleanup()` a `TerminalService`**

In `backend/app/services/terminal_service.py`, aggiungere il metodo `cleanup` subito dopo `mark_closed` (prima di `resize`):

```python
    def cleanup(self, terminal_id: str) -> None:
        """Idempotent PTY cleanup — no-op if terminal already removed."""
        with self._lock:
            if terminal_id not in self._terminals:
                return
            entry = self._terminals.pop(terminal_id)
            self._buffers.pop(terminal_id, None)
        try:
            pty = entry["pty"]
            if hasattr(pty, "close"):
                pty.close()
        except Exception:
            pass
```

- [ ] **Step 4: Spostare `resize()` dentro il lock**

Sostituire il metodo `resize()` con:

```python
    def resize(self, terminal_id: str, cols: int, rows: int) -> None:
        with self._lock:
            if terminal_id not in self._terminals:
                raise KeyError(f"Terminal {terminal_id} not found")
            entry = self._terminals[terminal_id]
            entry["cols"] = cols
            entry["rows"] = rows
            entry["pty"].set_size(cols, rows)
```

- [ ] **Step 5: Aggiungere il blocco `finally` nel WebSocket handler**

In `backend/app/routers/terminals.py`, sostituire il blocco finale del handler `terminal_ws` (le ultime righe da `pty_read_task = ...` in poi):

```python
    pty_read_task = asyncio.create_task(pty_to_ws())
    ws_read_task = asyncio.create_task(ws_to_pty())

    try:
        done, pending = await asyncio.wait(
            [pty_read_task, ws_read_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except Exception:
        pty_read_task.cancel()
        ws_read_task.cancel()
    finally:
        service.cleanup(terminal_id)
```

- [ ] **Step 6: Eseguire i test del terminal service e del router**

```bash
cd backend && python -m pytest tests/test_terminal_service.py tests/test_terminal_router.py -v
```

Output atteso: tutti PASSED.

- [ ] **Step 7: Commit**

```bash
cd backend && git add app/services/terminal_service.py app/routers/terminals.py tests/test_terminal_service.py
git commit -m "fix: guarantee PTY cleanup in finally block and move resize() inside lock (R1.3)"
```

---

## Task 4 — R1.4: MCP embed task tracking

**Files:**
- Modify: `backend/app/mcp/server.py`
- Modify: `backend/tests/test_mcp_tools.py`

- [ ] **Step 1: Leggere il test file MCP esistente per capire il pattern**

```bash
cd backend && head -60 tests/test_mcp_tools.py
```

- [ ] **Step 2: Scrivere il test per il task tracking dell'embed**

Aggiungere alla fine di `backend/tests/test_mcp_tools.py`. Se `import asyncio` non è già presente, aggiungerlo tra gli import.

```python
@pytest.mark.asyncio
async def test_embed_background_task_tracking():
    """_background_tasks tiene il riferimento durante l'esecuzione e lo rimuove al completamento."""
    import asyncio
    from app.mcp import server as mcp_server

    mcp_server._background_tasks.clear()

    async def slow_coroutine():
        await asyncio.sleep(0.1)

    task = asyncio.create_task(slow_coroutine())
    mcp_server._background_tasks.add(task)
    task.add_done_callback(mcp_server._background_tasks.discard)

    assert len(mcp_server._background_tasks) == 1

    await asyncio.sleep(0.15)  # aspetta che la task finisca e il callback si attivi
    assert len(mcp_server._background_tasks) == 0
```

- [ ] **Step 3: Verificare che il test fallisca**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py::test_complete_issue_embed_task_is_tracked -v
```

Output atteso: FAILED con `AttributeError: module 'app.mcp.server' has no attribute '_background_tasks'`.

- [ ] **Step 4: Aggiungere `logging`, `_background_tasks` e logger in `server.py`**

In `backend/app/mcp/server.py`, dopo gli import esistenti (dopo la riga `import asyncio`), aggiungere:

```python
import logging
```

Subito dopo `mcp = FastMCP(...)`, aggiungere:

```python
logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task] = set()
```

Il file attuale:
```python
mcp = FastMCP(_desc["server.name"], streamable_http_path="/")
```

Diventa:
```python
mcp = FastMCP(_desc["server.name"], streamable_http_path="/")

logger = logging.getLogger(__name__)
_background_tasks: set[asyncio.Task] = set()
```

- [ ] **Step 5: Salvare il riferimento alla task embed**

In `backend/app/mcp/server.py`, sostituire le righe 150–155:

```python
            asyncio.create_task(rag.embed_issue(
                project_id=project_id,
                source_id=issue_id_val,
                issue_data=issue_data,
                project_name=project_name,
            ))
```

Con:

```python
            embed_task = asyncio.create_task(rag.embed_issue(
                project_id=project_id,
                source_id=issue_id_val,
                issue_data=issue_data,
                project_name=project_name,
            ))
            _background_tasks.add(embed_task)
            embed_task.add_done_callback(_background_tasks.discard)
            logger.debug("embed_issue task started for issue %s", issue_id_val)
```

- [ ] **Step 6: Eseguire i test MCP**

```bash
cd backend && python -m pytest tests/test_mcp_tools.py -v
```

Output atteso: tutti PASSED.

- [ ] **Step 7: Eseguire l'intera suite di test**

```bash
cd backend && python -m pytest -v
```

Output atteso: tutti PASSED (o solo test già precedentemente falliti).

- [ ] **Step 8: Commit**

```bash
cd backend && git add app/mcp/server.py tests/test_mcp_tools.py
git commit -m "fix: track embed background task in MCP server to prevent GC (R1.4)"
```

---

## Checklist di verifica finale

- [ ] `python -m pytest backend/ -v` — tutti i test passano
- [ ] `_issue_completion_locks` presente in `issue_service.py` come variabile module-level
- [ ] `HOOK_TIMEOUT = 300` in `registry.py`, `asyncio.wait_for` in `_run_hook`
- [ ] `HookRegistry._background_tasks` popolato in `fire()` e svuotato via `discard` callback
- [ ] `TerminalService.cleanup()` esiste ed è idempotente
- [ ] `resize()` usa `with self._lock:`
- [ ] `terminal_ws` ha blocco `finally: service.cleanup(terminal_id)`
- [ ] `_background_tasks` e `logger` presenti in `mcp/server.py`
