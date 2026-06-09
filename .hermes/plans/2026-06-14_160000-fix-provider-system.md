# Fix Provider System — Implementation Plan

> **For Hermes:** Execute tasks sequentially. Each task has its own TDD cycle.

**Goal:** Far sì che la selezione del provider (`agent_provider` setting) venga rispettata in tutti i flussi: pipeline auto-mode, pipeline orchestrata, e Ask/Manage terminals (già funzionanti).

**Architecture:** Il provider è un **setting globale** (`agent_provider` in `default_settings.json`, default `"claude"`), non un attributo per-agent. I due moduli pipeline (`_execution.py`, `_orchestrated.py`) hardcodano `"claude"` invece di leggere il setting. Il fix è leggere `SettingsService.get("agent_provider")` in entrambi.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, pytest

---

## Task 1: Fix `_execution.py` — Leggere provider dal setting in auto-mode

**Objective:** Sostituire l'hardcoded `provider_name = "claude"` in `execute()` con la lettura dal `SettingsService`.

**Files:**
- Modify: `backend/app/services/pipeline_run/_execution.py:57`
- Test: `backend/tests/test_pipeline_integration.py` (aggiungere test)

**Context:** `execute()` riceve `session: AsyncSession` (line 33). Subito dopo (line 37-39) decide se usare quella o crearne una via `session_factory()`. Il setting va letto DOPO aver stabilito `exec_session`, appena prima del loop.

Il codice attuale:
```python
# riga 57 - dentro execute()
try:
    provider_name = "claude"  # ← HARDCODED
    success = await _run_step(
```

**Step 1: Aggiungi import**

Aggiungere in cima al file:
```python
from app.services.settings_service import SettingsService
```

**Step 2: Leggi il setting**

Sostituire `provider_name = "claude"` con:
```python
try:
    provider_name = await SettingsService(exec_session).get("agent_provider")
except (KeyError, Exception):
    provider_name = "claude"
    logger.warning("agent_provider setting not found, falling back to 'claude'")
```

Posizionarlo PRIMA del `try` che contiene il loop while (riga 56), in modo da leggerlo una volta sola per l'intera esecuzione.

**Step 3: Scrivi test**

```python
@pytest.mark.asyncio
async def test_auto_mode_pipeline_reads_provider_from_settings(db_session, monkeypatch):
    """Auto-mode reads agent_provider from SettingsService."""
    from app.services.settings_service import SettingsService
    from app.services.pipeline_run._execution import _run_step
    from app.providers.hermes_provider import HermesProvider
    from app.providers.registry import AgentProviderRegistry

    # 1. Set the setting to "hermes"
    await SettingsService(db_session).set("agent_provider", "hermes")
    await db_session.commit()

    # 2. Create pipeline with agent (no provider field — using default)
    agents = await create_agents(db_session, ["TestAgent"])
    pipeline, steps = await create_pipeline(db_session, agents, [("TestAgent", 0)])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)

    # 3. Mock AgentProviderRegistry.get + terminal
    called_with = []
    def _tracking_get(name: str):
        called_with.append(name)
        return HermesProvider()
    monkeypatch.setattr(AgentProviderRegistry, "get", _tracking_get)
    monkeypatch.setattr(
        "app.services.pipeline_run._execution.terminal_service.get_pty",
        lambda _tid: FakePTY(),
    )
    monkeypatch.setattr(
        "app.services.terminal_session._ensure_reader",
        lambda _tid, _svc: None,
    )
    mock_event = asyncio.Event()
    mock_event.set()
    monkeypatch.setattr(
        "app.services.pipeline_run._execution._completion.register_completion_event",
        lambda _rid, _idx: mock_event,
    )

    # 4. Call _run_step (provider_name will be resolved from test)
    try:
        await _run_step(
            term_id="test-term",
            agent_name="TestAgent",
            intent="Role: TestAgent",
            issue_id=issue.id,
            run_id=run.id,
            step_index=0,
        )
    except Exception:
        pass

    # 5. Verify AgentProviderRegistry.get was called with "hermes"
    assert "hermes" in called_with, (
        f"Expected 'hermes' in {called_with}"
    )
```

