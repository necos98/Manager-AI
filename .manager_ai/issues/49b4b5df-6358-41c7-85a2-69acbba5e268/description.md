`_check_resource_consistency()` in `backend/app/routers/projects.py:83-217` fa uno scan RAW (senza cache) di TUTTI i file YAML/markdown per verificare `project_id` mismatches. Il frontend chiama l'health endpoint ogni 30 secondi (`refetchInterval: 30_000` in `hooks.ts:70`).

Anche quando non c'è nulla da fixare (caso comune), vengono letti:
- `issues.yaml` (index)
- Ogni `issue.yaml` individuale
- `memories.yaml` (index)
- Ogni `memory.md` individuale (con parsing frontmatter)

Queste letture bypassano completamente il cache layer (`ReadCache`) perché usano `open()` + `yaml.safe_load()` raw.

**Fix possibili:**
1. Cache del risultato per N minuti (il check è idempotente)
2. Timestamp-based: ri-scansionare solo se i file YAML sono stati modificati dopo l'ultimo check
3. Ridurre la frequenza frontend (da 30s a 5min)