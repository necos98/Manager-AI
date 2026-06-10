Fix: renamed `event_service.notify()` → `event_service.emit()` in two endpoints in `backend/app/routers/issues.py`:

1. **`complete_issue()`** (line 133) — was calling `notify` on `EventService` which has no such method. Would crash every time an issue was completed via REST endpoint.
2. **`force_finish_issue_endpoint()`** (line 159) — same bug, was the one that actually surfaced as the user's reported ASGI error.

`EventService` has an `emit()` method that dispatches events to all registered notifiers (WebSocketNotifier, NotificationService). The `notify()` method only exists on the `BaseNotifier` subclasses — it was never a method of `EventService` itself.

Verified: syntax check passed, EventService.emit() confirmed present, zero remaining occurrences of `event_service.notify` in the codebase.