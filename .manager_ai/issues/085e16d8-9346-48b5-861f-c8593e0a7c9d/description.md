`invalidate_issue_cache()` in `issue_store.py:325` chiama `issue_cache.clear()` che cancella TUTTI i dati in cache per TUTTI i progetti. Un singolo file change in un progetto azzera l'intera cache.

Stesso problema in `memory_store.py` e `file_store.py` — tutte usano `.clear()` globale.

**Impatto:** Se hai 3 progetti e modifichi un'issue nel progetto A, le cache di B e C vengono invalidate. Al prossimo accesso a B o C, tutto va riletto da disco.

**Fix:**
1. Passare a invalidazione per-project: `cache.invalidate(f"{project_path}:*")` o mantenere un set di chiavi per progetto
2. Ancora meglio: invalidazione per-ID nei casi in cui il watcher sa quale file è cambiato (il watcher ha il path completo, può estrarre l'ID)