## Analisi

L'errore segnalato ha **due cause distinte** che combinate producono il fallimento CORS visibile all'utente:

### Causa 1 — CORS origins non includono la porta 4173

`backend/app/config.py` linea 17:
```python
cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
```

Il frontend Vite preview server è sulla porta **4173** (default di `python start.py`), non 5173 (Vite HMR dev). Qualsiasi richiesta cross-origin dal frontend (porta 4173) al backend (porta 8000/8001) viene bloccata perché `Access-Control-Allow-Origin` non include `http://localhost:4173`.

Inoltre:
- `cors_origins` non è sovrascrivibile da `.env` — il valore è hardcoded
- Manca `http://127.0.0.1:4173` oltre a `http://localhost:4173`
- Se l'utente usa altre porte (`--port 8080`, `--frontend-port 3000`), si ripete lo stesso problema

### Causa 2 — URL con doppio slash `/api/projects//issues/`

L'errore mostra `http://localhost:4173/api/projects//issues/` — con `//` dopo projects. Questo significa che `projectId` è una stringa vuota quando viene costruito il path.

Analisi del codice:
- `hooks.ts` → `useIssues(projectId)` chiama `fetchIssues(projectId)` che costruisce ``/projects/${projectId}/issues``
- Il React Query hook **non ha** `enabled: Boolean(projectId)` — quindi anche con `projectId=""` parte la fetch
- Altri hook simili (come `useActivePipelineRuns`) già hanno `enabled: Boolean(projectId)` — `useIssues` no

Il doppio slash causa un redirect HTTP (Starlette normalizza le URL), e il redirect cross-origin viene bloccato da CORS.

### Sintomi visibili all'utente
1. La pagina Issues non carica — errore CORS in console
2. React Error #310 (minified) — l'app crasha completamente
3. Loop infinito di tentativi di fetch (React Query retry)

## Specifica

### Task 1: Aggiungere porta 4173 e rendere CORS_ORIGINS configurabile

**File:** `backend/app/config.py`

- Aggiungere `http://localhost:4173` e `http://127.0.0.1:4173` al default di `cors_origins`
- Rimuovere l'hardcode: rendere `cors_origins` sovrascrivibile da env var `CORS_ORIGINS` nel model_config di Settings (Pydantic lo fa già tramite `env_file`)

**Esempio di default:**
```
cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
```

L'utente può poi impostare `CORS_ORIGINS=http://localhost:3000` in `.env` se usa una porta diversa.

### Task 2: Aggiungere guard `enabled` a useIssues

**File:** `frontend/src/features/issues/hooks.ts`

- Aggiungere `enabled: Boolean(projectId)` al `useQuery` in `useIssues` per prevenire fetch con projectId vuoto
- Questo evita che venga costruita la URL con doppio slash

### Task 3: Verificare altri hook `useXxx(projectId)` senza guard

- Controllare `hooks.ts` e `hooks-bulk.ts` per altri hook che prendono `projectId` e non hanno `enabled: Boolean(projectId)` — aggiungere la guard dove manca

## Criteri di accettazione
1. Backend risponde con CORS header per `http://localhost:4173` (preflight OPTIONS passa)
2. `useIssues` non fetcha quando `projectId` è vuoto
3. Nessun errore CORS in console quando si naviga alla pagina Issues
4. `CORS_ORIGINS` env var sovrascrive il default