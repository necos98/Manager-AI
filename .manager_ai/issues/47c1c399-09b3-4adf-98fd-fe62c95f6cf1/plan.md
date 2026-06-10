## Implementation Plan: Cmd+K Command Palette & Global Search

### Approach
Due alla natura del backend (file-based storage, non SQL), la ricerca globale richiede di iterare tutti i progetti. Creeremo un endpoint backend dedicato `/api/search` e un command palette frontend con keyboard shortcuts globali.

### Step 1: Backend — Nuovo schema search
**File: `backend/app/schemas/search.py`**
- `SearchResultItem` — id, name, description, status, project_id, project_name, type (issue|project|page), priority, url
- `SearchResults` — issues: list, projects: list, pages: list

### Step 2: Backend — Nuovo router search
**File: `backend/app/routers/search.py`**
- `GET /api/search?q=<query>` — cerca in tutti i progetti non-archiviati:
  - Issues: iterare `issue_store.list_issues_full(project.path)` per ogni progetto, filtrare per match case-insensitive in name/description. Includere project_name.
  - Projects: cercare per nome, restituire id + name
  - Pages: mappa statica delle route dell'app
- Limite 20 risultati per categoria, ordinati per priorità

### Step 3: Backend — Registrare router in main.py
**File: `backend/app/main.py`**
- `app.include_router(search_router)` — aggiungere import e registrazione

### Step 4: Frontend — Tipi e API
**File: `frontend/src/shared/types/index.ts`** — aggiungere `SearchResult`, `SearchResults` types
**File: `frontend/src/features/command-palette/api.ts`** — `searchAll(query)` via apiGet

### Step 5: Frontend — Hook use-keyboard-shortcuts
**File: `frontend/src/shared/hooks/use-keyboard-shortcuts.ts`**
- Hook globale per registrare shortcuts con `useEffect`
- Sequence key support (`g` → wait 1s per secondo tasto)
- Callback pattern: onCmdPalette, onNewIssue, onNavigate
- Evitare interferenza quando input è focalizzato

### Step 6: Frontend — Command palette hooks
**File: `frontend/src/features/command-palette/hooks.ts`**
- `useCommandPalette()` — open/close, selectedIndex, query, risultati
- `useGlobalSearch(query)` — React Query con debounce

### Step 7: Frontend — Command palette component
**File: `frontend/src/features/command-palette/components/command-palette.tsx`**
- Dialog modale con input di ricerca
- Risultati raggruppati per categoria (Issues, Projects, Pages)
- Highlight del match
- Navigazione frecce + Enter
- Collegamento a route TanStack Router per navigazione
- Shortcut Cmd+K per aprire

### Step 8: Frontend — Integrazione in __root.tsx
**File: `frontend/src/routes/__root.tsx`**
- Montare `CommandPalette` component
- Attivare `useKeyboardShortcuts` hook
- Passare callback di navigazione

### Verification
1. Avviare backend e testare `curl http://localhost:8000/api/search?q=test`
2. Avviare frontend e verificare che Cmd+K apra la palette
3. Testare search con risultati multi-progetto
4. Verificare che `g i`, `g d`, `n`, `/`, `?` funzionino
