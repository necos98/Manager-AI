# Pipeline Run Service — Refactoring Plan

> **Goal:** Trasformare `pipeline_run_service.py` (1211 righe) in un package modulare dove ogni responsabilità ha il proprio file, l'aggiunta di nuove feature è banale e il codice duplicato viene eliminato. La superficie pubblica (`PipelineRunService` + `set_step_completed`) rimane identica per tutti i chiamanti esterni.

---

## Stato Attuale — Analisi

### File attuale: `backend/app/services/pipeline_run_service.py` (1211 righe)

**Metodi pubblici** (chiamati da router/MPP — 15 metodi):
- `start()` — Avvia pipeline (auto-mode o orchestrated)
- `get_run()` — Dettaglio run
- `get_runs_for_issue()` — Lista run per issue
- `get_active_runs_for_issues()` — Run attive per lista issue ID
- `get_active_runs_for_project()` — Run attive per progetto
- `cancel_run()` — Cancella pipeline running
- `add_message()` — Aggiunge messaggio
- `get_messages()` — Lista messaggi
- `start_step()` — Orchestrated: avvia step
- `advance_step()` — Orchestrated: avanza al prossimo step
- `pause_run()` — Mette in pausa
- `resume_run()` — Riprende
- `reject_step()` — Rifiuta step e regredisce
- `resolve_rejection_target()` — Trova target event rules

**Metodi privati** (13 metodi interni):
- `_execute()`, `_wait_for_run()`, `_setup_step_environment()`, `_handle_step_completion()`, `_cleanup_step()`, `_finalize_run()`, `_safe_flush_session()`, `_safe_commit_session()`, `_run_step()`, `_get_run()`, `_get_run_with_session()`, `_monitor_step()`

**Modulo-level:**
- `set_step_completed()` — Segnala completamento step
- `_step_completion_events` — Dict globale di `asyncio.Event`

### Problemi identificati (4 categorie)

#### 1. DUPLICAZIONE RESPONSE BUILDING
Lo stesso pattern di conversione `step_run → dict` appare in **4 metodi** con minime variazioni:
- `get_run()` (righe 633-655)
- `get_runs_for_issue()` (righe 682-708)
- `get_active_runs_for_project()` (righe 755-780)
- `start()` (righe 88-106 — parziale, senza agent_intent)

#### 2. DUPLICAZIONE TERMINAL CLEANUP
Le stesse 4 operazioni (`_save_recording`, `_stop_reader`, `_sessions.pop`, `terminal_service.kill`) appaiono in **5 punti**:
- `_cleanup_step()` (righe 504-508)
- `cancel_run()` (righe 792-800)
- `pause_run()` (righe 1156-1170)
- `advance_step()` — cleanup finale (righe 1067-1079)
- `advance_step()` — cleanup intermedio (righe 1107-1119)

#### 3. DUE MODALITÀ ESECUTIVE MESCOLATE
Auto-mode (`_execute` + `_run_step` + `_wait_for_run`) e orchestrated-mode (`_monitor_step` + `start_step`) condividono la stessa classe ma hanno logiche completamente diverse. Questo rende difficile:
- Testare una modalità senza l'altra
- Aggiungere una terza modalità (es. supervisionata)
- Capire quali variabili globali servono a quale flusso

#### 4. LATE IMPORTS E AFFOLLAMENTO
- `from app.services.pipeline_service import PipelineService` dentro `resolve_rejection_target()`
- `from app.services.wsl_support import ...` dentro `_setup_step_environment()`
- `from app.services.terminal_session import ...` in `_run_step()` e `_monitor_step()`
- Gestione diretta di globali `_sessions`, `_stop_reader`, `_save_recording`

---

## Architettura Proposta

```
backend/app/services/pipeline_run/       # ← NUOVO PACKAGE
├── __init__.py                          # Re-export: PipelineRunService + set_step_completed
├── service.py                           # Facade: PipelineRunService (THIN ~80 righe)
├── _queries.py                          # DB read queries (get_run, get_runs_for_issue, ecc.)
├── _lifecycle.py                        # start, pause, resume, cancel, advance_step, _finalize_run
├── _execution.py                        # Auto-mode: _execute, _wait_for_run, _run_step
├── _orchestrated.py                     # Orchestrated: _monitor_step, start_step
├── _rejection.py                        # reject_step, resolve_rejection_target
├── _terminal.py                         # Terminal create + cleanup utility (elimina duplicati)
├── _responses.py                        # StepRun→dict, Run→dict builders (elimina duplicati)
├── _events.py                           # Event emission helpers
├── _messages.py                         # add_message, get_messages
├── _safe_session.py                     # _safe_flush, _safe_commit
└── _completion.py                       # set_step_completed + _step_completion_events (modulo)
```

Il file originale `pipeline_run_service.py` viene ELIMINATO.

Tutti i chiamanti esterni (`routers/pipeline_runs.py`, `mcp/shared_tools.py`) continuano a importare:
```python
from app.services.pipeline_run import PipelineRunService, set_step_completed
```

### Diagramma delle dipendenze

```
service.py (facade ~80 righe)
├── _queries.py        ─── dipende da: modelli, session
├── _lifecycle.py      ─── dipende da: _terminal, _events, _safe_session, _responses, _completion
├── _execution.py      ─── dipende da: _terminal, _events, _safe_session, _completion
├── _orchestrated.py   ─── dipende da: _terminal, _events, _safe_session, _completion
├── _rejection.py      ─── dipende da: _terminal, _events, _safe_session, _responses, _queries
├── _messages.py       ─── dipende da: modelli, session
├── _terminal.py       ─── dipende da: terminal_service, terminal_session globals
├── _responses.py      ─── dipende da: schemas, modelli (puramente funzionale)
├── _events.py         ─── dipende da: event_service
├── _safe_session.py   ─── dipende da: sqlalchemy, logging
└── _completion.py     ─── dipende da: asyncio (modulo-level, nessuna dipendenza interna)
```

**Regola:** Nessun modulo `_*.py` importa un altro modulo `_*.py` direttamente — passano solo attraverso la facade (`PipelineRunService`) o vengono passati come parametri. Questo elimina il rischio di dipendenze cicliche.

---

## Strategia di Migrazione

### Fase 1: Creare il package (no breaking changes)
Il file originale rimane intatto. Creiamo il nuovo package come migrazione graduale:
1. Creare `backend/app/services/pipeline_run/__init__.py` che re-exporta da `pipeline_run_service.py`
2. Verificare che `from app.services.pipeline_run import PipelineRunService` funzioni

### Fase 2: Estrarre moduli indipendenti
Moduli senza dipendenze dal service class vengono estratti per primi:
1. `_completion.py` — `set_step_completed()` + `_step_completion_events`
2. `_safe_session.py` — `_safe_flush_session()`, `_safe_commit_session()`
3. `_responses.py` — `step_run_to_dict()`, `run_to_dict()`, `active_run_to_dict()`
4. `_terminal.py` — `create_terminal_for_step()`, `cleanup_terminal()`, `cleanup_terminal_for_step_run()`
5. `_events.py` — `emit_step_started()`, `emit_step_completed()`, `emit_step_failed()`, ecc.
6. `_messages.py` — `add_message()`, `get_messages()`

