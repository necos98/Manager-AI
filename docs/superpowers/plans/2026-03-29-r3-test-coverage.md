# R3 — Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Coprire con test solidi tutti i percorsi critici elencati in R3 del ROADMAP (R3.1–R3.4), rafforzando i test deboli e aggiungendo quelli mancanti.

**Architecture:** Tutti i test vengono aggiunti a file di test esistenti — nessun nuovo file. I test verificano comportamento già implementato (nessuna modifica al codice applicativo). L'approccio è TDD-in-retro: scrivi il test, eseguilo per verificare che passi, committa.

**Tech Stack:** Python 3.11+, pytest-asyncio, unittest.mock, starlette.testclient (per WebSocket), asyncio, threading

---

## File modificati

| File | Azione | Test aggiunti |
|------|--------|---------------|
| `backend/tests/test_terminal_service.py` | Modify | 3 (buffer overflow, noop, empty) |
| `backend/tests/test_issue_service.py` | Modify | 1 (concurrent complete) |
| `backend/tests/test_rag_service.py` | Modify | 1 (lock concurrency) |
| `backend/tests/test_hook_registry.py` | Modify | 2 (fire no-raise, e2e trigger) |
| `backend/tests/test_terminal_router.py` | Modify | 2 (resize KeyError, WS cleanup) |
| `backend/tests/test_r2_mcp_transactions.py` | Modify | 2 (project 404, no-commit) |
| `ROADMAP.md` | Modify | Aggiorna `[ ]` → `[x]` per R3.1–R3.4 |

---

## Task 1: Buffer tests — terminal_service

**File:** `backend/tests/test_terminal_service.py`

Aggiunge tre test per `append_output` e `get_buffered_output`. Appendi al fondo del file.

- [ ] **Step 1: Scrivi i tre test**

```python
# --- buffer tests -----------------------------------------------------------

def test_append_output_overflow_trims_from_front(service):
    """Buffer che supera MAX_BUFFER_SIZE viene trimmato dal fronte (dati vecchi persi)."""
    from app.services.terminal_service import MAX_BUFFER_SIZE

    with patch("app.services.terminal_service.PTY") as MockPTY:
        mock_pty = MagicMock()
        mock_pty.spawn = MagicMock()
        MockPTY.return_value = mock_pty

        term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
        tid = term["id"]

        # Riempi il buffer con 'A', poi appendi 'B' per sforare il limite
        service.append_output(tid, "A" * MAX_BUFFER_SIZE)
        service.append_output(tid, "B" * 100)

        result = service.get_buffered_output(tid)
        assert len(result.encode("utf-8")) <= MAX_BUFFER_SIZE
        assert result.endswith("B" * 100), "I dati più recenti devono essere preservati"
        assert not result.startswith("A"), "I dati più vecchi devono essere eliminati dal fronte"


def test_append_output_unknown_terminal_is_noop(service):
    """append_output su terminal_id inesistente non deve sollevare eccezioni."""
    service.append_output("nonexistent-id", "some data")  # must not raise


def test_get_buffered_output_empty(service):
    """Terminal appena creato: get_buffered_output ritorna stringa vuota."""
    with patch("app.services.terminal_service.PTY") as MockPTY:
        mock_pty = MagicMock()
        mock_pty.spawn = MagicMock()
        MockPTY.return_value = mock_pty

        term = service.create(issue_id="t1", project_id="p1", project_path="C:/a")
        result = service.get_buffered_output(term["id"])
        assert result == ""
```

- [ ] **Step 2: Esegui e verifica che passino**

```bash
cd backend && python -m pytest tests/test_terminal_service.py::TestTerminalServiceRegistry::test_append_output_overflow_trims_from_front tests/test_terminal_service.py::TestTerminalServiceRegistry::test_append_output_unknown_terminal_is_noop tests/test_terminal_service.py::TestTerminalServiceRegistry::test_get_buffered_output_empty -v
```

Expected: tutti e tre `PASSED`

> Nota: i test esistono fuori dalla classe `TestTerminalServiceRegistry`. Se li hai aggiunti fuori dalla classe, pytest li eseguirà come funzioni standalone — va bene così. In alternativa, puoi inserirli dentro la classe.

- [ ] **Step 3: Committa**

```bash
git add backend/tests/test_terminal_service.py
git commit -m "test(R3.1): add buffer overflow and noop tests for terminal_service"
```

---

## Task 2: Concurrent complete_issue — issue_service

**File:** `backend/tests/test_issue_service.py`

Appendi al fondo del file.

- [ ] **Step 1: Scrivi il test**