**Step 4: Esegui test**

```bash
cd backend
python -m pytest tests/test_pipeline_integration.py::test_auto_mode_pipeline_reads_provider_from_settings -v
```

Expected: PASS

**Step 5: Esegui test esistenti per verificare che non si rompa nulla**

```bash
cd backend
python -m pytest tests/test_pipeline_integration.py -v
python -m pytest tests/test_agent_providers.py -v
```

Expected: tutti PASS (alcuni potrebbero fallire, vedi Task 3)

---

## Task 2: Fix `_orchestrated.py` — Leggere provider dal setting in modalità orchestrata

**Objective:** Sostituire l'hardcoded `provider_name = "claude"` in `start_step()` con la lettura dal `SettingsService`.

**Files:**
- Modify: `backend/app/services/pipeline_run/_orchestrated.py:84`
- Test: `backend/tests/test_pipeline_integration.py` (aggiungere test)

**Context:** `start_step()` riceve `session: AsyncSession` (line 32). Ha già fatto operazioni sul DB prima della riga 84. Il setting va letto subito prima di usarlo.

**Step 1: Aggiungi import**

```python
from app.services.settings_service import SettingsService
```

**Step 2: Leggi il setting**

Sostituire `provider_name = "claude"` (riga 84) con:
```python
try:
    provider_name = await SettingsService(session).get("agent_provider")
except (KeyError, Exception):
    provider_name = "claude"
    logger.warning("agent_provider setting not found, falling back to 'claude'")
```

Posizionarlo DOPO `await _safe_session.safe_commit(session)` (riga 80) e PRIMA di `agent = step.agent` (riga 82). Questo perché la lettura del setting non richiede una sessione pulita — la sessione è attiva e non c'è race condition.

**Step 3: Scrivi test**

```python
@pytest.mark.asyncio
async def test_orchestrated_mode_reads_provider_from_settings(db_session, monkeypatch):
    """Orchestrated start_step reads agent_provider from SettingsService."""
    from app.services.settings_service import SettingsService
    from app.services.pipeline_run._orchestrated import start_step
    from app.providers.hermes_provider import HermesProvider
    from app.providers.registry import AgentProviderRegistry

    # 1. Set the setting to "hermes"
    await SettingsService(db_session).set("agent_provider", "hermes")
    await db_session.commit()

    # 2. Create pipeline + run in WAITING_FOR_STEP
    agents = await create_agents(db_session, ["OrchAgent"])
    pipeline, steps = await create_pipeline(db_session, agents, [("OrchAgent", 0)])
    project, issue = await create_project_and_issue(db_session)
    run, step_runs = await create_run(db_session, pipeline, issue, orchestrated=True)

    # Set status to WAITING_FOR_STEP
    run.status = PipelineRunStatus.WAITING_FOR_STEP
    await db_session.commit()

    # 3. Mock AgentProviderRegistry.get + terminal
    called_with = []
    def _tracking_get(name: str):
        called_with.append(name)
        return HermesProvider()
    monkeypatch.setattr(AgentProviderRegistry, "get", _tracking_get)
    monkeypatch.setattr(
        "app.services.pipeline_run._orchestrated.terminal_service.get_pty",
        lambda _tid: FakePTY(),
    )
    monkeypatch.setattr(
        "app.services.pipeline_run._orchestrated._completion.register_completion_event",
        lambda _rid, _idx: asyncio.Event(),
    )
    # Prevent background monitor from running
    monkeypatch.setattr(
        "app.services.pipeline_run._orchestrated.asyncio.create_task",
        lambda _coro: None,
    )

    # 4. Call start_step
    try:
        result = await start_step(
            run_id=run.id,
            project_id=project.id,
            project_path="/tmp/test",
            session=db_session,
        )
    except Exception:
        pass

    # 5. Verify AgentProviderRegistry.get was called with "hermes"
    assert "hermes" in called_with, (
        f"Expected 'hermes' in {called_with}"
    )
```