### Fase 3: Estrarre moduli con logica di dominio
1. `_queries.py` — Tutti i metodi `get_*`
2. `_lifecycle.py` — `start()`, `pause_run()`, `resume_run()`, `cancel_run()`, `advance_step()`, `_finalize_run()`
3. `_execution.py` — `_execute()`, `_wait_for_run()`, `_run_step()`, `_handle_step_completion()`, `_setup_step_environment()`
4. `_orchestrated.py` — `start_step()`, `_monitor_step()`
5. `_rejection.py` — `reject_step()`, `resolve_rejection_target()`

### Fase 4: Creare la facade e testare
1. `service.py` — `PipelineRunService` che delega ai moduli interni
2. Aggiornare `__init__.py` per importare da `service.py`
3. Eseguire tutti i test esistenti

### Fase 5: Eliminare il file originale
1. Rimuovere `pipeline_run_service.py`
2. Eseguire tutti i test
3. Commit finale

---

## Specifica Dettagliata di Ogni Modulo

### `_completion.py` (modulo-level)

```python
"""Module-level step completion event signaling.

Orchestrates the interaction between the auto-mode _execute loop,
orchestrated-mode _monitor_step, and the MCP finished_pipeline_step tool.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

# Maps (run_id, step_index) -> asyncio.Event for step completion signaling
_completion_events: dict[tuple[str, int], asyncio.Event] = {}


def set_step_completed(run_id: str, step_index: int) -> bool:
    """Signal that a pipeline step has completed. Called by finished_pipeline_step MCP tool."""
    key = (run_id, step_index)
    event = _completion_events.get(key)
    if event is None:
        return False
    event.set()
    return True


def register_completion_event(run_id: str, step_index: int) -> asyncio.Event:
    """Create and register a completion event for a step."""
    event = asyncio.Event()
    _completion_events[(run_id, step_index)] = event
    return event


def unregister_completion_event(run_id: str, step_index: int) -> None:
    """Remove a completion event."""
    _completion_events.pop((run_id, step_index), None)
```

### `_safe_session.py`

```python
"""Safe database session helpers for the long-running pipeline background task."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def safe_flush(session: AsyncSession) -> None:
    """Flush with automatic rollback on failure."""
    try:
        await session.flush()
    except Exception:
        logger.warning("safe_flush: flush failed, rolling back", exc_info=True)
        await session.rollback()
        await session.flush()


async def safe_commit(session: AsyncSession) -> None:
    """Commit and release SQLite write lock.

    Called before/after pipeline steps so the long-running background
    task doesn't hold an open transaction that blocks MCP tool writes
    from the claude subprocess.
    """
    try:
        await session.commit()
    except Exception:
        logger.warning("safe_commit: commit failed, rolling back", exc_info=True)
        await session.rollback()
        await session.commit()
```

### `_responses.py`

```python
"""Response/serialization helpers for PipelineRun and PipelineStepRun objects.

ELIMINA LA DUPLICAZIONE: il pattern step_run → dict ora vive in un unico posto.
"""

from app.models.pipeline import PipelineStep
from app.models.pipeline_run import (
    PipelineRun,
    PipelineStepRun,
    PipelineStepRunStatus,
)


def step_run_to_dict(
    sr: PipelineStepRun,
    include_intent: bool = False,
) -> dict:
    """Convert a PipelineStepRun to a dictionary response.

    Questo è il builder centrale. Tutti i metodi get_* usano questo, non
    costruiscono dict manualmente.
    """
    agent_name = "unknown"
    agent_intent = ""
    if sr.pipeline_step and sr.pipeline_step.agent:
        agent_name = sr.pipeline_step.agent.name
        agent_intent = sr.pipeline_step.agent.intent or ""

    result = {
        "id": sr.id,
        "pipeline_run_id": sr.pipeline_run_id,
        "pipeline_step_id": sr.pipeline_step_id,
        "agent_name": agent_name,
        "status": sr.status.value,
        "terminal_id": sr.terminal_id,
        "started_at": sr.started_at.isoformat() if sr.started_at else None,
        "finished_at": sr.finished_at.isoformat() if sr.finished_at else None,
    }
    if include_intent:
        result["agent_intent"] = agent_intent
    return result


def run_to_dict(run: PipelineRun) -> dict:
    """Convert a PipelineRun + its step_runs to a dictionary response."""
    steps = []
    for sr in sorted(
        run.step_runs,
        key=lambda s: s.pipeline_step.order_index if s.pipeline_step else 0,
    ):
        steps.append(step_run_to_dict(sr, include_intent=True))

    return {
        "id": run.id,
        "pipeline_id": run.pipeline_id,
        "pipeline_name": run.pipeline.name if run.pipeline else "",
        "issue_id": run.issue_id,
        "status": run.status.value,
        "current_step_index": run.current_step_index,
        "steps": steps,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def active_run_to_dict(run: PipelineRun) -> dict:
    """Compact dict for active runs (no step sub-list)."""
    return {
        "pipeline_name": run.pipeline.name if run.pipeline else "",
        "status": run.status.value,
    }
```

### `_terminal.py`

```python
"""Terminal lifecycle management for pipeline steps.

ELIMINA LA DUPLICAZIONE: Le 4 operazioni di cleanup terminale ora vivono in un unico posto.
"""

from app.services.terminal_service import terminal_service
from app.services.terminal_session import _save_recording, _sessions, _stop_reader


def cleanup_terminal(term_id: str) -> None:
    """Save recording, stop reader, remove session, and kill PTY."""
    _save_recording(term_id, terminal_service.get_buffered_output(term_id))
    _stop_reader(term_id)
    _sessions.pop(term_id, None)
    terminal_service.kill(term_id)
```

### `_events.py`

```python
"""Pipeline-specific WebSocket event emissions."""

from app.services.event_service import event_service


async def emit_step_started(
    project_id: str,
    issue_id: str,
    agent_name: str,
    step_run_id: str,
    terminal_id: str,
) -> None:
    await event_service.emit({
        "type": "agent_step_started",
        "project_id": project_id,
        "issue_id": issue_id,
        "agent_name": agent_name,
        "step_run_id": step_run_id,
        "terminal_id": terminal_id,
    })


async def emit_terminal_created(
    terminal_id: str,
    issue_id: str,
    project_id: str,
) -> None:
    await event_service.emit({
        "type": "terminal_created",
        "terminal_id": terminal_id,
        "issue_id": issue_id,
        "project_id": project_id,
    })


async def emit_step_completed(
    project_id: str,
    issue_id: str,
    agent_name: str,
    step_run_id: str,
) -> None:
    await event_service.emit({
        "type": "agent_step_completed",
        "project_id": project_id,
        "issue_id": issue_id,
        "agent_name": agent_name,
        "step_run_id": step_run_id,
    })


async def emit_step_failed(
    project_id: str,
    issue_id: str,
    agent_name: str,
    step_run_id: str,
) -> None:
    await event_service.emit({
        "type": "agent_step_failed",
        "project_id": project_id,
        "issue_id": issue_id,
        "agent_name": agent_name,
        "step_run_id": step_run_id,
    })


async def emit_pipeline_completed(
    project_id: str,
    issue_id: str,
    run_id: str,
    status: str,
) -> None:
    await event_service.emit({
        "type": "pipeline_completed",
        "project_id": project_id,
        "issue_id": issue_id,
        "run_id": run_id,
        "status": status,
    })


async def emit_step_rejected(
    project_id: str,
    issue_id: str,
    run_id: str,
    step_run_id: str,
    agent_name: str,
    reason: str,
    target_step_index: int,
    rejection_count: int,
) -> None:
    await event_service.emit({
        "type": "pipeline_step_rejected",
        "project_id": project_id,
        "issue_id": issue_id,
        "run_id": run_id,
        "step_run_id": step_run_id,
        "agent_name": agent_name,
        "reason": reason,
        "target_step_index": target_step_index,
        "rejection_count": rejection_count,
    })


async def emit_step_advanced(
    run_id: str,
    issue_id: str,
    from_step: int,
    to_step: int,
) -> None:
    await event_service.emit({
        "type": "pipeline_step_advanced",
        "run_id": run_id,
        "issue_id": issue_id,
        "from_step": from_step,
        "to_step": to_step,
        "status": "WAITING_FOR_STEP",
    })


async def emit_pipeline_paused(
    run_id: str,
    issue_id: str,
) -> None:
    await event_service.emit({
        "type": "pipeline_paused",
        "run_id": run_id,
        "issue_id": issue_id,
    })


async def emit_pipeline_resumed(
    run_id: str,
    issue_id: str,
) -> None:
    await event_service.emit({
        "type": "pipeline_resumed",
        "run_id": run_id,
        "issue_id": issue_id,
    })
```