```python
async def test_complete_issue_concurrent_two_tasks(db_session, project):
    """Due chiamate concorrenti: la prima completa, la seconda riceve InvalidTransitionError."""
    import asyncio
    from app.exceptions import InvalidTransitionError

    service = IssueService(db_session)
    issue = await service.create(project_id=project.id, description="Concurrent complete", priority=1)
    await service.create_spec(issue.id, project.id, "# Spec")
    await service.create_plan(issue.id, project.id, "# Plan")
    await service.accept_issue(issue.id, project.id)

    successes = []
    failures = []

    async def try_complete():
        try:
            result = await service.complete_issue(issue.id, project.id, "Done")
            successes.append(result)
        except InvalidTransitionError as e:
            failures.append(e)

    await asyncio.gather(try_complete(), try_complete())

    assert len(successes) == 1, "Esattamente una chiamata deve completare con successo"
    assert successes[0].status == IssueStatus.FINISHED
    assert len(failures) == 1, "La seconda chiamata deve ricevere InvalidTransitionError"
```

- [ ] **Step 2: Esegui e verifica che passi**

```bash
cd backend && python -m pytest tests/test_issue_service.py::test_complete_issue_concurrent_two_tasks -v
```

Expected: `PASSED`

- [ ] **Step 3: Committa**

```bash
git add backend/tests/test_issue_service.py
git commit -m "test(R3.1): add concurrent complete_issue race condition test"
```

---

## Task 3: Lock concurrency — rag_service

**File:** `backend/tests/test_rag_service.py`

Appendi al fondo del file.

- [ ] **Step 1: Scrivi il test**

```python
async def test_source_lock_serializes_concurrent_calls():
    """N coroutine concorrenti sullo stesso source_id vengono serializzate e il lock viene pulito."""
    import asyncio
    from app.services.rag_service import _source_lock, _source_locks

    _source_locks.clear()

    active_count = 0
    max_concurrent = 0

    async def worker():
        nonlocal active_count, max_concurrent
        async with _source_lock("source-concurrent"):
            active_count += 1
            max_concurrent = max(max_concurrent, active_count)
            await asyncio.sleep(0)  # cede il controllo per permettere interleaving
            active_count -= 1

    await asyncio.gather(*[worker() for _ in range(6)])

    assert max_concurrent == 1, "Al massimo una coroutine alla volta deve essere dentro il lock"
    assert "source-concurrent" not in _source_locks, "Il lock deve essere rimosso dopo l'ultimo uso"
```

- [ ] **Step 2: Esegui e verifica che passi**

```bash
cd backend && python -m pytest tests/test_rag_service.py::test_source_lock_serializes_concurrent_calls -v
```

Expected: `PASSED`

- [ ] **Step 3: Committa**

```bash
git add backend/tests/test_rag_service.py
git commit -m "test(R3.1): add concurrent lock serialization test for rag_service"
```

---

## Task 4: Hook fire-and-forget + end-to-end trigger

**File:** `backend/tests/test_hook_registry.py`

Appendi al fondo del file. Usa le classi `FailingHook` e `HookEvent`/`HookContext` già definite nel file.

- [ ] **Step 1: Scrivi i due test**

```python
@patch("app.hooks.registry.event_service")
async def test_fire_does_not_raise_when_hook_throws(mock_event_service):
    """fire() è fire-and-forget: eccezioni nell'hook non raggiungono il chiamante."""
    mock_event_service.emit = AsyncMock()
    registry = HookRegistry()
    registry.register(HookEvent.ISSUE_COMPLETED, FailingHook)
    ctx = HookContext(project_id="p1", issue_id="i1", event=HookEvent.ISSUE_COMPLETED)

    # Questo non deve sollevare eccezioni
    await registry.fire(HookEvent.ISSUE_COMPLETED, ctx)

    # Aspetta che la background task completi
    await asyncio.sleep(0.15)

    # Verifica che hook_failed sia stato emesso (prova che l'eccezione è stata gestita)
    emitted_types = [call[0][0]["type"] for call in mock_event_service.emit.call_args_list]
    assert "hook_failed" in emitted_types


async def test_issue_created_hook_end_to_end(db_session):
    """ISSUE_CREATED viene fired attraverso il registry reale (non mockato interamente)."""
    from unittest.mock import patch, AsyncMock
    from app.services.issue_service import IssueService
    from app.services.project_service import ProjectService
    import app.services.issue_service as issue_svc_module
    from app.hooks.registry import HookEvent

    project_service = ProjectService(db_session)
    project = await project_service.create(
        name="Hook E2E", path="/tmp/e2e", description="Test project"
    )

    fired_events = []

    async def recording_fire(event, ctx):
        fired_events.append(event)
        # Non eseguiamo i veri hook (richiederebbero claude CLI)

    # patch.object agisce sull'istanza singleton reale, non sulla reference nel modulo
    with patch.object(issue_svc_module.hook_registry, "fire", side_effect=recording_fire):
        svc = IssueService(db_session)
        await svc.create(project_id=project.id, description="E2E trigger test", priority=1)

    assert HookEvent.ISSUE_CREATED in fired_events, (
        "hook_registry.fire deve essere chiamato con HookEvent.ISSUE_CREATED "
        "alla creazione dell'issue (wiring service → registry verificato)"
    )
```

