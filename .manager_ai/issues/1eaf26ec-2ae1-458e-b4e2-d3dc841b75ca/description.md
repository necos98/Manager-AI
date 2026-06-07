30. ask_user_question blocca worker pool fino a 3600s

  mcp/server.py:957: await asyncio.wait_for(event.wait(), timeout=timeout_seconds) — blocca un worker ASGI per tutta
  l'attesa.