### `_queries.py`

```python
"""Database read queries for pipeline runs."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError
from app.models.issue import Issue
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import PipelineRun, PipelineRunStatus, PipelineStepRun
from app.services.pipeline_run._responses import active_run_to_dict, run_to_dict


# ── Loader utilities ──────────────────────────────────────────

_PIPELINE_LOAD = selectinload(PipelineRun.pipeline)
_STEP_RUNS_LOAD = selectinload(PipelineRun.step_runs).selectinload(
    PipelineStepRun.pipeline_step
).selectinload(PipelineStep.agent)
_FULL_RUN_LOAD = [_PIPELINE_LOAD, _STEP_RUNS_LOAD]


async def get_run_with_session(run_id: str, session: AsyncSession) -> PipelineRun:
    """Get a pipeline run with all eager-loaded relationships."""
    result = await session.execute(
        select(PipelineRun)
        .where(PipelineRun.id == run_id)
        .options(*_FULL_RUN_LOAD)
    )
    run = result.unique().scalar_one_or_none()
    if run is None:
        raise NotFoundError(f"Pipeline run not found: {run_id}")
    return run


# ── Public query methods ──────────────────────────────────────


async def get_run(run_id: str, session: AsyncSession) -> dict:
    """Get a single pipeline run with its step runs."""
    run = await get_run_with_session(run_id, session)
    return run_to_dict(run)


async def get_runs_for_issue(issue_id: str, session: AsyncSession) -> list[dict]:
    """Get all pipeline runs for an issue, ordered by creation date desc."""
    result = await session.execute(
        select(PipelineRun)
        .where(PipelineRun.issue_id == issue_id)
        .options(*_FULL_RUN_LOAD)
        .order_by(PipelineRun.created_at.desc())
    )
    runs = result.unique().scalars().all()
    return [run_to_dict(r) for r in runs]


async def get_active_runs_for_issues(
    issue_ids: list[str], session: AsyncSession
) -> dict[str, dict | None]:
    """Return active (RUNNING) pipeline runs for given issue ids."""
    result = await session.execute(
        select(PipelineRun)
        .where(
            PipelineRun.issue_id.in_(issue_ids),
            PipelineRun.status == PipelineRunStatus.RUNNING,
        )
        .options(_PIPELINE_LOAD)
    )
    runs = result.unique().scalars().all()
    run_by_issue: dict[str, dict | None] = {iid: None for iid in issue_ids}
    for r in runs:
        run_by_issue[r.issue_id] = active_run_to_dict(r)
    return run_by_issue


async def get_active_runs_for_project(
    project_id: str, session: AsyncSession
) -> list[dict]:
    """Return active (RUNNING) pipeline runs for a project via Issue JOIN."""
    result = await session.execute(
        select(PipelineRun)
        .join(Issue, PipelineRun.issue_id == Issue.id)
        .where(
            Issue.project_id == project_id,
            PipelineRun.status == PipelineRunStatus.RUNNING,
        )
        .options(*_FULL_RUN_LOAD)
        .order_by(PipelineRun.created_at.desc())
    )
    runs = result.unique().scalars().all()
    return [run_to_dict(r) for r in runs]
```

### `_lifecycle.py`

