## Recap

**Problema:** Errore CORS al caricamento della pagina Issues: `http://localhost:4173/api/projects//issues/` → redirect → bloccato da CORS su `http://localhost:8001`.

**Due cause identificate e risolte:**

### 1. CORS origins mancanti (backend/app/config.py)
- `cors_origins` hardcoded solo per `localhost:5173,127.0.0.1:5173` (Vite HMR dev)
- Manca la porta 4173 (Vite preview, default di `python start.py`)
- Fix: aggiunte `http://localhost:4173` e `http://127.0.0.1:4173` al default
- Già sovrascrivibile via env var `CORS_ORIGINS` in `.env`

### 2. Query hook React Query senza `enabled` guard (frontend/src/features/issues/hooks.ts)
- `useIssues`, `useIssue`, `useFeedback`, `useProjectTags` fetchavano anche con `projectId=""`
- Costruivano URL come `/api/projects//issues/` (doppio slash)
- Il doppio slash causava redirect HTTP → cross-origin → CORS block
- Fix: aggiunto `enabled: Boolean(projectId)` a tutti e 4 i query hook

**File modificati:**
- `backend/app/config.py` — 1 riga (cors_origins default)
- `frontend/src/features/issues/hooks.ts` — 4 righe (enabled guard)

**Verifica:** Python syntax check OK, TypeScript compilation OK (tsc exit 0).