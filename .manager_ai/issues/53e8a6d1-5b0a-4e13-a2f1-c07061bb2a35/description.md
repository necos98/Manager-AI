 23. background_writer.py:104-119 — Fire-and-forget event emission

  asyncio.create_task(event_service.emit(...))
  Task creato senza reference tracking. Eccezioni perse silenziosamente.