```python
"""Pipeline run lifecycle: start, pause, resume, cancel, advance_step, finalize."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.issue import Issue
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.services.pipeline_run import (
    _completion,
    _events,
    _queries,
    _responses,
    _safe_session,
    _terminal,
)
from app.services.pipeline_task_manager import pipeline_task_manager
from app.services.terminal_service import terminal_service
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def start(
    pipeline_id: str,
    issue_id: str,
    project_id: str,
    project_path: str,
    orchestrated: bool,
    session: AsyncSession,
    session_factory=None,
) -> dict:
    """Start a pipeline run. Returns run details with step runs."""
    # Guard: no concurrent runs
    existing = await session.execute(
        select(PipelineRun).where(
            PipelineRun.issue_id == issue_id,
            PipelineRun.status.in_([
                PipelineRunStatus.RUNNING,
                PipelineRunStatus.WAITING_FOR_STEP,
            ]),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValidationError(
            f"A pipeline is already running or waiting for step for issue {issue_id}"
        )

    # Load pipeline
    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
    )
    pipeline = pipeline.unique().scalar_one_or_none()
    if pipeline is None:
        raise NotFoundError(f"Pipeline not found: {pipeline_id}")

    # Create run
    run = PipelineRun(
        pipeline_id=pipeline_id,
        issue_id=issue_id,
        status=PipelineRunStatus.WAITING_FOR_STEP if orchestrated else PipelineRunStatus.RUNNING,
        current_step_index=0,
        orchestrated=orchestrated,
        started_at=now(),
    )
    session.add(run)
    await session.flush()

    # Create step runs
    step_responses = []
    for step in sorted(pipeline.steps, key=lambda s: s.order_index):
        step_run = PipelineStepRun(
            pipeline_run_id=run.id,
            pipeline_step_id=step.id,
            status=PipelineStepRunStatus.PENDING,
        )
        session.add(step_run)
        await session.flush()
        step_responses.append(_responses.step_run_to_dict(step_run))

    if orchestrated:
        await session.commit()
    else:
        task = asyncio.create_task(
            _execution.execute(run.id, project_id, project_path, session, session_factory)
        )
        await pipeline_task_manager.start_task(run.id, task)
        await session.commit()

    return {
        "id": run.id,
        "pipeline_id": run.pipeline_id,
        "pipeline_name": pipeline.name,
        "issue_id": run.issue_id,
        "status": run.status.value,
        "current_step_index": run.current_step_index,
        "steps": step_responses,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


async def pause_run(run_id: str, session: AsyncSession) -> dict:
    """Pause a pipeline run."""
    run = await _queries.get_run_with_session(run_id, session)

    if run.status not in (PipelineRunStatus.RUNNING, PipelineRunStatus.WAITING_FOR_STEP):
        raise ValidationError(
            f"Cannot pause: pipeline is {run.status.value}, "
            f"expected RUNNING or WAITING_FOR_STEP"
        )

    if run.status == PipelineRunStatus.RUNNING:
        step_idx = run.current_step_index
        for sr in run.step_runs:
            if sr.pipeline_step and sr.pipeline_step.order_index == step_idx and sr.terminal_id:
                _terminal.cleanup_terminal(sr.terminal_id)
                sr.status = PipelineStepRunStatus.FAILED
                sr.finished_at = now()
                break

        if not run.orchestrated:
            await pipeline_task_manager.cancel_task(run_id)
        else:
            _completion.set_step_completed(run_id, step_idx)

    run.status = PipelineRunStatus.PAUSED
    await _safe_session.safe_commit(session)
    await _events.emit_pipeline_paused(run_id, run.issue_id)
    return {"status": "PAUSED"}


async def resume_run(run_id: str, session: AsyncSession) -> dict:
    """Resume a paused pipeline."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status != PipelineRunStatus.PAUSED:
        raise ValidationError(
            f"Cannot resume: pipeline is {run.status.value}, "
            f"expected PAUSED"
        )
    run.status = PipelineRunStatus.WAITING_FOR_STEP
    await _safe_session.safe_commit(session)
    await _events.emit_pipeline_resumed(run_id, run.issue_id)
    return {"status": "WAITING_FOR_STEP"}


async def cancel_run(run_id: str, session: AsyncSession) -> bool:
    """Cancel a running pipeline and clean up all resources."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status != PipelineRunStatus.RUNNING:
        raise ValidationError(f"Can only cancel active pipelines (status: {run.status.value})")

    # Kill active terminal first
    for sr in run.step_runs:
        if sr.status == PipelineStepRunStatus.RUNNING and sr.terminal_id:
            _terminal.cleanup_terminal(sr.terminal_id)
            sr.status = PipelineStepRunStatus.FAILED
            sr.finished_at = now()
            break

    # Cancel background task
    await pipeline_task_manager.cancel_task(run_id)

    run.status = PipelineRunStatus.FAILED
    run.finished_at = now()
    await _safe_session.safe_flush(session)
    return True


async def advance_step(run_id: str, session: AsyncSession) -> dict:
    """Advance the pipeline to the next step (orchestrated mode)."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status not in (PipelineRunStatus.WAITING_FOR_STEP, PipelineRunStatus.RUNNING):
        raise ValidationError(
            f"Cannot advance: pipeline is {run.status.value}, "
            f"expected WAITING_FOR_STEP or RUNNING"
        )

    i = run.current_step_index
    current_completed = any(
        sr.pipeline_step and sr.pipeline_step.order_index == i
        and sr.status == PipelineStepRunStatus.COMPLETED
        for sr in run.step_runs
    )
    if not current_completed:
        raise ValidationError(f"Cannot advance: step {i} is not COMPLETED")

    total_steps = len(run.step_runs)
    if i + 1 >= total_steps:
        # Pipeline finished — cleanup final terminal
        _cleanup_current_terminal(run, i)
        run.status = PipelineRunStatus.COMPLETED
        run.finished_at = now()
        await _safe_session.safe_commit(session)

        issue = await session.get(Issue, run.issue_id)
        await _events.emit_pipeline_completed(
            project_id=issue.project_id if issue else "",
            issue_id=run.issue_id,
            run_id=run_id,
            status=PipelineRunStatus.COMPLETED.value,
        )
        return {"status": "COMPLETED", "next_step_index": None, "pipeline_finished": True}

    run.current_step_index = i + 1
    run.status = PipelineRunStatus.WAITING_FOR_STEP
    await _safe_session.safe_commit(session)

    # Defensive cleanup of previous step's terminal
    _cleanup_current_terminal(run, i)

    await _events.emit_step_advanced(run_id, run.issue_id, i, i + 1)
    return {"status": "WAITING_FOR_STEP", "next_step_index": i + 1, "pipeline_finished": False}


def _cleanup_current_terminal(run: PipelineRun, step_index: int) -> None:
    """Clean up terminal for a specific step, if present."""
    for sr in run.step_runs:
        if sr.pipeline_step and sr.pipeline_step.order_index == step_index and sr.terminal_id:
            _terminal.cleanup_terminal(sr.terminal_id)
            break
```

> **Nota:** `start()` chiama `_execution.execute()` — questo crea un import circolare a livello di modulo. La soluzione è **lazy import** dentro `start()` stessa, o spostare la logica di dispatch in un modulo separato. Nella sezione Rischi spiego come gestirlo.

### `_execution.py`

