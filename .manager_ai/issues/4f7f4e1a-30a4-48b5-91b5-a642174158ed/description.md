 24. memory_store_core.py:75 — Crash su created_at=None

  idx.sort(key=lambda e: (e.get("created_at", ""), e.get("id", "")))
  Se created_at è esplicitamente None, confronto None < str lancia TypeError.