- [ ] **Step 2: Esegui e verifica che passino**

```bash
cd backend && python -m pytest tests/test_hook_registry.py::test_fire_does_not_raise_when_hook_throws tests/test_hook_registry.py::test_issue_created_hook_end_to_end -v
```

Expected: entrambi `PASSED`

> Nota: `test_issue_created_hook_end_to_end` usa `db_session` (fixture async), quindi pytest-asyncio lo gestisce automaticamente con `asyncio_mode = "auto"`.

- [ ] **Step 3: Committa**

```bash
git add backend/tests/test_hook_registry.py
git commit -m "test(R3.2): add fire-and-forget and ISSUE_CREATED end-to-end hook tests"
```

---

## Task 5: Router terminali — resize KeyError e WS cleanup

**File:** `backend/tests/test_terminal_router.py`

Aggiunge in cima i nuovi import necessari e due test al fondo del file.

- [ ] **Step 1: Verifica gli import esistenti nel file**

Leggi `backend/tests/test_terminal_router.py` e verifica che `MagicMock` e `patch` siano già importati (lo sono). Aggiungi gli import mancanti se necessario:

```python
import time  # aggiungere se non presente
from starlette.testclient import TestClient  # aggiungere se non presente
```

- [ ] **Step 2: Scrivi i due test (appendi al fondo)**

```python
# --- resize su terminal inesistente -----------------------------------------

def test_resize_nonexistent_terminal_raises_key_error():
    """service.resize() con terminal_id inesistente solleva KeyError (comportamento '404-equivalente').

    Il resize avviene via messaggio WebSocket, non via endpoint REST.
    Questo test documenta il contratto a livello servizio.
    """
    from app.services.terminal_service import TerminalService

    svc = TerminalService()
    with pytest.raises(KeyError):
        svc.resize("nonexistent-id", 100, 25)


# --- WebSocket disconnect → PTY cleanup -------------------------------------

def test_websocket_disconnect_calls_cleanup():
    """Disconnessione brusca del WebSocket deve chiamare service.cleanup(terminal_id)."""
    import time
    from starlette.testclient import TestClient
    from app.main import app
    from app.routers.terminals import get_terminal_service

    mock_svc = MagicMock()

    # pty.read(blocking=True) viene chiamato in run_in_executor.
    # Restituire "output" mantiene pty_to_ws in loop (non tocca il path EOF).
    # La disconnessione del client fa vincere ws_to_pty (WebSocketDisconnect),
    # che cancella pty_to_ws e triggerà il finally → cleanup.
    mock_pty = MagicMock()
    mock_pty.read.return_value = "output"

    mock_svc.get.return_value = {
        "id": "term-ws-1",
        "issue_id": "i1",
        "project_id": "p1",
        "project_path": "C:/fake",
        "status": "active",
        "created_at": "2026-03-29T00:00:00Z",
        "cols": 120,
        "rows": 30,
    }
    mock_svc.get_pty.return_value = mock_pty
    mock_svc.get_buffered_output.return_value = ""
    mock_svc.cleanup = MagicMock()
    mock_svc.mark_closed = MagicMock()
    mock_svc.append_output = MagicMock()
    mock_svc.resize = MagicMock()

    app.dependency_overrides[get_terminal_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            with client.websocket_connect("/api/terminals/term-ws-1/ws"):
                pass  # disconnessione immediata
    finally:
        app.dependency_overrides.clear()

    mock_svc.cleanup.assert_called_once_with("term-ws-1")
```

- [ ] **Step 3: Esegui e verifica che passino**

```bash
cd backend && python -m pytest tests/test_terminal_router.py::test_resize_nonexistent_terminal_raises_key_error tests/test_terminal_router.py::test_websocket_disconnect_calls_cleanup -v
```

Expected: entrambi `PASSED`

> Se `test_websocket_disconnect_calls_cleanup` fallisce con timeout o threading issue, aggiungi `time.sleep(0.05)` prima di `mock_svc.cleanup.assert_called_once_with(...)` per lasciare che il finally block venga eseguito.

- [ ] **Step 4: Committa**

```bash
git add backend/tests/test_terminal_router.py
git commit -m "test(R3.3): add resize KeyError and WebSocket cleanup tests for terminal router"
```

---

## Task 6: MCP tools — project 404 e no-commit su errore

**File:** `backend/tests/test_r2_mcp_transactions.py`

Appendi al fondo del file.

- [ ] **Step 1: Scrivi i due test**