```python
"""Auto-mode: background execution loop for non-orchestrated pipelines."""

import asyncio
import logging
import shlex

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.models.project import Project
from app.providers.registry import AgentProviderRegistry
from app.services.pipeline_run import _completion, _events, _queries, _safe_session, _terminal
from app.services.pipeline_task_manager import pipeline_task_manager
from app.services.terminal_service import terminal_service
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def execute(
    run_id: str, project_id: str, project_path: str,
    session: AsyncSession, session_factory=None,
) -> None:
    """Main execution loop for auto-mode pipelines."""
    exec_session = session
    if session_factory is not None:
        exec_session = session_factory()

    try:
        run, steps = await _wait_for_run(run_id, exec_session)
        if run is None:
            return

        while run.current_step_index < len(steps) and run.status != PipelineRunStatus.FAILED:
            i = run.current_step_index
            step = steps[i]

            term_id, agent_name, step_run = await _setup_step_environment(
                step, run, exec_session, project_id, project_path, run_id,
            )
            if step_run is None:
                continue

            try:
                success = await _run_step(
                    term_id=term_id,
                    agent_name=agent_name,
                    intent=step.agent.intent if step.agent else "",
                    issue_id=run.issue_id,
                    run_id=run_id,
                    step_index=i,
                )

                await exec_session.refresh(run)
                await exec_session.refresh(step_run)

                if step_run.status == PipelineStepRunStatus.REJECTED:
                    step_run.finished_at = now()
                    await _safe_session.safe_commit(exec_session)
                    continue

                should_continue = await _handle_step_completion(
                    run, step_run, exec_session, success, agent_name,
                    project_id, run.issue_id,
                )
                if not should_continue:
                    break

                step_run.finished_at = now()
                await _safe_session.safe_commit(exec_session)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Step %s failed with exception", agent_name)
                step_run.status = PipelineStepRunStatus.FAILED
                run.status = PipelineRunStatus.FAILED
                step_run.finished_at = now()
                await _safe_session.safe_commit(exec_session)
                await _events.emit_step_failed(
                    project_id, run.issue_id, agent_name, step_run.id,
                )
                break
            finally:
                if term_id:
                    _terminal.cleanup_terminal(term_id)

        await _finalize_run(run, exec_session, project_id, run.issue_id, run_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Pipeline %s failed with unexpected error", run_id)
        try:
            run.status = PipelineRunStatus.FAILED
            run.finished_at = now()
            await _safe_session.safe_commit(exec_session)
        except Exception:
            pass
        await _events.emit_pipeline_completed(
            project_id, run.issue_id, run_id, PipelineRunStatus.FAILED.value,
        )
    finally:
        if session_factory is not None:
            try:
                await exec_session.close()
            except Exception:
                pass
        await pipeline_task_manager.cleanup_task(run_id)


async def _wait_for_run(
    run_id: str, session: AsyncSession,
) -> tuple[PipelineRun | None, list | None]:
    """Wait for the pipeline run to be committed by the caller."""
    run = None
    for _ in range(50):
        try:
            run = await _queries.get_run_with_session(run_id, session)
            break
        except NotFoundError:
            await asyncio.sleep(0.1)
    if run is None:
        logger.error("Pipeline run %s not found — execute started before commit finished", run_id)
        return None, None

    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == run.pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
    )
    pipeline = pipeline.unique().scalar_one_or_none()
    if pipeline is None:
        return None, None
    steps = sorted(pipeline.steps, key=lambda s: s.order_index)
    return run, steps


async def _setup_step_environment(
    step: PipelineStep,
    run: PipelineRun,
    session: AsyncSession,
    project_id: str,
    project_path: str,
    run_id: str,
) -> tuple[str | None, str | None, PipelineStepRun | None]:
    """Set up terminal and mark step run as RUNNING."""
    i = run.current_step_index

    step_run_result = await session.execute(
        select(PipelineStepRun).where(
            PipelineStepRun.pipeline_run_id == run_id,
            PipelineStepRun.pipeline_step_id == step.id,
        ).order_by(PipelineStepRun.started_at.desc().nulls_last())
    )
    step_run = step_run_result.scalars().first()
    if step_run is None:
        return None, None, None

    step_run.status = PipelineStepRunStatus.RUNNING
    step_run.started_at = now()
    run.current_step_index = i
    await _safe_session.safe_flush(session)

    agent = step.agent
    agent_name = agent.name if agent else "unknown"

    project_row = await session.get(Project, project_id)
    project_shell = project_row.shell if project_row else None
    project_wsl_distro = project_row.wsl_distro if project_row else None

    term = terminal_service.create(
        issue_id=run.issue_id,
        project_id=project_id,
        project_path=project_path,
        shell=project_shell,
        wsl_distro=project_wsl_distro,
    )
    term_id = term["id"]
    step_run.terminal_id = term_id
    await _safe_session.safe_commit(session)

    if project_shell:
        from app.services.wsl_support import is_wsl_shell, win_to_wsl_path
        if is_wsl_shell(project_shell):
            cwd_wsl = win_to_wsl_path(project_path)
            pty_for_cd = terminal_service.get_pty(term_id)
            pty_for_cd.write(f"cd {shlex.quote(cwd_wsl)}\r\n")

    await _events.emit_step_started(project_id, run.issue_id, agent_name, step_run.id, term_id)
    await _events.emit_terminal_created(term_id, run.issue_id, project_id)

    return term_id, agent_name, step_run


async def _handle_step_completion(
    run: PipelineRun,
    step_run: PipelineStepRun,
    session: AsyncSession,
    success: bool,
    agent_name: str,
    project_id: str,
    issue_id: str,
) -> bool:
    """Handle step completion result. Returns False if pipeline should stop."""
    if success:
        step_run.status = PipelineStepRunStatus.COMPLETED
        run.current_step_index += 1
        await _events.emit_step_completed(project_id, issue_id, agent_name, step_run.id)
        return True
    else:
        step_run.status = PipelineStepRunStatus.FAILED
        run.status = PipelineRunStatus.FAILED
        step_run.finished_at = now()
        await _safe_session.safe_commit(session)
        await _events.emit_step_failed(project_id, issue_id, agent_name, step_run.id)
        return False


async def _finalize_run(
    run: PipelineRun,
    session: AsyncSession,
    project_id: str,
    issue_id: str,
    run_id: str,
) -> None:
    """Finalize pipeline run: mark COMPLETED if not already FAILED."""
    await session.refresh(run)
    if run.status != PipelineRunStatus.FAILED:
        run.status = PipelineRunStatus.COMPLETED
    run.finished_at = now()
    await _safe_session.safe_commit(session)
    await _events.emit_pipeline_completed(project_id, issue_id, run_id, run.status.value)


async def _run_step(
    term_id: str,
    agent_name: str,
    intent: str,
    issue_id: str,
    run_id: str,
    step_index: int,
) -> bool:
    """Execute a single step via PTY and wait for completion."""
    import platform as _platform
    from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

    pty = terminal_service.get_pty(term_id)
    session = TerminalSession()
    _sessions[term_id] = session
    _ensure_reader(term_id, terminal_service)

    is_windows = _platform.system() == "Windows"
    provider = AgentProviderRegistry.get("claude")
    command = provider.build_run_pipeline_command(issue_id)

    pty.write(f"{command} {'&' if is_windows else ';'} exit\r\n")

    event = _completion.register_completion_event(run_id, step_index)
    async def wait_pty_death():
        await session.pty_dead.wait()

    pty_task = asyncio.create_task(wait_pty_death())
    event_task = asyncio.create_task(event.wait())

    try:
        done, pending = await asyncio.wait(
            [pty_task, event_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        success = event_task in done
        if pty_task in done and event_task not in done:
            logger.error("Step %s failed: PTY died before finished_pipeline_step called", agent_name)
            success = False

        for t in pending:
            t.cancel()
    finally:
        _completion.unregister_completion_event(run_id, step_index)

    return success
```

### `_orchestrated.py`

