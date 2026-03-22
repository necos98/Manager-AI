# Workflow Hardening — Design Spec

**Date:** 2026-03-22
**Scope:** Surgical fixes with solid architectural foundations
**Context:** Manager AI is a personal/local tool for AI-powered project management with Claude Code integration. These changes fix workflow gaps and establish clean architectural patterns for future growth.

---

## 1. Service Layer with Uniform Contract

### Problem

Business logic is scattered across services, routers, and MCP tools. Error handling is inconsistent: `ValueError` in issue_service, `KeyError` in terminal_service, `None` returns in project_service. Routers have ad-hoc try/except blocks. MCP tools duplicate logic that should live in services.

### Design

#### 1.1 — Custom Exceptions

Create `app/exceptions.py`:

```python
class AppError(Exception):
    """Base for all application errors."""
    status_code: int = 500
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class NotFoundError(AppError):
    status_code = 404

class InvalidTransitionError(AppError):
    status_code = 409

class ValidationError(AppError):
    status_code = 422
```

#### 1.2 — Global Exception Handler

Register in `main.py`:

```python
@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
```

All routers stop doing try/except for business logic. They call services and let exceptions propagate to the global handler.

#### 1.3 — The Rule

- **Services**: validate, raise exceptions, emit WebSocket events, fire hooks. All business logic lives here.
- **Routers**: receive request, call service, return response. Zero logic.
- **MCP tools**: call the same service methods as routers. Zero duplicated logic.

### Files Affected

- New: `app/exceptions.py`
- Modified: `app/main.py` (register handler)
- Modified: All services (use custom exceptions)
- Modified: All routers (remove try/except business logic)
- Modified: `app/mcp/server.py` (delegate to services, remove duplicated logic)

---

## 2. State Machine Cleanup

### Problem

- `DECLINED` state creates a dead-end with no valid outbound transitions
- `NEW → REASONING` transition is missing from `VALID_TRANSITIONS` but works via MCP bypass
- `decline_feedback` field exists for a state that's being removed

### Design

#### New Enum

```python
class IssueStatus(str, Enum):
    NEW = "new"
    REASONING = "reasoning"
    PLANNED = "planned"
    ACCEPTED = "accepted"
    FINISHED = "finished"
    CANCELED = "canceled"
```

#### New Transitions

```python
VALID_TRANSITIONS = [
    (IssueStatus.NEW, IssueStatus.REASONING),
    (IssueStatus.REASONING, IssueStatus.PLANNED),
    (IssueStatus.PLANNED, IssueStatus.ACCEPTED),
    (IssueStatus.ACCEPTED, IssueStatus.FINISHED),
]
# CANCELED is allowed from any state (checked separately)
```

#### Single Validation Point

All transition validation lives in `issue_service._validate_transition(current, target)`:
- Checks `VALID_TRANSITIONS` tuple list
- Handles CANCELED special case (any → CANCELED)
- Raises `InvalidTransitionError` if invalid

No other layer touches transition logic.

#### What Gets Removed

- `DECLINED` from `IssueStatus` enum
- `decline_feedback` column from Issue model
- `decline_issue()` from issue_service, MCP tools, and router
- `HookEvent.ISSUE_DECLINED` from hook registry
- `get_next_issue()` simplified (no DECLINED prioritization)
- Frontend: decline UI and feedback display

#### Migration

- Alembic migration drops `decline_feedback` column
- Any existing DECLINED issues get migrated to PLANNED status

### Files Affected

- Modified: `app/models/issue.py` (enum, transitions, model)
- Modified: `app/services/issue_service.py` (remove decline, add _validate_transition)
- Modified: `app/mcp/server.py` (remove decline_issue tool)
- Modified: `app/routers/issues.py` (remove decline endpoint handling)
- Modified: `app/hooks/registry.py` (remove ISSUE_DECLINED event)
- New: Alembic migration
- Modified: Frontend issue detail page (remove decline UI)

---

## 3. Hook Firing in Service Layer

### Problem

`hook_registry.fire()` is called in `mcp/server.py`. If a status transition happens via REST, no hooks fire. Same action, different behavior depending on channel.

### Design

Move all `hook_registry.fire()` calls into service methods:

```python
# issue_service.py
async def complete_issue(self, issue_id, project_id, recap):
    issue = await self.get_for_project(issue_id, project_id)
    self._validate_transition(issue.status, IssueStatus.FINISHED)
    self._validate_tasks_completed(issue)
    issue.status = IssueStatus.FINISHED
    issue.recap = recap
    await self.session.commit()
    await event_service.emit(...)        # WebSocket notification
    await hook_registry.fire(...)        # Hook execution
```