**Step 4: Esegui test**

```bash
cd backend
python -m pytest tests/test_pipeline_integration.py::test_orchestrated_mode_reads_provider_from_settings -v
```

Expected: PASS

---

## Task 3: Fix `pipeline_test_helpers.py` e test legacy — L'Agent model non ha `provider`

**Objective:** Ripulire il codice che ancora riferisce `step.agent.provider` nonostante il campo sia stato rimosso dalla migration `f9e8d7c6b5a4`.

**Files:**
- Modify: `backend/tests/pipeline_test_helpers.py:55`
- Modify: `backend/tests/test_pipeline_integration.py:537-621` (test `test_auto_mode_pipeline_uses_agent_provider`)
- Modify: (maybe) `backend/tests/test_pipeline_integration.py:560-565` references to `step.agent.provider`

**Step 1: Fix `create_agents()` in `pipeline_test_helpers.py`**

Rimuovere il parametro `provider` che non esiste più sul modello:

```python
async def create_agents(
    db_session: AsyncSession,
    names: list[str],
) -> dict[str, Agent]:
    """Create agents by name. Returns dict {name: Agent}."""
    agents = {}
    for n in names:
        a = Agent(name=n, intent=f"Role: {n}")
        db_session.add(a)
        agents[n] = a
    await db_session.flush()
    return agents
```

**Step 2: Riscrivi il test legacy `test_auto_mode_pipeline_uses_agent_provider`**

Questo test non può più testare `step.agent.provider` perché il campo non esiste. Va riscritto come test di integrazione che verifica che:
- Il setting `agent_provider` venga letto
- Il valore passato ad `AgentProviderRegistry.get()` corrisponda

**Step 2a:** Sostituisci l'intero test con una versione aggiornata:

```python
@pytest.mark.asyncio
async def test_auto_mode_pipeline_uses_agent_provider_setting(db_session, monkeypatch):
    """Auto-mode pipeline reads agent_provider from SettingsService."""
    from app.services.settings_service import SettingsService
    from app.services.pipeline_run._execution import _run_step
    from app.providers.hermes_provider import HermesProvider
    from app.providers.registry import AgentProviderRegistry

    # 1. Set setting to "hermes"
    await SettingsService(db_session).set("agent_provider", "hermes")
    await db_session.commit()

    # 2. Verify setting is readable
    assert await SettingsService(db_session).get("agent_provider") == "hermes"

    # 3. Create basic pipeline (no provider on agent)
    agents = await create_agents(db_session, ["TestAgent"])
    pipeline, steps = await create_pipeline(db_session, agents, [("TestAgent", 0)])
    project, issue = await create_project_and_issue(db_session)
    run, _step_runs = await create_run(db_session, pipeline, issue)

    # 4. Mock registry + terminal
    called_with = []
    def _tracking_get(name: str):
        called_with.append(name)
        return HermesProvider()
    monkeypatch.setattr(AgentProviderRegistry, "get", _tracking_get)
    monkeypatch.setattr(
        "app.services.pipeline_run._execution.terminal_service.get_pty",
        lambda _tid: FakePTY(),
    )
    monkeypatch.setattr(
        "app.services.terminal_session._ensure_reader",
        lambda _tid, _svc: None,
    )
    mock_event = asyncio.Event()
    mock_event.set()
    monkeypatch.setattr(
        "app.services.pipeline_run._execution._completion.register_completion_event",
        lambda _rid, _idx: mock_event,
    )

    # 5. Call _run_step — should read provider from setting
    try:
        await _run_step(
            term_id="test-term-legacy",
            agent_name="TestAgent",
            intent="Role: TestAgent",
            issue_id=issue.id,
            run_id=run.id,
            step_index=0,
        )
    except Exception:
        pass

    # 6. Assert "hermes" was used
    assert "hermes" in called_with, (
        f"AgentProviderRegistry.get should have been called with 'hermes', "
        f"got calls: {called_with}"
    )
```

**Step 3: Verifica che tutti i test passino**