```python
"""Orchestrated mode: Hermes-controlled step execution."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.providers.registry import AgentProviderRegistry
from app.database import async_session
from app.services.pipeline_run import _completion, _events, _queries, _safe_session, _terminal
from app.services.terminal_service import terminal_service
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def start_step(
    run_id: str,
    project_id: str,
    project_path: str,
    session: AsyncSession,
) -> dict:
    """Spawn PTY terminal + Claude for the current pipeline step (orchestrated mode)."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status != PipelineRunStatus.WAITING_FOR_STEP:
        raise ValidationError(
            f"Cannot start step: pipeline is {run.status.value}, "
            f"expected WAITING_FOR_STEP"
        )

    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == run.pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
    )
    pipeline = pipeline.unique().scalar_one_or_none()
    if pipeline is None:
        raise NotFoundError(f"Pipeline not found: {run.pipeline_id}")

    steps = sorted(pipeline.steps, key=lambda s: s.order_index)
    i = run.current_step_index
    if i >= len(steps):
        raise ValidationError(f"No more steps available (index {i} >= {len(steps)})")

    step = steps[i]
    step_run_result = await session.execute(
        select(PipelineStepRun).where(
            PipelineStepRun.pipeline_run_id == run_id,
            PipelineStepRun.pipeline_step_id == step.id,
        ).order_by(PipelineStepRun.started_at.desc().nulls_last())
    )
    step_run = step_run_result.scalars().first()
    if step_run is None:
        raise NotFoundError(f"StepRun not found for pipeline_step {step.id}")
    if step_run.status != PipelineStepRunStatus.PENDING:
        raise ValidationError(f"Step {i} is {step_run.status.value}, expected PENDING")

    # Create terminal
    term = terminal_service.create(
        issue_id=run.issue_id,
        project_id=project_id,
        project_path=project_path,
    )
    term_id = term["id"]
    step_run.terminal_id = term_id
    step_run.status = PipelineStepRunStatus.RUNNING
    step_run.started_at = now()
    run.status = PipelineRunStatus.RUNNING
    await _safe_session.safe_commit(session)

    agent = step.agent
    agent_name = agent.name if agent else "unknown"
    provider_name = getattr(agent, "provider", "claude") if agent else "claude"

    pty = terminal_service.get_pty(term_id)
    try:
        provider = AgentProviderRegistry.get(provider_name)
        command = provider.build_run_pipeline_command(run.issue_id)
    except KeyError:
        logger.warning("Unknown provider %r for agent %r, falling back to claude", provider_name, agent_name)
        provider = AgentProviderRegistry.get("claude")
        command = provider.build_run_pipeline_command(run.issue_id)
    pty.write(command + "\r\n")

    _completion.register_completion_event(run_id, i)
    asyncio.create_task(monitor_step(run_id=run_id, step_index=i, term_id=term_id))

    await _events.emit_step_started(project_id, run.issue_id, agent_name, step_run.id, term_id)

    return {
        "term_id": term_id,
        "agent_name": agent_name,
        "agent_intent": step.agent.intent if step.agent else "",
        "step_index": i,
        "step_run_id": step_run.id,
    }


async def monitor_step(
    run_id: str,
    step_index: int,
    term_id: str,
) -> None:
    """Background task: wait for step completion or PTY death (orchestrated mode).

    Cleans up the terminal when done.
    """
    from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader

    term_session = TerminalSession()
    _sessions[term_id] = term_session
    _ensure_reader(term_id, terminal_service)

    event = _completion._completion_events.get((run_id, step_index))
    if event is None:
        logger.warning("monitor_step: no completion event for (%s, %d)", run_id, step_index)
        return

    async def wait_pty_death():
        await term_session.pty_dead.wait()

    pty_task = asyncio.create_task(wait_pty_death())
    event_task = asyncio.create_task(event.wait())

    try:
        done, pending = await asyncio.wait(
            [pty_task, event_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()

        if pty_task in done and event_task not in done:
            # PTY died before step completed — mark as FAILED
            logger.error("Step %d of run %s: PTY died before finished_pipeline_step", step_index, run_id)
            async with async_session() as fresh_session:
                run = await _queries.get_run_with_session(run_id, fresh_session)
                if run.status == PipelineRunStatus.RUNNING:
                    run.status = PipelineRunStatus.FAILED
                    run.finished_at = now()
                    for sr in run.step_runs:
                        if sr.pipeline_step and sr.pipeline_step.order_index == step_index and sr.status == PipelineStepRunStatus.RUNNING:
                            sr.status = PipelineStepRunStatus.FAILED
                            sr.finished_at = now()
                            break
                    await fresh_session.commit()
        else:
            # Normal completion
            async with async_session() as fresh_session:
                run = await _queries.get_run_with_session(run_id, fresh_session)
                if run.status == PipelineRunStatus.RUNNING:
                    run.status = PipelineRunStatus.WAITING_FOR_STEP
                for sr in run.step_runs:
                    if sr.pipeline_step and sr.pipeline_step.order_index == step_index and sr.status == PipelineStepRunStatus.RUNNING:
                        sr.status = PipelineStepRunStatus.COMPLETED
                        sr.finished_at = now()
                        break
                await fresh_session.commit()
    finally:
        _completion.unregister_completion_event(run_id, step_index)
        _terminal.cleanup_terminal(term_id)
```

### `_rejection.py`

```python
"""Pipeline step rejection logic."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import NotFoundError, ValidationError
from app.models.pipeline import Pipeline, PipelineStep
from app.models.pipeline_run import (
    PipelineMessage,
    PipelineRun,
    PipelineRunStatus,
    PipelineStepRun,
    PipelineStepRunStatus,
)
from app.services.pipeline_run import _completion, _events, _queries, _safe_session
from app.utils.datetime import now

logger = logging.getLogger(__name__)


async def resolve_rejection_target(
    run_id: str, step_id: str, session: AsyncSession,
) -> int | None:
    """Check event rules for rejection redirect. Returns target order_index or None."""
    from app.services.pipeline_service import PipelineService

    run = await _queries.get_run_with_session(run_id, session)
    pipeline_svc = PipelineService(session)
    rule = await pipeline_svc.get_event_rule_for_step(
        run.pipeline_id, "step_rejected", step_id,
    )
    if rule is None:
        return None
    pipeline = await session.get(Pipeline, run.pipeline_id)
    if pipeline is None:
        return None
    for s in pipeline.steps:
        if s.id == rule.target_step_id:
            return s.order_index
    return None


async def reject_step(
    run_id: str,
    reason: str,
    target_step_index: int,
    project_id: str,
    session: AsyncSession,
) -> dict:
    """Reject current pipeline step and regress to target step."""
    run = await _queries.get_run_with_session(run_id, session)
    if run.status in (PipelineRunStatus.COMPLETED, PipelineRunStatus.FAILED):
        raise ValidationError("Can only reject steps in a running pipeline")
    if target_step_index < 0:
        raise ValidationError("target_step_index must be >= 0")
    if target_step_index >= run.current_step_index:
        raise ValidationError(
            f"target_step_index ({target_step_index}) must be less than "
            f"current_step_index ({run.current_step_index})"
        )

    # Find current RUNNING step
    current_sr = next(
        (sr for sr in run.step_runs if sr.status == PipelineStepRunStatus.RUNNING),
        None,
    )
    if current_sr is None:
        raise ValidationError("No RUNNING step run found")

    agent_name = "unknown"
    if current_sr.pipeline_step and current_sr.pipeline_step.agent:
        agent_name = current_sr.pipeline_step.agent.name

    # Mark as REJECTED
    current_sr.status = PipelineStepRunStatus.REJECTED
    current_sr.finished_at = now()

    # Load pipeline, find target step
    pipeline = await session.execute(
        select(Pipeline)
        .where(Pipeline.id == run.pipeline_id)
        .options(selectinload(Pipeline.steps).selectinload(PipelineStep.agent))
    )
    pipeline = pipeline.unique().scalar_one_or_none()
    if pipeline is None:
        raise NotFoundError(f"Pipeline not found: {run.pipeline_id}")

    steps = sorted(pipeline.steps, key=lambda s: s.order_index)
    if target_step_index >= len(steps):
        raise ValidationError(
            f"target_step_index ({target_step_index}) out of bounds "
            f"(pipeline has {len(steps)} steps)"
        )

    target_step = steps[target_step_index]
    new_step_run = PipelineStepRun(
        pipeline_run_id=run.id,
        pipeline_step_id=target_step.id,
        status=PipelineStepRunStatus.RUNNING,
    )
    session.add(new_step_run)
    new_step_run.started_at = now()
    await session.flush()

    # Update run state
    run.current_step_index = target_step_index
    run.rejection_count = (run.rejection_count or 0) + 1
    max_reached = False
    if run.rejection_count >= 3:
        run.status = PipelineRunStatus.FAILED
        run.finished_at = now()
        max_reached = True

    # Save rejection message
    msg = PipelineMessage(
        pipeline_run_id=run.id,
        sender_agent_name=agent_name,
        content=f"**Step rejected — regressing to step {target_step_index}**\n\nReason: {reason}",
    )
    session.add(msg)

    await _events.emit_step_rejected(
        project_id, run.issue_id, run_id, current_sr.id,
        agent_name, reason, target_step_index, run.rejection_count,
    )

    await _safe_session.safe_commit(session)

    # Signal _execute() to wake up
    old_idx = None
    for i, step in enumerate(steps):
        if step.id == current_sr.pipeline_step_id:
            old_idx = i
            break

    if old_idx is not None:
        _completion.set_step_completed(run_id, old_idx)

    return {"success": True, "rejection_count": run.rejection_count, "max_reached": max_reached}
```

