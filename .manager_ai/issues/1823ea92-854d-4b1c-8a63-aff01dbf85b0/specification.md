## Bug Analysis

The `force_finish_issue_endpoint` in `backend/app/routers/issues.py` calls `await event_service.notify(...)` which raises `AttributeError: 'EventService' object has no attribute 'notify'`.

`EventService` (defined in `backend/app/services/event_service.py`) has:
- `emit(event: dict)` — the correct method that dispatches events to all registered notifiers
- NO `notify` method — `notify()` exists only on the `BaseNotifier` subclasses (`WebSocketNotifier`)

The same incorrect call `event_service.notify(...)` also exists in the `complete_issue` endpoint (line 133), which would crash anytime an issue is completed.

## Fix

Replace both occurrences of `event_service.notify(` with `event_service.emit(` in:
1. `backend/app/routers/issues.py:133` — in `complete_issue()`
2. `backend/app/routers/issues.py:159` — in `force_finish_issue_endpoint()`

That's it — one-character method rename, two lines.