```bash
cd backend
python -m pytest tests/test_pipeline_integration.py -v
python -m pytest tests/test_agent_providers.py -v
python -m pytest tests/ -x --timeout=30
```

Expected: Tutti PASS

---

## Task 4: Fix `_run_step()` default parameter in `_execution.py`

**Objective:** Cambiare il default del parametro `provider_name` da `"claude"` a `None` per forzare i chiamanti a passarlo esplicitamente (o gestire il fallback nel corpo della funzione).

**Files:**
- Modify: `backend/app/services/pipeline_run/_execution.py:297`

**Context:** La funzione `_run_step()` ha un default `provider_name: str = "claude"` (riga 297). Questo default non sarà più usato dopo Task 1, ma è una trappola per futuri chiamanti. Meglio renderlo esplicito.

**Step 1: Cambia la firma**

```python
async def _run_step(
    term_id: str,
    agent_name: str,
    intent: str,
    issue_id: str,
    run_id: str,
    step_index: int,
    provider_name: str | None = None,  # Must be resolved by caller
) -> bool:
```

**Step 2: Aggiungi fallback interno**

Dentro `_run_step()`, dopo la definizione:

```python
if provider_name is None:
    provider_name = "claude"
    logger.warning(
        "_run_step called without provider_name, falling back to 'claude'"
    )
```

**Step 3: Verifica test**

```bash
cd backend
python -m pytest tests/test_pipeline_integration.py -v
```

Expected: PASS

---

## Task 5: (Analisi) `build_run_issue_command()` — Dove dovrebbe essere chiamato?

**Objective:** Analizzare se il metodo `build_run_issue_command()` debba essere integrato nel flusso Run Issue, e dove.

**Files:**
- Read: `backend/app/mcp/shared_tools.py` — cerca funzioni che preparano terminali per issue
- Read: `backend/app/routers/terminals.py` — cerca eventuali endpoint `run-issue`
- Read: `backend/app/services/terminal_operations.py` — flusso `create_terminal()`

**Analisi:** Attualmente non esiste un endpoint "Run Issue" separato. Il bottone "Run Issue" nell'UI avvia una pipeline (tramite `PipelineRunButton` → `POST /api/pipeline-runs`). Il comando `/run-issue` è un comando built-in di Claude Code che Claude esegue DENTRO il proprio contesto quando è già spawnato. Il metodo `build_run_issue_command()` esiste nell'ABC per completezza ma non ha un punto di chiamata nel backend.

**Decisione:** Per ora NON wiring `build_run_issue_command()` — non c'è un flusso che lo richieda. Il flusso Run Issue passa attraverso il sistema pipeline, che dopo i Task 1-4 userà correttamente il provider selezionato. Il metodo rimane disponibile per futuri sviluppi (es. esecuzione diretta di una issue senza pipeline).

**Verifica:** Nessuna modifica al codice per questo task — solo documentazione.

---

## Riassunto ordine di esecuzione

| Ordine | Task | File principale | Modifica |
|---|---|---|---|
| 1 | Task 1 | `_execution.py:57` | Leggere `SettingsService.get("agent_provider")` invece di hardcodare `"claude"` |
| 2 | Task 2 | `_orchestrated.py:84` | Leggere `SettingsService.get("agent_provider")` invece di hardcodare `"claude"` |
| 3 | Task 3 | `pipeline_test_helpers.py` + test | Rimuovere riferimenti a `step.agent.provider` (campo rimosso) |
| 4 | Task 4 | `_execution.py:297` | Cambiare default di `provider_name` da `"claude"` a `None` |
| 5 | Task 5 | — | Analisi: `build_run_issue_command()` non ha ancora un punto di chiamata |

---

## Verifica finale

```bash
cd backend

# Agent provider unit tests
python -m pytest tests/test_agent_providers.py -v

# Pipeline integration tests (include i nuovi test per provider)
python -m pytest tests/test_pipeline_integration.py -v

# Full test suite
python -m pytest tests/ -x --timeout=60
```

Expected: Tutti i test PASS, nessuna regressione.