### `_messages.py`

```python
"""Pipeline message operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline_run import PipelineMessage


async def add_message(
    run_id: str,
    sender_agent_name: str,
    content: str,
    session: AsyncSession,
) -> dict:
    """Add a message to a pipeline run."""
    msg = PipelineMessage(
        pipeline_run_id=run_id,
        sender_agent_name=sender_agent_name,
        content=content,
    )
    session.add(msg)
    await session.flush()
    return {
        "id": msg.id,
        "pipeline_run_id": msg.pipeline_run_id,
        "sender_agent_name": msg.sender_agent_name,
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


async def get_messages(
    run_id: str,
    session: AsyncSession,
) -> list[dict]:
    """Get all messages for a pipeline run."""
    result = await session.execute(
        select(PipelineMessage)
        .where(PipelineMessage.pipeline_run_id == run_id)
        .order_by(PipelineMessage.created_at)
    )
    msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "pipeline_run_id": m.pipeline_run_id,
            "sender_agent_name": m.sender_agent_name,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]
```

### `service.py` (la Facade)

```python
"""PipelineRunService facade — delegates to specialized modules.

This is the ONLY public entry point. All external callers import from here
via the package __init__.py.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pipeline_run import (
    _execution,
    _lifecycle,
    _messages,
    _orchestrated,
    _queries,
    _rejection,
)


class PipelineRunService:
    """Facade for pipeline run operations.

    Every public method delegates cleanly to a sub-module. Adding a new feature
    means adding a new _<feature>.py module and wiring it here — no file
    grows beyond ~200 lines.
    """

    def __init__(self, session: AsyncSession, session_factory=None):
        self.session = session
        self.session_factory = session_factory

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(
        self, pipeline_id: str, issue_id: str, project_id: str, project_path: str,
        orchestrated: bool = False,
    ) -> dict:
        return await _lifecycle.start(
            pipeline_id, issue_id, project_id, project_path,
            orchestrated, self.session, self.session_factory,
        )

    async def pause_run(self, run_id: str) -> dict:
        return await _lifecycle.pause_run(run_id, self.session)

    async def resume_run(self, run_id: str) -> dict:
        return await _lifecycle.resume_run(run_id, self.session)

    async def cancel_run(self, run_id: str) -> bool:
        return await _lifecycle.cancel_run(run_id, self.session)

    async def advance_step(self, run_id: str) -> dict:
        return await _lifecycle.advance_step(run_id, self.session)

    # ── Orchestrated execution ───────────────────────────────────

    async def start_step(
        self, run_id: str, project_id: str, project_path: str,
    ) -> dict:
        return await _orchestrated.start_step(run_id, project_id, project_path, self.session)

    # ── Rejection ────────────────────────────────────────────────

    async def resolve_rejection_target(self, run_id: str, step_id: str) -> int | None:
        return await _rejection.resolve_rejection_target(run_id, step_id, self.session)

    async def reject_step(
        self, run_id: str, reason: str, target_step_index: int, project_id: str,
    ) -> dict:
        return await _rejection.reject_step(run_id, reason, target_step_index, project_id, self.session)

    # ── Queries ──────────────────────────────────────────────────

    async def get_run(self, run_id: str) -> dict:
        return await _queries.get_run(run_id, self.session)

    async def get_runs_for_issue(self, issue_id: str) -> list[dict]:
        return await _queries.get_runs_for_issue(issue_id, self.session)

    async def get_active_runs_for_issues(self, issue_ids: list[str]) -> dict[str, dict | None]:
        return await _queries.get_active_runs_for_issues(issue_ids, self.session)

    async def get_active_runs_for_project(self, project_id: str) -> list[dict]:
        return await _queries.get_active_runs_for_project(project_id, self.session)

    # ── Messages ─────────────────────────────────────────────────

    async def add_message(self, run_id: str, sender_agent_name: str, content: str) -> dict:
        return await _messages.add_message(run_id, sender_agent_name, content, self.session)

    async def get_messages(self, run_id: str) -> list[dict]:
        return await _messages.get_messages(run_id, self.session)
```

### `__init__.py`

```python
"""Pipeline run service package — modular replacement for monolithic pipeline_run_service.py."""

from app.services.pipeline_run._completion import set_step_completed
from app.services.pipeline_run.service import PipelineRunService

__all__ = [
    "PipelineRunService",
    "set_step_completed",
]
```

---

## Rischi e Mitigazioni

### R1: Dipendenza circolare `_lifecycle` → `_execution`
`_lifecycle.start()` per auto-mode deve chiamare `_execution.execute()`. Ma `_execution` non dipende da `_lifecycle`, quindi l'import è unidirezionale. Tuttavia, se `_execution` importasse `_lifecycle`, creerebbe un ciclo.

**Soluzione:** L'import di `_execution` dentro `_lifecycle.start()` è esplicito e **top-level**, non circolare:
```python
# _lifecycle.py
from app.services.pipeline_run import _execution  # OK: _execution non importa _lifecycle
```
(Verificato: `_execution` importa solo `_queries`, `_terminal`, `_events`, `_completion`, `_safe_session`)

### R2: `_orchestrated.monitor_step()` accede a `_completion._completion_events`
Il modulo `_completion` espone `_completion_events` come variabile privata. `_orchestrated` deve leggerla per verificare se l'evento esiste.

**Soluzione:** Aggiungere un getter pubblico in `_completion`:
```python
def get_completion_event(run_id: str, step_index: int) -> asyncio.Event | None:
    return _completion_events.get((run_id, step_index))
```

### R3: `_execution._run_step()` usa late-import per `terminal_session`
`from app.services.terminal_session import TerminalSession, _sessions, _ensure_reader` è già un late import oggi. Rimane tale per non introdurre nuove dipendenze circolari con `terminal_session`.

### R4: `_rejection.resolve_rejection_target()` usa late-import per `PipelineService`
Stessa situazione di oggi. Rimane late import.

### R5: Possibili rotture in test
I test in `test_pipeline_run_service.py` fanno `from app.services.pipeline_run_service import PipelineRunService`. Dopo il refactoring diventa `from app.services.pipeline_run import PipelineRunService`.

**Soluzione:** I test vengono aggiornati nell'ultimo step prima di eliminare il file originale. Funzionano sia con l'import vecchio che nuovo fino a quel punto.

---

## File che Cambiano / Vengono Creati / Eliminati

