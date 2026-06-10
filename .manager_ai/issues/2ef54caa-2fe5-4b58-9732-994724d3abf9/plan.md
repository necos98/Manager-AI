## Piano di implementazione

### Task 1: Fix mark_dispatched() in issue_queue_service.py
Modificare `mark_dispatched()` per cercare un entry PENDING se non trova un entry DISPATCHING,
esattamente come già fa `mark_failed()`.

**File:** `backend/app/services/issue_queue_service.py`
**Metodo:** `mark_dispatched` (line 116-129)

**Modifica:**
```python
async def mark_dispatched(self, issue_id: str) -> Optional[QueueEntry]:
    """Mark the QueueEntry for ``issue_id`` as ``dispatched``.

    Supports both DISPATCHING → DISPATCHED (normal completion)
    and PENDING → DISPATCHED (manual removal from queue).
    """
    async with async_session() as session:
        entry = await self._get_dispatching_by_issue(session, issue_id)
        if entry is None:
            entry = await self._get_pending_by_issue(session, issue_id)
        if entry is None:
            logger.warning(
                "No active QueueEntry found for issue %s — already dispatched?",
                issue_id,
            )
            return None
        entry.status = QueueEntryStatus.DISPATCHED
        await session.commit()
        logger.info("QueueEntry %s marked DISPATCHED", entry.id)
        return entry
```

**Verifica:** Import test con `python -c` per confermare sintassi e logica.