Same pattern for `accept_issue()`, `cancel_issue()`, and any future stateful operations.

MCP tools and routers both call `service.complete_issue()` — same logic, same side-effects, always.

### Dependency Injection

Services that fire hooks need access to `hook_registry`. Pass it as a parameter or import the global singleton (already exists at `hooks/registry.py` module level).

### Files Affected

- Modified: `app/services/issue_service.py` (add hook firing)
- Modified: `app/mcp/server.py` (remove hook firing, delegate to service)

---

## 4. Enforce Task Completion

### Problem

An issue can be marked FINISHED with all tasks still PENDING. No validation that work was actually done.

### Design

`issue_service.complete_issue()` checks:

1. Load all tasks for the issue
2. If tasks exist and any are not COMPLETED → raise `ValidationError` with list of pending task names
3. If no tasks exist → allow completion (tasks are optional)

```python
async def _validate_tasks_completed(self, issue):
    tasks = await task_service.list_by_issue(issue.id)
    if not tasks:
        return  # No tasks = completion allowed
    pending = [t for t in tasks if t.status != TaskStatus.COMPLETED]
    if pending:
        names = ", ".join(t.name for t in pending)
        raise ValidationError(f"Cannot complete: {len(pending)} tasks not finished: {names}")
```

### Files Affected

- Modified: `app/services/issue_service.py` (add validation)

---

## 5. Terminal Cleanup on Project Delete

### Problem

`DELETE /projects/{id}` cascades in DB but leaves orphaned PTY processes alive.

### Design

`project_service.delete()` performs cleanup before DB delete:

1. `terminal_service.list_active(project_id=id)` → get active terminals
2. `terminal_service.kill(terminal_id)` for each → terminate PTY processes
3. Proceed with DB cascade delete

Same pattern in `issue_service.cancel_issue()` if terminals are open for that issue.

Note: `terminal_service` is a singleton (not session-scoped like DB services), so dependency injection differs — import the global instance directly rather than injecting via session.

### Files Affected

- Modified: `app/services/project_service.py` (add terminal cleanup)
- Modified: `app/services/issue_service.py` (optional: cleanup on cancel)

---

## 6. MCP Input Validation

### Problem

Some service methods accept empty strings where they shouldn't. `create_spec()` and `create_plan()` already validate for empty/blank input. But `complete_issue(recap)` and `set_issue_name(name)` do not.

### Design

Validation lives in service methods (not MCP layer). Add validation where missing:

- `complete_issue(recap)`: raises `ValidationError` if `recap.strip()` is empty
- `set_issue_name(name)`: raises `ValidationError` if `name` exceeds 500 chars

Note: `create_spec()` and `create_plan()` already validate — no changes needed there.

Since both MCP and REST call the same service, validation is applied uniformly.

### Files Affected

- Modified: `app/services/issue_service.py` (add input validation to existing methods)

---

## 7. Observable Hook Failures

### Problem

If `claude` CLI is not installed, the hook executor catches `FileNotFoundError` and returns an `ExecutorResult` but doesn't log the error or emit an observable event.

### Design

In `hook_registry.fire()` and `executor.py`:

1. Add `logger.error(f"Hook {hook_name} failed: {error}")` in all catch blocks
2. Verify that `hook_failed` WebSocket event is emitted with error details in all failure paths
3. Frontend: ensure `hook_failed` events render as red error toasts (verify existing behavior)

### Files Affected

- Modified: `app/hooks/registry.py` (verify error event emission)
- Modified: `app/hooks/executor.py` (add logging)
- Modified: Frontend toast component (verify error styling, if needed)

---

## Implementation Order

Dependencies flow top-down:

1. **Exceptions** (1.1, 1.2) — foundation for everything else
2. **State machine cleanup** (2) — removes DECLINED, cleans transitions
3. **Service layer consolidation** (1.3, 3) — move all logic + hooks into services
4. **Task completion enforcement** (4) — depends on clean service layer
5. **Terminal cleanup** (5) — independent
6. **Input validation** (6) — depends on exceptions being in place
7. **Hook failure observability** (7) — independent

Steps 5 and 7 can be done in parallel. Steps 1-4 are sequential.

---

## Out of Scope

- Authentication / authorization (not needed for local tool)
- Terminal session persistence (not needed per user decision)
- LanceDB integration (future feature)
- Priority field in frontend (cosmetic, not a workflow gap)
- State machine library (overengineering for 5 states)
