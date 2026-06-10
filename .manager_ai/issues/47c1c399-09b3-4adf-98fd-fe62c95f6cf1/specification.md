## Cmd+K Command Palette & Global Search — Specifica

### Overview
Aggiungere una command palette stile Linear/VSCode accessibile via `Cmd+K` (o `Ctrl+K` su Windows/Linux) che consenta:
1. Ricerca full-text globale su tutte le issue (tutti i progetti)
2. Navigazione rapida tra pagine dell'app
3. Ricerca progetti
4. Registro shortcuts globali

L'app usa TanStack Router, feature-based architecture e shadcn/ui components.

### Backend changes

**Nuovo endpoint: `GET /api/search`**
Routes: `backend/app/routers/search.py`, registrato in `backend/app/main.py`

Risposta:
```json
{
  "issues": [{ "id", "name", "description", "status", "project_id", "project_name", "priority" }],
  "projects": [{ "id", "name" }],
  "pages": [{ "id": "route-path", "label": "Human label", "project_id?": "..." }]
}
```

Logica:
- Issues: scorre TUTTI i progetti (non-archived), carica le issue da ogni `.manager_ai/` e filtra per match in name/description
- Projects: cerca per nome nei progetti non-archiviati
- Pages: mappa statica delle route dell'app (dashboard, issues, files, activity, memories, settings, etc.)
- Limite: max 20 risultati per categoria, search case-insensitive

**Nuovo endpoint: `GET /api/projects/{project_id}/issues?global=true`**
Opzionale — se il search rimane per-progetto ma vogliamo un modo per estendere a multi-progetto, meglio un endpoint separato `/api/search`.

### Frontend changes

**1. `frontend/src/features/command-palette/components/command-palette.tsx`**
Componente modale (dialog) che si apre con Cmd+K:
- Input di ricerca con autofocus
- Risultati raggruppati per categoria (Issues, Projects, Pages)
- Navigazione con frecce su/giù + Enter per selezionare
- Highlight del match nei risultati
- Key: Escape chiude, Tab naviga tra categorie
- Debounce 200ms sulla digitazione

**2. `frontend/src/features/command-palette/api.ts`**
- `searchAll(query: string): Promise<SearchResults>` — chiama `GET /api/search?q=...`

**3. `frontend/src/features/command-palette/hooks.ts`**
- `useCommandPalette()` — stato di apertura/chiusura, query, risultati, selectedIndex
- `useGlobalSearch(query)` — React Query hook

**4. `frontend/src/shared/hooks/use-keyboard-shortcuts.ts`**
Hook globale per registrare shortcuts:
- `Cmd+K` / `Ctrl+K` → apre command palette
- `n` (quando nessun input focus) → nuova issue (naviga a new issue page)
- `g i` → go to issues (dopo `g`, `i` naviga)
- `g d` → go to dashboard
- `/` → focus search (se su una pagina con search bar)
- `?` → mostra help overlay con tutte le shortcuts

**5. Integrazione in `frontend/src/routes/__root.tsx`**
- Importare e montare il componente CommandPalette a livello root
- Attivare `use-keyboard-shortcuts.ts`

### Keyboard shortcuts design

Le shortcuts usano una sequenza di tasti (come Vim / Linear):
- `g i` → Issues page (premi `g`, poi `i` entro 1 secondo)
- `g d` → Dashboard
- `g p` → Projects page
- `n` → Nuova issue (se non si sta scrivendo in un input)
- `Cmd+K` → Command palette (sempre attivo)
- `/` → Focus su search (contestuale alla pagina)
- `?` → Help overlay

Lo stato di attesa della `g` viene gestito con un piccolo stato globale + timeout 1s.

### File da creare
1. `backend/app/routers/search.py` — nuovo router
2. `backend/app/schemas/search.py` — nuovi schemi
3. `frontend/src/features/command-palette/components/command-palette.tsx`
4. `frontend/src/features/command-palette/api.ts`
5. `frontend/src/features/command-palette/hooks.ts`
6. `frontend/src/shared/hooks/use-keyboard-shortcuts.ts`

### File da modificare
1. `backend/app/main.py` — registrare il nuovo router
2. `frontend/src/routes/__root.tsx` — montare CommandPalette e keyboard shortcuts hook
3. `frontend/src/shared/types/index.ts` — aggiungere SearchResult type

### Non incluso in questa issue
- Ricerca full-text su memories (sarà una issue separata)
- Filtri avanzati (per status, priorità, tag) nella command palette
- Plugin per command palette