### Creati (12 file nuovi)
| File | Righe stimate |
|---|---|
| `backend/app/services/pipeline_run/__init__.py` | ~5 |
| `backend/app/services/pipeline_run/service.py` | ~80 |
| `backend/app/services/pipeline_run/_completion.py` | ~40 |
| `backend/app/services/pipeline_run/_safe_session.py` | ~35 |
| `backend/app/services/pipeline_run/_responses.py` | ~70 |
| `backend/app/services/pipeline_run/_terminal.py` | ~15 |
| `backend/app/services/pipeline_run/_events.py` | ~100 |
| `backend/app/services/pipeline_run/_messages.py` | ~50 |
| `backend/app/services/pipeline_run/_queries.py` | ~100 |
| `backend/app/services/pipeline_run/_lifecycle.py` | ~200 |
| `backend/app/services/pipeline_run/_execution.py` | ~230 |
| `backend/app/services/pipeline_run/_orchestrated.py` | ~150 |
| `backend/app/services/pipeline_run/_rejection.py` | ~120 |

### Modificati (3 file)
| File | Cosa cambia |
|---|---|
| `backend/tests/test_pipeline_run_service.py` | Import: `pipeline_run_service` → `pipeline_run` |
| `backend/tests/test_pipeline_event_rules.py` | Stesso cambio import |
| `backend/tests/test_pipeline_rejection.py` | Stesso cambio import |

### Eliminati (1 file)
| File | Motivo |
|---|---|
| `backend/app/services/pipeline_run_service.py` | Sostituito dal package |

---

## Piano di Esecuzione — Task per Task

### Task 1: Creare la struttura del package
**Obiettivo:** Setup della directory `pipeline_run/` con `__init__.py` che re-exporta dal vecchio file.

**File:**
- Create: `backend/app/services/pipeline_run/__init__.py`
- Create: directory `backend/app/services/pipeline_run/`

**Codice `__init__.py`:**
```python
from app.services.pipeline_run_service import PipelineRunService, set_step_completed

__all__ = ["PipelineRunService", "set_step_completed"]
```

**Verifica:**
```bash
cd backend && python -c "from app.services.pipeline_run import PipelineRunService, set_step_completed; print('OK')"
```

### Task 2: Estrarre `_completion.py`
**Obiettivo:** Spostare `_step_completion_events` + `set_step_completed()` + aggiungere `register_completion_event()`, `unregister_completion_event()`, `get_completion_event()`.

**File:**
- Create: `backend/app/services/pipeline_run/_completion.py`
- Il vecchio file mantiene `set_step_completed` (re-export via import) finché non viene eliminato

**Codice:** Come da specifica sopra.

**Verifica:** `python -c "from app.services.pipeline_run._completion import set_step_completed, register_completion_event; print('OK')"`

### Task 3: Estrarre `_safe_session.py`
**Obiettivo:** Spostare `_safe_flush_session()` e `_safe_commit_session()` in modulo separato.

**File:**
- Create: `backend/app/services/pipeline_run/_safe_session.py`

### Task 4: Estrarre `_responses.py`
**Obiettivo:** Creare i builder `step_run_to_dict()`, `run_to_dict()`, `active_run_to_dict()`.

**File:**
- Create: `backend/app/services/pipeline_run/_responses.py`

**Verifica:**
```bash
cd backend && python -m pytest tests/test_pipeline_run_service.py -v 2>&1 | head -30
# Deve passare — il vecchio file è ancora intatto
```

### Task 5: Estrarre `_terminal.py`
**Obiettivo:** Creare `cleanup_terminal()` utility.

**File:**
- Create: `backend/app/services/pipeline_run/_terminal.py`

### Task 6: Estrarre `_events.py`
**Obiettivo:** Tutte le funzioni `emit_*` per eventi WebSocket.

**File:**
- Create: `backend/app/services/pipeline_run/_events.py`

### Task 7: Estrarre `_messages.py`
**Obiettivo:** `add_message()` e `get_messages()`.

**File:**
- Create: `backend/app/services/pipeline_run/_messages.py`

### Task 8: Estrarre `_queries.py`
**Obiettivo:** Tutti i metodi `get_*`.

**File:**
- Create: `backend/app/services/pipeline_run/_queries.py`

### Task 9: Estrarre `_execution.py`
**Obiettivo:** Auto-mode: `execute()`, `_wait_for_run()`, `_setup_step_environment()`, `_handle_step_completion()`, `_finalize_run()`, `_run_step()`.

**File:**
- Create: `backend/app/services/pipeline_run/_execution.py`

### Task 10: Estrarre `_orchestrated.py`
**Obiettivo:** Orchestrated: `start_step()`, `monitor_step()`.

**File:**
- Create: `backend/app/services/pipeline_run/_orchestrated.py`

### Task 11: Estrarre `_rejection.py`
**Obiettivo:** `reject_step()`, `resolve_rejection_target()`.

**File:**
- Create: `backend/app/services/pipeline_run/_rejection.py`

### Task 12: Estrarre `_lifecycle.py`
**Obiettivo:** `start()`, `pause_run()`, `resume_run()`, `cancel_run()`, `advance_step()`.

**File:**
- Create: `backend/app/services/pipeline_run/_lifecycle.py`

### Task 13: Creare la Facade `service.py`
**Obiettivo:** `PipelineRunService` che DELEGA a tutti i moduli interni.

**File:**
- Create: `backend/app/services/pipeline_run/service.py`

### Task 14: Aggiornare `__init__.py`
**Obiettivo:** Puntare al nuovo `service.py` invece che al vecchio file.

**Modifica:**
```python
from app.services.pipeline_run.service import PipelineRunService
from app.services.pipeline_run._completion import set_step_completed
```

### Task 15: Eseguire tutti i test
**Obiettivo:** Verificare che tutto il vecchio e nuovo codice funzioni.

```bash
cd backend && python -m pytest tests/test_pipeline_run_service.py tests/test_pipeline_event_rules.py tests/test_pipeline_rejection.py -v
```

### Task 16: Aggiornare import nei test
**Obiettivo:** Tutti i test importano dal nuovo package.

**Modifiche:**
- `tests/test_pipeline_run_service.py`: `from app.services.pipeline_run import PipelineRunService`
- `tests/test_pipeline_event_rules.py`: stesso
- `tests/test_pipeline_rejection.py`: stesso

### Task 17: Eliminare `pipeline_run_service.py`
**Obiettivo:** Rimuovere definitivamente il file monolitico.

```bash
rm backend/app/services/pipeline_run_service.py
```

### Task 18: Test finale
**Obiettivo:** Suite completa passa.

```bash
cd backend && python -m pytest tests/ -v --timeout=60
```

---

## Metriche di Successo

| Metrica | Prima | Dopo |
|---|---|---|
| `pipeline_run_service.py` righe | 1211 | ELIMINATO |
| Modulo più grande nel package | — | ~230 righe (`_execution.py`) |
| Numero di file nel package | 1 | 12 |
| Linee duplicate (response building) | ~60 (×4 copie) | 0 (1 funzione centrale) |
| Linee duplicate (terminal cleanup) | ~20 (×5 copie) | 0 (1 funzione centrale) |
| Eventi WebSocket inline | ~15 chiamate sparse | 10 funzioni dedicate in 1 file |
| Import circolari (lazy import) | 2 | 2 (stessi, non eliminabili) |
| Test che passano | 10 | 10 (stessi test, stessi risultati) |
| Tempo per aggiungere nuova feature | Alto (toccare 1200 righe) | Basso (creare nuovo `_*.py` + 1 riga in facade) |