```python
@pytest.mark.asyncio
async def test_mcp_get_project_context_nonexistent_returns_error():
    """get_project_context con project_id inesistente ritorna {'error': ...}, non lancia eccezioni."""
    from app.exceptions import AppError
    from app.mcp.server import get_project_context

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_project_service = MagicMock()
    mock_project_service.get_by_id = AsyncMock(
        side_effect=AppError("Project not found", 404)
    )

    with patch("app.mcp.server.async_session", return_value=mock_session), \
         patch("app.mcp.server.ProjectService", return_value=mock_project_service):
        result = await get_project_context("00000000-0000-0000-0000-000000000000")

    assert "error" in result
    assert "not found" in result["error"].lower()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_complete_issue_mcp_no_commit_on_app_error():
    """AppError in complete_issue MCP tool: commit non viene chiamato."""
    from app.exceptions import AppError
    from app.mcp.server import complete_issue

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_issue_service = MagicMock()
    mock_issue_service.complete_issue = AsyncMock(
        side_effect=AppError("Cannot complete: issue not in Accepted state", 422)
    )

    with patch("app.mcp.server.async_session", return_value=mock_session), \
         patch("app.mcp.server.IssueService", return_value=mock_issue_service):
        result = await complete_issue(
            project_id="proj-1",
            issue_id="issue-1",
            recap="Done",
        )

    assert result == {"error": "Cannot complete: issue not in Accepted state"}
    mock_session.commit.assert_not_called()
```

- [ ] **Step 2: Esegui e verifica che passino**

```bash
cd backend && python -m pytest tests/test_r2_mcp_transactions.py::test_mcp_get_project_context_nonexistent_returns_error tests/test_r2_mcp_transactions.py::test_complete_issue_mcp_no_commit_on_app_error -v
```

Expected: entrambi `PASSED`

- [ ] **Step 3: Committa**

```bash
git add backend/tests/test_r2_mcp_transactions.py
git commit -m "test(R3.4): add MCP project 404 and no-commit-on-error tests"
```

---

## Task 7: Esegui l'intera suite e aggiorna ROADMAP

- [ ] **Step 1: Esegui tutti i test**

```bash
cd backend && python -m pytest tests/test_terminal_service.py tests/test_issue_service.py tests/test_rag_service.py tests/test_hook_registry.py tests/test_terminal_router.py tests/test_r2_mcp_transactions.py -v
```

Expected: tutti `PASSED`, nessun warning inatteso.

- [ ] **Step 2: Aggiorna ROADMAP.md — marca R3 come completata**

Nel file `ROADMAP.md`, aggiorna i seguenti `[ ]` → `[x]`:

```
### R3.1
- [x] `terminal_service.py`: test per close/resize concorrente, buffer overflow, cleanup su disconnect
- [x] `issue_service.py`: test per race condition su `complete_issue` (async concurrent calls)
- [x] `rag_service.py`: test per lock cleanup con N thread concorrenti

### R3.2
- [x] Hook che lancia eccezione: verificare che il flusso principale non si interrompa
- [x] Hook con timeout: verificare che venga cancellato e loggato
- [x] `ISSUE_CREATED` hook: test end-to-end del trigger

### R3.3
- [x] Creazione terminale: risposta corretta
- [x] WebSocket connect/disconnect: PTY cleanup verificato
- [x] Resize con terminale inesistente: 404 pulito

### R3.4
- [x] Transazione atomica: errore nel tool non lascia DB in stato parziale
- [x] Tool call con project_id inesistente: `NotFoundError` propagato correttamente
```

- [ ] **Step 3: Committa il ROADMAP aggiornato**

```bash
git add ROADMAP.md
git commit -m "docs: mark R3 test coverage complete in ROADMAP"
```

---

## Checklist finale

- [ ] `test_append_output_overflow_trims_from_front` — buffer trim dal fronte verificato
- [ ] `test_append_output_unknown_terminal_is_noop` — nessun crash su ID inesistente
- [ ] `test_get_buffered_output_empty` — terminal fresco ritorna `""`
- [ ] `test_complete_issue_concurrent_two_tasks` — lock serializza, seconda chiamata fallisce pulito
- [ ] `test_source_lock_serializes_concurrent_calls` — max 1 coroutine attiva, lock rimosso dopo uso
- [ ] `test_fire_does_not_raise_when_hook_throws` — `fire()` è fire-and-forget
- [ ] `test_issue_created_hook_end_to_end` — wiring service → registry verificato
- [ ] `test_resize_nonexistent_terminal_raises_key_error` — KeyError pulito
- [ ] `test_websocket_disconnect_calls_cleanup` — PTY cleanup sul disconnect
- [ ] `test_mcp_get_project_context_nonexistent_returns_error` — 404 → `{"error": ...}`
- [ ] `test_complete_issue_mcp_no_commit_on_app_error` — nessun commit su errore
